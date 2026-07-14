from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, HotLink, TrendSignal
from app.services.agent_service import AgentError, call_llm
from app.services.content_service import ContentError


SYSTEM_PROMPT = """你是跨境电商 Listing 优化顾问。请结合目标 Amazon 产品标题、
同品类 Amazon 标题高频词，以及小红书、Reddit、YouTube 的真实用户讨论，生成 Listing 优化建议。

规则：
1. 只输出 JSON，不得修改或声称已修改目标 Listing。
2. 这是跨平台品类洞察，不得把外部讨论伪装成该 Amazon 产品的真实差评。
3. keyword_directions、selling_points、improvement_points 各输出 1-3 项。
4. 每项必须引用 1-3 个 source_candidates 中存在的 evidence_ids。
5. 不得编造销量、功效、认证、材质或产品参数。
6. 不得将“没有负面反馈”当作卖点证据，不得建议未经验证的竞品对比或耐用性结论。
7. selling_points 只能提炼目标标题已有信息，外部证据仅用于说明该卖点对应的用户需求。
8. 所有说明使用简体中文，英文关键词可保留；数据不足时在 limitations 中明确说明。
9. keyword、headline、pain_point 必须是短关键词，不超过 12 个中文字符或 4 个英文单词，
   不得包含括号、冒号、解释或完整句子。

输出结构：
{
  "keyword_directions": [
    {"keyword": "关键词方向", "reason": "补充原因", "evidence_ids": [原帖ID]}
  ],
  "selling_points": [
    {"headline": "卖点方向", "reason": "提炼依据", "evidence_ids": [原帖ID]}
  ],
  "improvement_points": [
    {"pain_point": "跨平台用户痛点", "suggestion": "Listing表达或产品改进建议", "evidence_ids": [原帖ID]}
  ],
  "limitations": ["数据边界说明"]
}"""

REPAIR_PROMPT = """上一条响应格式无效。请严格按指定结构重新输出 JSON。
三个建议数组各含 1-3 项，每项 evidence_ids 必须引用 source_candidates 中存在的整数 ID。
不要输出 Markdown 或额外解释。"""

_WORD_RE = re.compile(r"[a-z][a-z0-9-]{2,}", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s）)]+")
_SOURCE_TOKEN_RE = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)
_STOP_WORDS = {
    "and",
    "for",
    "from",
    "the",
    "this",
    "that",
    "with",
    "your",
}
_SOURCE_STOP_WORDS = {
    "analysis",
    "comment",
    "comments",
    "pain",
    "review",
    "user",
    "youtube",
}


def _best_source(signal: TrendSignal, sources: list[HotLink]) -> HotLink | None:
    for url in _URL_RE.findall(f"{signal.title}\n{signal.summary}"):
        normalized = url.rstrip("。.,，")
        match = next((source for source in sources if source.url == normalized), None)
        if match is not None:
            return match

    candidates = [source for source in sources if source.platform == signal.platform]
    if not candidates:
        return None
    signal_tokens = {
        token
        for token in _SOURCE_TOKEN_RE.findall(
            f"{signal.title} {signal.keyword}".lower()
        )
        if token not in _SOURCE_STOP_WORDS
    }
    return max(
        candidates,
        key=lambda source: (
            len(
                signal_tokens
                & set(_SOURCE_TOKEN_RE.findall(source.title.lower()))
            ),
            source.hotness_score or 0,
        ),
    )


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def _clean_text(value: object, *, max_length: int = 500) -> str:
    return re.sub(r"[<>`]", "", str(value or "")).strip()[:max_length]


def _clean_keyword(value: object) -> str:
    text = _clean_text(value, max_length=80)
    text = re.split(r"[：:（(，,；;。]", text, maxsplit=1)[0].strip()
    if not re.search(r"[\u4e00-\u9fff]", text):
        return " ".join(text.split()[:4])
    return text[:12]


def _parse_items(
    value: object,
    *,
    fields: tuple[str, str],
    allowed_ids: set[int],
) -> list[dict[str, object]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 3:
        raise ValueError("expected 1-3 suggestions")
    result = []
    for raw in value:
        if not isinstance(raw, dict):
            raise ValueError("suggestion must be an object")
        item = {field: _clean_text(raw.get(field)) for field in fields}
        item[fields[0]] = _clean_keyword(raw.get(fields[0]))
        if not all(item.values()):
            raise ValueError("suggestion fields cannot be empty")
        evidence_ids = raw.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            raise ValueError("evidence_ids must be an array")
        valid_ids = list(
            dict.fromkeys(
                source_id
                for source_id in evidence_ids
                if isinstance(source_id, int) and source_id in allowed_ids
            )
        )[:3]
        if not valid_ids:
            raise ValueError("suggestion needs valid evidence")
        item["evidence_ids"] = valid_ids
        result.append(item)
    return result


def _parse_response(content: str, allowed_ids: set[int]) -> dict[str, object]:
    payload = json.loads(_strip_code_fence(content))
    if not isinstance(payload, dict):
        raise ValueError("response must be an object")
    limitations = payload.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        raise ValueError("limitations are required")
    return {
        "keyword_directions": _parse_items(
            payload.get("keyword_directions"),
            fields=("keyword", "reason"),
            allowed_ids=allowed_ids,
        ),
        "selling_points": _parse_items(
            payload.get("selling_points"),
            fields=("headline", "reason"),
            allowed_ids=allowed_ids,
        ),
        "improvement_points": _parse_items(
            payload.get("improvement_points"),
            fields=("pain_point", "suggestion"),
            allowed_ids=allowed_ids,
        ),
        "limitations": [_clean_text(item) for item in limitations[:3] if _clean_text(item)],
    }


def _call_and_parse(
    messages: list[dict[str, str]],
    allowed_ids: set[int],
) -> dict[str, object]:
    response = call_llm(messages, temperature=0.3, max_tokens=2400, json_mode=True)
    try:
        return _parse_response(response["content"], allowed_ids)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        retry = call_llm(
            [*messages, {"role": "user", "content": REPAIR_PROMPT}],
            temperature=0.1,
            max_tokens=2400,
            json_mode=True,
        )
        try:
            return _parse_response(retry["content"], allowed_ids)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AgentError("LLM Listing 建议格式无效，自动重试后仍失败") from exc


def _title_keywords(products: list[HotLink]) -> list[dict[str, object]]:
    counts = Counter(
        word.lower()
        for product in products
        for word in _WORD_RE.findall(html.unescape(product.title))
        if word.lower() not in _STOP_WORDS
    )
    return [
        {"keyword": keyword, "count": count}
        for keyword, count in counts.most_common(20)
    ]


def generate_listing_suggestion_preview(
    db: Session,
    *,
    product: HotLink,
) -> dict[str, object]:
    if product.platform != "amazon" or product.link_type != "product":
        raise ContentError("Listing suggestions are only available for Amazon products")
    category = db.get(Category, product.category_id)
    if category is None:
        raise ContentError("Product category not found")

    amazon_products = db.scalars(
        select(HotLink)
        .where(
            HotLink.category_id == category.id,
            HotLink.platform == "amazon",
            HotLink.link_type == "product",
        )
        .order_by(HotLink.is_hot.desc(), HotLink.hotness_score.desc())
        .limit(30)
    ).all()
    sources = db.scalars(
        select(HotLink)
        .where(
            HotLink.category_id == category.id,
            HotLink.platform.in_(("xiaohongshu", "reddit", "youtube")),
        )
        .order_by(HotLink.is_hot.desc(), HotLink.hotness_score.desc())
        .limit(30)
    ).all()
    if not sources:
        raise ContentError("No cross-platform evidence is available for this category")
    cutoff = datetime.now(UTC) - timedelta(days=90)
    signals = db.scalars(
        select(TrendSignal)
        .where(
            TrendSignal.category_id == category.id,
            TrendSignal.platform.in_(("xiaohongshu", "reddit", "youtube")),
            TrendSignal.signal_type.in_(("user_pain_point", "review_sentiment")),
            TrendSignal.collected_at >= cutoff,
        )
        .order_by(TrendSignal.metric_value.desc(), TrendSignal.collected_at.desc())
        .limit(30)
    ).all()
    context = {
        "category": {"code": category.code, "name": category.name},
        "target_product": {
            "id": product.id,
            "title": html.unescape(product.title),
            "metrics": product.description,
        },
        "amazon_title_frequencies": _title_keywords(amazon_products),
        "cross_platform_signals": [
            {
                "platform": signal.platform,
                "title": signal.title_zh or signal.title,
                "summary": (signal.summary_zh or signal.summary or "")[:700],
                "source_id": (
                    source.id if (source := _best_source(signal, sources)) else None
                ),
            }
            for signal in signals
        ],
        "source_candidates": [
            {
                "id": source.id,
                "platform": source.platform,
                "title": source.title_zh or source.title,
                "description": (source.description_zh or source.description or "")[:500],
                "url": source.url,
            }
            for source in sources
        ],
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "请生成该产品的 Listing 优化建议预览：\n\n"
            + json.dumps(context, ensure_ascii=False, indent=2),
        },
    ]
    result = _call_and_parse(messages, {source.id for source in sources})
    cited_ids = {
        source_id
        for key in (
            "keyword_directions",
            "selling_points",
            "improvement_points",
        )
        for item in result[key]
        for source_id in item["evidence_ids"]
    }
    source_by_id = {source.id: source for source in sources}
    return {
        "product_id": product.id,
        "basis": "cross_platform_category_insights",
        **result,
        "evidence": [
            {
                "id": source_id,
                "platform": source_by_id[source_id].platform,
                "title": source_by_id[source_id].title_zh
                or source_by_id[source_id].title,
                "url": source_by_id[source_id].url,
            }
            for source_id in sorted(cited_ids)
        ],
    }
