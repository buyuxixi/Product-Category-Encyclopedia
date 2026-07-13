"""选品Agent核心服务 — 数据收集 + LLM分析 + 产品发现 + 多轮对话。

v2重构要点：
1. 防幻觉：把数据库真实URL作为context传给LLM，prompt中明确禁止编造URL
2. 真对话：chat()函数完全重写，不是返回扫描摘要，而是基于上下文的多轮对话
3. 话题探索：collect_data时按topic关键词搜索所有数据源
4. 数据溯源：每个discovery的source_links必须来自数据库真实记录
"""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    AgentMessage,
    AgentScan,
    Category,
    HotLink,
    ProductDiscovery,
    SourceMaterial,
    TrendSignal,
)

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """选品Agent运行时错误。"""


# ---------------------------------------------------------------------------
# 数据收集
# ---------------------------------------------------------------------------

def collect_data(
    db: Session,
    *,
    category_code: str | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    """从数据库多维度收集市场数据，供LLM分析。

    所有数据包含真实URL，LLM只能引用这些URL，不能编造。
    """
    data: dict[str, Any] = {}

    # 1. 品类列表
    categories = db.scalars(
        select(Category).where(Category.parent_id.is_(None)).order_by(Category.name)
    ).all()
    data["categories"] = [
        {
            "code": c.code,
            "name": c.name,
            "description": (c.description or "")[:200],
            "children": [
                {"code": ch.code, "name": ch.name}
                for ch in sorted(c.children, key=lambda x: x.name)
            ],
        }
        for c in categories
    ]

    # 2. Amazon产品 (从HotLink表 — 这里有真实的Amazon URL)
    amazon_links_query = (
        select(HotLink)
        .where(HotLink.platform == "amazon", HotLink.link_type == "product")
        .order_by(HotLink.is_hot.desc(), HotLink.hotness_score.desc())
        .limit(60)
    )
    if category_code:
        amazon_links_query = amazon_links_query.where(
            HotLink.category_id == select(Category.id).where(Category.code == category_code).scalar_subquery()
        )
    amazon_links = db.scalars(amazon_links_query).all()
    data["amazon_products"] = [
        {
            "title": _parse_brand_or_title(l),
            "url": l.url,  # 真实Amazon URL
            "description": l.description,  # 包含价格/评分/BSR
            "hotness_score": l.hotness_score,
            "is_hot": l.is_hot,
            "category_code": _hotlink_category_code(db, l.category_id),
        }
        for l in amazon_links
    ]

    # 3. YouTube热门视频 (真实URL)
    yt_query = (
        select(HotLink)
        .where(HotLink.platform == "youtube")
        .order_by(HotLink.is_hot.desc(), HotLink.hotness_score.desc())
        .limit(30)
    )
    if category_code:
        yt_query = yt_query.where(
            HotLink.category_id == select(Category.id).where(Category.code == category_code).scalar_subquery()
        )
    yt_links = db.scalars(yt_query).all()
    data["youtube_videos"] = [
        {
            "title": l.title,
            "url": l.url,
            "description": (l.description or "")[:200],
            "hotness_score": l.hotness_score,
            "category_code": _hotlink_category_code(db, l.category_id),
        }
        for l in yt_links
    ]

    # 4. Reddit讨论 (真实URL)
    reddit_query = (
        select(HotLink)
        .where(HotLink.platform == "reddit")
        .order_by(HotLink.collected_at.desc())
        .limit(20)
    )
    if category_code:
        reddit_query = reddit_query.where(
            HotLink.category_id == select(Category.id).where(Category.code == category_code).scalar_subquery()
        )
    reddit_links = db.scalars(reddit_query).all()
    data["reddit_posts"] = [
        {
            "title": l.title,
            "url": l.url,
            "description": (l.description or "")[:200],
            "category_code": _hotlink_category_code(db, l.category_id),
        }
        for l in reddit_links
    ]

    # 5. 趋势信号 (最近30天)
    cutoff = datetime.now(UTC) - timedelta(days=30)
    trend_query = select(TrendSignal).where(TrendSignal.collected_at >= cutoff).order_by(
        TrendSignal.collected_at.desc()
    ).limit(100)
    if category_code:
        trend_query = trend_query.where(
            TrendSignal.category_id == select(Category.id).where(Category.code == category_code).scalar_subquery()
        )
    trends = db.scalars(trend_query).all()
    data["trend_signals"] = [
        {
            "keyword": t.keyword,
            "signal_type": t.signal_type,
            "platform": t.platform,
            "metric_value": t.metric_value,
            "metric_unit": t.metric_unit,
            "trend_direction": t.trend_direction,
            "summary": (t.summary or "")[:300],
            "category_code": _trend_category_code(db, t.category_id),
        }
        for t in trends
    ]

    # 6. 话题搜索 — 按topic关键词跨品类搜索所有数据
    if topic and not category_code:
        topic_terms = _topic_search_terms(topic)
        # 搜索HotLink
        topic_hotlinks = db.scalars(
            select(HotLink).where(
                or_(
                    *(
                        condition
                        for term in topic_terms
                        for condition in (
                            func.lower(HotLink.title).contains(term),
                            func.lower(HotLink.description).contains(term),
                        )
                    )
                )
            ).limit(30)
        ).all()
        data["topic_links"] = [
            {
                "title": l.title,
                "url": l.url,
                "platform": l.platform,
                "description": (l.description or "")[:200],
                "category_code": _hotlink_category_code(db, l.category_id),
            }
            for l in topic_hotlinks
        ]
        # 搜索TrendSignal
        topic_trends = db.scalars(
            select(TrendSignal).where(
                or_(
                    *(
                        condition
                        for term in topic_terms
                        for condition in (
                            func.lower(TrendSignal.keyword).contains(term),
                            func.lower(TrendSignal.summary).contains(term),
                        )
                    )
                ),
            ).limit(20)
        ).all()
        data["topic_trends"] = [
            {
                "keyword": t.keyword,
                "platform": t.platform,
                "trend_direction": t.trend_direction,
                "summary": (t.summary or "")[:200],
            }
            for t in topic_trends
        ]
        # 标记是否在数据库中找到了话题相关数据
        data["topic_has_data"] = bool(topic_hotlinks or topic_trends)

    return data


_TOPIC_ALIASES: dict[str, tuple[str, ...]] = {
    "无线": ("wireless", "cordless", "bluetooth"),
    "便携": ("portable", "rechargeable"),
    "风扇": ("fan",),
    "夜灯": ("night light", "nightlight"),
    "药盒": ("pill organizer", "pill box", "pill dispenser"),
    "热敷": ("heating pad", "heat therapy"),
    "肩颈": ("neck", "shoulder"),
    "电疗": ("tens", "ems"),
}


def _topic_search_terms(topic: str) -> set[str]:
    """Expand common Chinese topic terms to the English terms in source data."""
    normalized = topic.strip().lower()
    terms = {normalized}
    terms.update(token for token in re.findall(r"[a-z0-9]+", normalized) if token)
    for source_term, aliases in _TOPIC_ALIASES.items():
        if source_term in normalized:
            terms.update(aliases)
    return {term for term in terms if term}


def _parse_brand_or_title(link: HotLink) -> str:
    """从Amazon HotLink中提取产品名称。

    HotLink.title通常是品牌名，description包含完整信息。
    我们优先用description里的信息构建标题。
    """
    desc = link.description or ""
    if "$" in desc and "BSR" in desc:
        # 格式如 "$21.55 ⭐4.5 (5907 reviews) — BSR #1"
        # title是品牌名，组合为更有意义的名称
        return f"{link.title} (BSR product)"
    return link.title


def _hotlink_category_code(db: Session, category_id: int) -> str:
    c = db.get(Category, category_id)
    return c.code if c else ""


def _trend_category_code(db: Session, category_id: int) -> str:
    c = db.get(Category, category_id)
    return c.code if c else ""


# ---------------------------------------------------------------------------
# LLM调用
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一个专业的跨境电商选品分析师。你的任务是基于提供的真实数据进行分析。

## 核心规则（必须遵守）：

1. **数据优先** — 如果数据库中有相关数据，必须基于真实数据分析。如果数据库中没有该话题的数据（topic_has_data=false），你应该：
   - 用你的通用电商知识给出初步分析（市场规模/竞争格局/选品方向）
   - 建议用户需要采集哪些数据（Amazon BSR/YouTube/Reddit/Google Trends）
   - 仍然可以给出discoveries，但opportunity_type应为"emerging_category"或"gap_opportunity"，reasoning中注明"基于通用市场知识，待数据验证"
   - source_links留空数组[]

2. **链接真实性** — 你收到的数据包含真实的Amazon产品URL、YouTube视频URL、Reddit讨论帖URL。你必须在source_links中使用这些真实URL，绝对不能编造URL、ASIN或产品链接。

3. **发现类型**：
   - hot_product: 数据中BSR排名靠前、评分高、评论多的产品
   - rising_trend: 搜索趋势方向为"new"或"up"的关键词
   - gap_opportunity: 有需求但产品评分低或评论指出痛点的品类
   - emerging_category: 跨品类组合或新出现的话题趋势

4. **评分标准** (0-100):
   - BSR Top3 + 4.5★以上 → 85-100分
   - BSR Top10 + 4★以上 → 70-85分
   - 趋势方向为new/up → 60-80分
   - 机会空白（痛点明显但竞争不足）→ 50-70分
   - 通用知识推断（无数据验证）→ 40-60分

5. **输出格式** (严格JSON，不要有额外文字):
{
  "summary": "2-3句概述",
  "market_overview": {
    "total_products": 数字,
    "price_range": "价格区间",
    "top_categories": ["品类1", "品类2"]
  },
  "discoveries": [
    {
      "product_name": "产品名",
      "category_code": "品类code（可为空字符串）",
      "opportunity_type": "hot_product|rising_trend|gap_opportunity|emerging_category",
      "opportunity_score": 0-100,
      "reasoning": "2-4句推荐理由",
      "keywords": ["关键词"],
      "market_signals": {
        "bsr_rank": 数字或null,
        "price": 数字或null,
        "rating": 数字或null,
        "trend_direction": "up|down|stable|new|null",
        "social_hotness": "描述"
      },
      "source_links": [
        {"title": "标题", "url": "真实URL", "platform": "amazon|youtube|reddit|google"}
      ]
    }
  ],
  "recommendations": ["行动建议1", "行动建议2"]
}

6. **source_links规则**：每个discovery的URL必须来自你收到的数据中已存在的真实URL。如果数据库无相关数据或找不到合适链接，留空数组[]。
"""


def build_analysis_prompt(data: dict[str, Any], *, topic: str | None = None) -> str:
    """构建LLM分析prompt，包含真实数据。"""
    parts: list[str] = []

    if topic:
        parts.append(f"## 分析主题\n用户指定话题：{topic}\n请重点关注与该话题相关的市场机会。\n")

    # 品类信息
    if data.get("categories"):
        cat_lines = []
        for c in data["categories"]:
            children = ", ".join(ch["name"] for ch in c["children"])
            cat_lines.append(f"- {c['name']} ({c['code']}): {c['description'][:100]} [子品类: {children}]")
        parts.append("## 品类列表\n" + "\n".join(cat_lines) + "\n")

    # Amazon产品 (真实URL!)
    if data.get("amazon_products"):
        product_lines = []
        for p in data["amazon_products"][:40]:
            product_lines.append(
                f"- {p['title']} | {p['description']} | 品类: {p['category_code']} | URL: {p['url']}"
            )
        parts.append("## Amazon BSR产品 (真实链接)\n以下每个产品都包含真实的Amazon购买链接，请在source_links中引用这些URL：\n" + "\n".join(product_lines) + "\n")

    # YouTube视频 (真实URL!)
    if data.get("youtube_videos"):
        yt_lines = []
        for v in data["youtube_videos"][:20]:
            yt_lines.append(
                f"- {v['title']} | 热度: {v['hotness_score']} | {v['description'][:80]} | URL: {v['url']}"
            )
        parts.append("## YouTube热门视频 (真实链接)\n" + "\n".join(yt_lines) + "\n")

    # Reddit讨论 (真实URL!)
    if data.get("reddit_posts"):
        reddit_lines = []
        for r in data["reddit_posts"][:15]:
            reddit_lines.append(
                f"- {r['title']} | {r['description'][:80]} | URL: {r['url']}"
            )
        parts.append("## Reddit热门讨论 (真实链接)\n" + "\n".join(reddit_lines) + "\n")

    # 趋势信号
    if data.get("trend_signals"):
        trend_lines = []
        for t in data["trend_signals"][:40]:
            trend_lines.append(
                f"- [{t['platform']}] {t['keyword'] or ''} | 类型: {t['signal_type']} | "
                f"方向: {t['trend_direction']} | {t['summary'][:100]}"
            )
        parts.append("## 趋势信号\n" + "\n".join(trend_lines) + "\n")

    # 话题相关数据
    if data.get("topic_links"):
        topic_lines = []
        for l in data["topic_links"]:
            topic_lines.append(
                f"- [{l['platform']}] {l['title']} | {l['description'][:80]} | URL: {l['url']}"
            )
        parts.append(f"## 话题「{topic}」相关数据\n" + "\n".join(topic_lines) + "\n")

    if data.get("topic_trends"):
        tt_lines = [
            f"- [{t['platform']}] {t['keyword']} | 方向: {t['trend_direction']} | {t['summary'][:100]}"
            for t in data["topic_trends"]
        ]
        parts.append("## 话题相关趋势信号\n" + "\n".join(tt_lines) + "\n")

    # 如果话题没有数据，明确告诉LLM
    if topic and not data.get("topic_has_data", True):
        parts.append(
            f"\n## ⚠️ 数据库中暂无「{topic}」相关数据\n"
            f"请基于你的通用跨境电商知识分析「{topic}」市场：\n"
            f"- 市场规模与增长趋势\n"
            f"- Amazon上的竞争格局（头部品牌/价格带/评分分布）\n"
            f"- 选品机会点（差异化方向/痛点/空白）\n"
            f"- 建议采集哪些数据来验证（Amazon BSR/YouTube/Reddit/Google Trends关键词）\n"
            f"discoveries中可以给出基于通用知识的初步建议，reasoning注明「基于通用市场知识，待数据验证」，source_links留空。\n"
        )
    else:
        parts.append(
            "\n## ⚠️ 重要提醒\n"
            "在discoveries的source_links中，URL必须使用上述数据中已有的真实链接。"
            "不要编造任何URL或ASIN。如果某个发现没有对应的真实链接，source_links留空数组。"
        )

    return "\n".join(parts)


def call_llm(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 8000,
) -> dict[str, Any]:
    """调用LLM (OpenAI compatible API)。"""
    settings = get_settings()
    if not settings.llm_api_key:
        raise AgentError("LLM_API_KEY未配置，请在.env中设置")

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    import os
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")

    try:
        with httpx.Client(timeout=90.0, proxy=proxy) as client:
            resp = client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            # Some OpenAI-compatible gateways do not implement JSON mode. Fall
            # back to the strict prompt + parser retry path for those gateways.
            if resp.status_code in {400, 422}:
                fallback_payload = {key: value for key, value in payload.items() if key != "response_format"}
                resp = client.post(
                    f"{settings.llm_base_url}/chat/completions",
                    headers=headers,
                    json=fallback_payload,
                )
            if resp.status_code != 200:
                raise AgentError(f"LLM服务返回错误（HTTP {resp.status_code}）")

            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise AgentError("LLM服务返回了空内容")
            usage = result.get("usage", {})
            return {"content": content, "usage": usage}
    except AgentError:
        raise
    except httpx.HTTPError as exc:
        raise AgentError("LLM服务暂时不可用") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AgentError("LLM服务返回格式无效") from exc


def parse_discoveries(content: str) -> dict[str, Any]:
    """解析LLM输出的JSON分析报告。"""
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.IGNORECASE | re.DOTALL).strip()

    # 去掉 markdown code fence
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end = i
                break
        cleaned = "\n".join(lines[start:end])

    # 先尝试直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 尝试提取JSON对象 — 用括号匹配而非正则
    start = cleaned.find("{")
    if start < 0:
        raise AgentError("LLM输出中未找到有效JSON")

    # 括号匹配找到完整的JSON对象
    depth = 0
    in_string = False
    escape = False
    end = start
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    # 如果输出被截断，使用最后一个闭合括号作为候选结尾，便于给出明确错误。
    json_str = cleaned[start:end if end > start else len(cleaned)]
    candidates = [json_str, re.sub(r",\s*([}\]])", r"\1", json_str)]
    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc

    assert last_error is not None
    raise AgentError(
        "LLM输出JSON无效："
        f"{last_error.msg}（第{last_error.lineno}行，第{last_error.colno}列）"
    ) from last_error


REPAIR_PROMPT = """上一条响应无法被系统解析为 JSON。请重新输出完整结果。
只允许输出一个合法 JSON 对象，不要 Markdown 代码块、不要解释、不要前后缀文字。
所有字符串中的双引号、换行和反斜杠必须正确转义；必须包含 summary、market_overview、
discoveries、recommendations 四个字段。discoveries 中的 source_links 只能使用输入数据里的真实 URL。"""


def _call_and_parse_report(messages: list[dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Call the model and retry once when its structured response is invalid."""
    result = call_llm(messages, temperature=0.7, max_tokens=12000)
    try:
        return validate_report(parse_discoveries(result["content"])), result
    except AgentError as first_error:
        logger.warning("LLM结构化输出解析失败，准备重试：%s", first_error)

    retry_messages = [*messages, {"role": "user", "content": REPAIR_PROMPT}]
    retry_result = call_llm(retry_messages, temperature=0.2, max_tokens=12000)
    try:
        return validate_report(parse_discoveries(retry_result["content"])), retry_result
    except AgentError as retry_error:
        raise AgentError(f"LLM输出格式无效，自动重试后仍失败：{retry_error}") from retry_error


ALLOWED_OPPORTUNITY_TYPES = {
    "hot_product",
    "rising_trend",
    "gap_opportunity",
    "emerging_category",
}


def validate_report(report: Any) -> dict[str, Any]:
    """Validate and normalize the model response before writing discoveries."""
    if not isinstance(report, dict):
        raise AgentError("LLM输出必须是JSON对象")

    raw_discoveries = report.get("discoveries", [])
    if raw_discoveries is None:
        raw_discoveries = []
    if not isinstance(raw_discoveries, list):
        raise AgentError("LLM输出中的 discoveries 必须是数组")

    discoveries: list[dict[str, Any]] = []
    for raw in raw_discoveries:
        if not isinstance(raw, dict):
            raise AgentError("LLM输出中的 discovery 格式无效")

        product_name = str(raw.get("product_name") or "").strip()
        opportunity_type = str(raw.get("opportunity_type") or "").strip()
        if not product_name or opportunity_type not in ALLOWED_OPPORTUNITY_TYPES:
            raise AgentError("LLM输出中的 discovery 缺少有效字段")

        try:
            score = float(raw.get("opportunity_score", 0) or 0)
        except (TypeError, ValueError) as exc:
            raise AgentError("LLM输出中的 opportunity_score 无效") from exc
        if not math.isfinite(score) or not 0 <= score <= 100:
            raise AgentError("LLM输出中的 opportunity_score 超出范围")

        keywords = raw.get("keywords", []) or []
        if not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords):
            raise AgentError("LLM输出中的 keywords 格式无效")
        market_signals = raw.get("market_signals", {}) or {}
        if not isinstance(market_signals, dict):
            raise AgentError("LLM输出中的 market_signals 格式无效")
        source_links = raw.get("source_links", []) or []
        if not isinstance(source_links, list) or not all(isinstance(item, dict) for item in source_links):
            raise AgentError("LLM输出中的 source_links 格式无效")
        normalized_links = []
        for link in source_links[:20]:
            url = str(link.get("url") or "").strip()
            if not url:
                continue
            normalized_links.append(
                {
                    "title": str(link.get("title") or "")[:500],
                    "url": url[:2000],
                    "platform": str(link.get("platform") or "other")[:40],
                }
            )

        discoveries.append(
            {
                "product_name": product_name[:500],
                "category_code": str(raw.get("category_code") or "").strip()[:80] or None,
                "opportunity_type": opportunity_type,
                "opportunity_score": score,
                "reasoning": str(raw.get("reasoning") or "")[:10000],
                "market_signals": market_signals,
                "keywords": [item[:200] for item in keywords[:50]],
                "source_links": normalized_links,
            }
        )

    report["discoveries"] = discoveries
    report["summary"] = str(report.get("summary") or "")[:10000]
    recommendations = report.get("recommendations", []) or []
    report["recommendations"] = (
        [str(item)[:1000] for item in recommendations[:20]] if isinstance(recommendations, list) else []
    )
    report["market_overview"] = (
        report.get("market_overview", {})
        if isinstance(report.get("market_overview", {}), dict)
        else {}
    )
    return report


def _validate_and_fix_links(discoveries: list[dict], data: dict[str, Any]) -> list[dict]:
    """验证discoveries中的URL是否来自数据库真实数据。

    如果LLM编造了URL，移除该URL，确保不出现假链接；如果模型漏填链接，
    则按发现名称和关键词从本次分析使用的真实数据库链接中补回相关来源。
    """
    # 收集所有真实URL
    real_urls: set[str] = set()
    for p in data.get("amazon_products", []):
        if p.get("url"):
            real_urls.add(p["url"])
    for v in data.get("youtube_videos", []):
        if v.get("url"):
            real_urls.add(v["url"])
    for r in data.get("reddit_posts", []):
        if r.get("url"):
            real_urls.add(r["url"])
    for l in data.get("topic_links", []):
        if l.get("url"):
            real_urls.add(l["url"])

    for d in discoveries:
        valid_links = []
        for link in d.get("source_links", []):
            url = link.get("url", "")
            if url in real_urls:
                valid_links.append(link)
            else:
                logger.warning(f"过滤幻觉URL: {url[:80]}")
        fallback_links = _fallback_source_links(d, data)
        linked_urls = {link["url"] for link in valid_links}
        for link in fallback_links:
            if link["url"] not in linked_urls:
                valid_links.append(link)
                linked_urls.add(link["url"])
        d["source_links"] = valid_links[:20]

    return discoveries


_SOURCE_CANDIDATE_KEYS = ("amazon_products", "youtube_videos", "reddit_posts", "topic_links")
_GENERIC_SOURCE_TERMS = {
    "a", "an", "and", "app", "based", "best", "controlled", "device", "enabled",
    "for", "from", "in", "new", "of", "product", "rechargeable", "the", "unit",
    "with",
}


def _source_tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _fallback_source_links(discovery: dict[str, Any], data: dict[str, Any], limit: int = 3) -> list[dict[str, str]]:
    """Select matching URLs from the already-collected source data.

    This is intentionally conservative: a candidate must share at least two
    meaningful title/keyword tokens with the discovery. It never creates a URL.
    """
    discovery_terms = (
        _source_tokens(discovery.get("product_name"))
        | _source_tokens(" ".join(discovery.get("keywords", []) or []))
    ) - _GENERIC_SOURCE_TERMS
    if len(discovery_terms) < 2:
        return []

    candidates: dict[str, tuple[int, dict[str, str]]] = {}
    for key in _SOURCE_CANDIDATE_KEYS:
        platform_default = {
            "amazon_products": "amazon",
            "youtube_videos": "youtube",
            "reddit_posts": "reddit",
            "topic_links": "other",
        }[key]
        for item in data.get(key, []) or []:
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            title = str(item.get("title") or "").strip()
            description = str(item.get("description") or "").strip()
            title_terms = _source_tokens(title) - _GENERIC_SOURCE_TERMS
            candidate_terms = title_terms | _source_tokens(description)
            title_overlap = discovery_terms & title_terms
            overlap = discovery_terms & candidate_terms
            if len(title_overlap) < 1 or len(overlap) < 2:
                continue
            score = len(overlap) * 2 + len(title_overlap)
            if discovery.get("category_code") and item.get("category_code") == discovery["category_code"]:
                score += 2
            candidates[url] = (
                max(score, candidates.get(url, (0, {}))[0]),
                {
                    "title": title[:500],
                    "url": url[:2000],
                    "platform": str(item.get("platform") or platform_default)[:40],
                },
            )

    ranked = sorted(candidates.values(), key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:limit]]


# ---------------------------------------------------------------------------
# 扫描执行
# ---------------------------------------------------------------------------

def run_scan(
    db: Session,
    *,
    scan_type: str = "full",
    category_code: str | None = None,
    topic: str | None = None,
    actor: str = "system",
) -> AgentScan:
    """执行一次选品扫描。"""
    scan = AgentScan(
        scan_type=scan_type,
        category_code=category_code,
        topic=topic,
        status="running",
        triggered_by=actor,
        report={},
        data_snapshot={},
        stats={},
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        # 1. 收集数据
        data = collect_data(db, category_code=category_code, topic=topic)
        scan.data_snapshot = {
            "categories_count": len(data.get("categories", [])),
            "amazon_products_count": len(data.get("amazon_products", [])),
            "youtube_videos_count": len(data.get("youtube_videos", [])),
            "reddit_posts_count": len(data.get("reddit_posts", [])),
            "trends_count": len(data.get("trend_signals", [])),
        }
        scan.stats = {
            "products_analyzed": len(data.get("amazon_products", [])),
            "videos_analyzed": len(data.get("youtube_videos", [])),
            "posts_analyzed": len(data.get("reddit_posts", [])),
            "trends_analyzed": len(data.get("trend_signals", [])),
        }
        db.flush()

        # 2. 构建prompt
        user_prompt = build_analysis_prompt(data, topic=topic)

        # 3. 调用LLM
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        # 4. 解析结果；模型偶发输出非法 JSON 时自动重试一次
        report, result = _call_and_parse_report(messages)

        # 5. 验证链接 — 过滤掉LLM编造的URL
        discoveries_data = report.get("discoveries", [])
        discoveries_data = _validate_and_fix_links(discoveries_data, data)
        known_category_codes = {
            category["code"]
            for category in data.get("categories", [])
            if isinstance(category, dict) and category.get("code")
        }
        known_category_codes.update(
            child["code"]
            for category in data.get("categories", [])
            if isinstance(category, dict)
            for child in category.get("children", [])
            if isinstance(child, dict) and child.get("code")
        )

        scan.report = {
            "summary": report.get("summary", ""),
            "market_overview": report.get("market_overview", {}),
            "recommendations": report.get("recommendations", []),
        }

        # 6. 创建ProductDiscovery记录
        for d in discoveries_data:
            discovery_category = d.get("category_code")
            if discovery_category not in known_category_codes:
                discovery_category = category_code if category_code in known_category_codes else None
            discovery = ProductDiscovery(
                scan_id=scan.id,
                product_name=d.get("product_name", ""),
                category_code=discovery_category,
                opportunity_type=d.get("opportunity_type", "hot_product"),
                opportunity_score=float(d.get("opportunity_score", 0)),
                reasoning=d.get("reasoning", ""),
                market_signals=d.get("market_signals", {}),
                keywords=d.get("keywords", []),
                source_links=d.get("source_links", []),
                status="new",
            )
            db.add(discovery)

        # 7. 保存初始对话消息
        db.add(AgentMessage(
            scan_id=scan.id,
            role="user",
            content=f"[扫描触发] 类型: {scan_type}, 品类: {category_code or '全站'}, 话题: {topic or '无'}",
            metadata_json={"scan_type": scan_type, "category_code": category_code, "topic": topic},
        ))
        # 生成一条AI总结消息（用于对话上下文）
        ai_summary = f"## 扫描完成\n\n{report.get('summary', '')}\n\n"
        ai_summary += f"分析了 {len(data.get('amazon_products', []))} 个Amazon产品、"
        ai_summary += f"{len(data.get('youtube_videos', []))} 个YouTube视频、"
        ai_summary += f"{len(data.get('reddit_posts', []))} 个Reddit讨论、"
        ai_summary += f"{len(data.get('trend_signals', []))} 条趋势信号。\n\n"
        ai_summary += f"发现了 {len(discoveries_data)} 个选品机会。你可以在「发现」标签页查看详情，或者在这里问我任何问题。"

        db.add(AgentMessage(
            scan_id=scan.id,
            role="assistant",
            content=ai_summary,
            metadata_json={
                "model": get_settings().llm_model,
                "usage": result.get("usage", {}),
                "is_scan_result": True,
            },
        ))

        scan.status = "completed"
        scan.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(scan)

    except Exception as exc:
        scan_id = scan.id
        data_snapshot = dict(scan.data_snapshot or {})
        stats = dict(scan.stats or {})
        db.rollback()
        failed_scan = db.get(AgentScan, scan_id)
        if failed_scan is not None:
            failed_scan.status = "failed"
            failed_scan.error_message = str(exc)[:500]
            failed_scan.data_snapshot = data_snapshot
            failed_scan.stats = stats
            failed_scan.completed_at = datetime.now(UTC)
            db.commit()
            db.refresh(failed_scan)
            scan = failed_scan
        logger.exception("选品Agent扫描失败")
        raise AgentError(f"选品Agent扫描失败：{str(exc)[:240]}") from exc


# ---------------------------------------------------------------------------
# 对话 — 真正的多轮对话
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """你是一个专业的跨境电商选品助手。用户刚完成了一次选品扫描，你可以基于扫描结果回答用户的问题。

你的能力：
1. 解答关于扫描发现的任何问题（产品、品类、趋势、机会评分等）
2. 对比分析不同产品的优劣势
3. 深入分析某个机会点的市场前景
4. 给出选品建议和行动方案
5. 解释评分逻辑和数据来源

注意事项：
- 回答要基于扫描数据，不要编造数据
- 如果用户问的数据不在扫描结果中，坦诚告知
- 回答简洁有力，用要点列表而非大段文字
- 可以用Markdown格式（标题、加粗、列表）
"""


def chat(
    db: Session,
    scan_id: int,
    user_message: str,
) -> dict[str, Any]:
    """在已有扫描会话基础上进行真正的多轮对话。

    不是返回扫描摘要，而是基于用户的实际问题进行对话式回答。
    """
    scan = db.get(AgentScan, scan_id)
    if scan is None:
        raise AgentError(f"扫描会话 {scan_id} 不存在")

    # 收集历史对话消息（最近20条）
    history = db.scalars(
        select(AgentMessage).where(AgentMessage.scan_id == scan_id).order_by(AgentMessage.id)
    ).all()

    # 构建对话上下文
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]

    # 添加扫描报告摘要作为上下文
    if scan.report:
        report_ctx = f"## 扫描报告摘要\n{scan.report.get('summary', '')}\n"
        if scan.report.get("recommendations"):
            report_ctx += "\n## 行动建议\n" + "\n".join(f"- {r}" for r in scan.report["recommendations"])
        messages.append({"role": "system", "content": report_ctx})

    # 添加discoveries作为上下文
    discoveries = db.scalars(
        select(ProductDiscovery).where(ProductDiscovery.scan_id == scan_id).order_by(
            ProductDiscovery.opportunity_score.desc()
        )
    ).all()
    if discoveries:
        disc_ctx = "## 发现的选品机会\n"
        for d in discoveries:
            disc_ctx += f"\n### {d.product_name}\n"
            disc_ctx += f"- 类型: {d.opportunity_type} | 评分: {d.opportunity_score}\n"
            disc_ctx += f"- 理由: {d.reasoning}\n"
            if d.market_signals:
                disc_ctx += f"- 市场信号: {json.dumps(d.market_signals, ensure_ascii=False)}\n"
            if d.keywords:
                disc_ctx += f"- 关键词: {', '.join(d.keywords)}\n"
        messages.append({"role": "system", "content": disc_ctx})

    # 添加历史对话（最近20条，跳过第一条扫描触发消息）
    recent = [m for m in history if not m.metadata_json.get("is_scan_result")][-20:]
    for msg in recent:
        messages.append({"role": msg.role, "content": msg.content[:4000]})

    # 添加用户新消息
    messages.append({"role": "user", "content": user_message})

    # 保存用户消息
    db.add(AgentMessage(
        scan_id=scan_id,
        role="user",
        content=user_message,
        metadata_json={},
    ))
    db.flush()

    # 调用LLM
    result = call_llm(messages, temperature=0.6, max_tokens=4000)

    # 保存回复
    db.add(AgentMessage(
        scan_id=scan_id,
        role="assistant",
        content=result["content"],
        metadata_json={
            "model": get_settings().llm_model,
            "usage": result.get("usage", {}),
        },
    ))
    db.commit()

    return {
        "content": result["content"],
        "usage": result.get("usage", {}),
    }
