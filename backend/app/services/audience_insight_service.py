from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AuditEvent,
    Category,
    EncyclopediaSection,
    EvidenceLink,
    HotLink,
    TrendSignal,
)
from app.services.agent_service import AgentError, call_llm
from app.services.content_service import ContentError


AUDIENCE_INSIGHT_SYSTEM_PROMPT = """你是产品用户研究分析师。请基于给定的真实 user_pain_point
信号和原帖，聚类提取用户画像、使用场景和 Top 用户痛点。

规则：
1. 只输出 JSON，不得补充解释。
2. personas 和 pain_points 各输出 1-5 项，按重要性排序。
3. 只归纳输入数据明确支持的结论；数据不足时减少条目，不使用常识补造。
4. 每项必须提供 1-3 个 evidence_ids，且只能引用 source_candidates 中的 id。
5. evidence_ids 必须指向直接支持该条结论的原帖。

输出结构：
{
  "personas": [
    {
      "name": "画像名称",
      "traits": "典型特征",
      "scenarios": "使用场景",
      "needs": "核心诉求",
      "evidence_ids": [原帖ID]
    }
  ],
  "pain_points": [
    {
      "name": "痛点名称",
      "description": "痛点描述",
      "scenarios": "影响场景",
      "opportunity": "需求机会",
      "evidence_ids": [原帖ID]
    }
  ]
}"""

REPAIR_PROMPT = """上一条响应格式无效。请严格按要求重新输出完整 JSON：
personas 和 pain_points 必须是数组；每项字段齐全；每项 evidence_ids 必须包含
1-3 个 source_candidates 中存在的整数 ID。不要输出 Markdown 或额外解释。"""

_URL_RE = re.compile(r"https?://[^\s）)]+")
_TOKEN_RE = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)
_STOP_WORDS = {
    "analysis",
    "comment",
    "comments",
    "review",
    "youtube",
    "pain",
    "user",
}


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def _best_source(signal: TrendSignal, sources: list[HotLink]) -> HotLink | None:
    urls = _URL_RE.findall(f"{signal.title}\n{signal.summary}")
    for url in urls:
        normalized = url.rstrip("。.,，")
        match = next((source for source in sources if source.url == normalized), None)
        if match is not None:
            return match

    candidates = [source for source in sources if source.platform == signal.platform]
    if not candidates:
        return None
    signal_tokens = {
        token
        for token in _TOKEN_RE.findall(f"{signal.title} {signal.keyword}".lower())
        if token not in _STOP_WORDS
    }
    ranked = sorted(
        candidates,
        key=lambda source: (
            len(signal_tokens & set(_TOKEN_RE.findall(source.title.lower()))),
            source.hotness_score or 0,
        ),
        reverse=True,
    )
    return ranked[0]


def _build_context(
    db: Session,
    category: Category,
) -> tuple[dict[str, object], dict[int, HotLink]]:
    cutoff = datetime.now(UTC) - timedelta(days=90)
    signals = db.scalars(
        select(TrendSignal)
        .where(
            TrendSignal.category_id == category.id,
            TrendSignal.signal_type == "user_pain_point",
            TrendSignal.platform.in_(("reddit", "xiaohongshu", "youtube")),
            TrendSignal.collected_at >= cutoff,
        )
        .order_by(TrendSignal.metric_value.desc(), TrendSignal.collected_at.desc())
        .limit(50)
    ).all()
    sources = db.scalars(
        select(HotLink)
        .where(
            HotLink.category_id == category.id,
            HotLink.platform.in_(("reddit", "xiaohongshu", "youtube")),
        )
        .order_by(HotLink.is_hot.desc(), HotLink.hotness_score.desc())
        .limit(40)
    ).all()
    if not signals or not sources:
        raise ContentError("No user pain point signals with source posts are available")

    source_by_id = {source.id: source for source in sources}
    signal_payload = []
    for signal in signals:
        source = _best_source(signal, sources)
        signal_payload.append(
            {
                "id": signal.id,
                "platform": signal.platform,
                "keyword": signal.keyword,
                "title": signal.title_zh or signal.title,
                "summary": (signal.summary_zh or signal.summary or "")[:800],
                "metric_value": signal.metric_value,
                "metric_unit": signal.metric_unit,
                "source_id": source.id if source else None,
            }
        )
    context = {
        "category": {
            "code": category.code,
            "name": category.name,
            "description": category.description,
        },
        "pain_point_signals": signal_payload,
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
    return context, source_by_id


def _clean_text(value: object, *, max_length: int = 500) -> str:
    text = re.sub(r"[*_#`<>]", "", str(value or "")).strip()
    return text[:max_length]


def _parse_items(
    value: object,
    *,
    fields: tuple[str, ...],
    allowed_source_ids: set[int],
) -> list[dict[str, object]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 5:
        raise ValueError("expected 1-5 insight items")
    result = []
    for raw in value:
        if not isinstance(raw, dict):
            raise ValueError("insight item must be an object")
        item = {field: _clean_text(raw.get(field)) for field in fields}
        if not all(item.values()):
            raise ValueError("insight item fields cannot be empty")
        evidence_ids = raw.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            raise ValueError("evidence_ids must be an array")
        valid_ids = list(
            dict.fromkeys(
                int(source_id)
                for source_id in evidence_ids
                if isinstance(source_id, int) and source_id in allowed_source_ids
            )
        )[:3]
        if not valid_ids:
            raise ValueError("each insight needs valid evidence")
        item["evidence_ids"] = valid_ids
        result.append(item)
    return result


def _parse_response(
    content: str,
    allowed_source_ids: set[int],
) -> dict[str, list[dict[str, object]]]:
    payload = json.loads(_strip_code_fence(content))
    if not isinstance(payload, dict):
        raise ValueError("response must be an object")
    return {
        "personas": _parse_items(
            payload.get("personas"),
            fields=("name", "traits", "scenarios", "needs"),
            allowed_source_ids=allowed_source_ids,
        ),
        "pain_points": _parse_items(
            payload.get("pain_points"),
            fields=("name", "description", "scenarios", "opportunity"),
            allowed_source_ids=allowed_source_ids,
        ),
    }


def _call_and_parse(
    messages: list[dict[str, str]],
    allowed_source_ids: set[int],
) -> dict[str, list[dict[str, object]]]:
    response = call_llm(messages, temperature=0.3, max_tokens=3000, json_mode=True)
    try:
        return _parse_response(response["content"], allowed_source_ids)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        retry = call_llm(
            [*messages, {"role": "user", "content": REPAIR_PROMPT}],
            temperature=0.1,
            max_tokens=3000,
            json_mode=True,
        )
        try:
            return _parse_response(retry["content"], allowed_source_ids)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AgentError("LLM用户洞察格式无效，自动重试后仍失败") from exc


def _evidence_markdown(
    evidence_ids: list[int],
    source_by_id: dict[int, HotLink],
) -> str:
    links = []
    for source_id in evidence_ids:
        source = source_by_id[source_id]
        title = _clean_text(source.title_zh or source.title, max_length=80)
        links.append(f"[{title}]({source.url})")
    return " · ".join(links)


def _users_markdown(
    personas: list[dict[str, object]],
    source_by_id: dict[int, HotLink],
) -> str:
    lines = ["> 🤖 **AI 智能提取**：基于当前社区讨论与评论信号聚类生成", "", "### 2.1 核心用户画像", ""]
    for index, item in enumerate(personas, 1):
        evidence_ids = item["evidence_ids"]
        lines.extend(
            [
                f"{index}. **{item['name']}**",
                f"   - 特征：{item['traits']}",
                f"   - 使用场景：{item['scenarios']}",
                f"   - 核心诉求：{item['needs']}",
                f"   - 证据：{_evidence_markdown(evidence_ids, source_by_id)}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _needs_markdown(
    pain_points: list[dict[str, object]],
    source_by_id: dict[int, HotLink],
) -> str:
    lines = ["> 🤖 **AI 智能提取**：基于当前社区讨论与评论信号聚类生成", "", "### 3.1 Top 用户痛点", ""]
    for index, item in enumerate(pain_points, 1):
        evidence_ids = item["evidence_ids"]
        lines.extend(
            [
                f"{index}. **{item['name']}**",
                f"   - 痛点描述：{item['description']}",
                f"   - 影响场景：{item['scenarios']}",
                f"   - 需求机会：{item['opportunity']}",
                f"   - 证据：{_evidence_markdown(evidence_ids, source_by_id)}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _replace_hot_link_evidence(
    section: EncyclopediaSection,
    source_ids: set[int],
) -> None:
    section.evidence[:] = [
        evidence for evidence in section.evidence if evidence.source_type != "hot_link"
    ]
    for source_id in sorted(source_ids):
        section.evidence.append(
            EvidenceLink(
                source_type="hot_link",
                source_id=source_id,
                locator="LLM user insight evidence",
            )
        )


def generate_audience_insights(
    db: Session,
    *,
    category: Category,
    actor: str,
) -> list[EncyclopediaSection]:
    sections = db.scalars(
        select(EncyclopediaSection)
        .options(selectinload(EncyclopediaSection.evidence))
        .where(
            EncyclopediaSection.category_id == category.id,
            EncyclopediaSection.section_key.in_(("users", "needs")),
        )
    ).all()
    section_by_key = {section.section_key: section for section in sections}
    if set(section_by_key) != {"users", "needs"}:
        raise ContentError("User and needs sections are required")
    locked = [
        section.title
        for section in sections
        if section.locked_by_human and section.content.strip()
    ]
    if locked:
        raise ContentError(f"Human-edited sections are locked: {', '.join(locked)}")
    existing = [section.title for section in sections if section.content.strip()]
    if existing:
        raise ContentError(
            "Existing section content is protected and cannot be overwritten: "
            + ", ".join(existing)
        )

    context, source_by_id = _build_context(db, category)
    messages = [
        {"role": "system", "content": AUDIENCE_INSIGHT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "请根据以下真实数据提取用户画像和 Top 痛点：\n\n"
            + json.dumps(context, ensure_ascii=False, indent=2),
        },
    ]
    insights = _call_and_parse(messages, set(source_by_id))
    users = section_by_key["users"]
    needs = section_by_key["needs"]
    users.content = _users_markdown(insights["personas"], source_by_id)
    needs.content = _needs_markdown(insights["pain_points"], source_by_id)

    for section, items in (
        (users, insights["personas"]),
        (needs, insights["pain_points"]),
    ):
        source_ids = {
            source_id
            for item in items
            for source_id in item["evidence_ids"]
        }
        section.generation_mode = "generated"
        section.locked_by_human = False
        section.updated_by = actor
        _replace_hot_link_evidence(section, source_ids)
        db.add(
            AuditEvent(
                actor=actor,
                action="audience_insights_generated",
                entity_type="encyclopedia_section",
                entity_id=str(section.id),
                metadata_json={
                    "section_key": section.section_key,
                    "evidence_count": len(source_ids),
                },
            )
        )
    db.commit()
    for section in sections:
        db.refresh(section)
    return sections
