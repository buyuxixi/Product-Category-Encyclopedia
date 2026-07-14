from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Category, EncyclopediaSection, HotLink, TrendSignal
from app.services.agent_service import AgentError, call_llm
from app.services.content_service import ContentError


MARKET_BRIEF_SYSTEM_PROMPT = """你是产品品类研究分析师。请根据提供的真实热点链接和趋势信号，
生成“06 舆情与市场趋势”的简短摘要。

规则：
1. 只输出 Markdown 正文，不使用 JSON，也不要用代码围栏包裹全文。
2. 只输出 3 条简洁要点，分别概括市场热度、用户关注和趋势判断。
3. 每条格式必须是 `- **维度**：完整结论`，维度依次为“市场热度”“用户关注”“趋势判断”。
4. 不得编造数字、品牌、结论或 URL；引用链接只能使用上下文中的真实 URL。
5. 数据不足时明确说明覆盖限制，不要用常识补造事实。
6. 每条只保留一个完整句子，并用 `**关键词**` 加粗 1-3 个关键短语。
7. 不要输出标题、链接或省略号，不要逐条复述原始卡片，也不要截断句子。
8. 摘要只用于辅助阅读，不能替代或改写已有分析正文。
"""

_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_AI_SUMMARY_WRAPPER = re.compile(
    r"\A## 🤖 AI 生成摘要\n.*?\n---\n\n## 原始分析正文\n",
    re.DOTALL,
)
SUMMARY_REPAIR_PROMPT = """上一条摘要格式不符合要求。请重新输出且只输出 3 条 Markdown 列表：
- **市场热度**：一个完整短句
- **用户关注**：一个完整短句
- **趋势判断**：一个完整短句
每条加粗 1-3 个重点关键词，不要标题、链接、省略号或额外解释。"""


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def _remove_unverified_links(content: str, allowed_urls: set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        label, url = match.groups()
        return match.group(0) if url in allowed_urls else label

    return _MARKDOWN_LINK.sub(replace, content)


def _original_content(content: str) -> str:
    return _AI_SUMMARY_WRAPPER.sub("", content, count=1)


def _normalize_summary(content: str) -> str | None:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) != 3:
        return None
    expected_labels = ("市场热度", "用户关注", "趋势判断")
    normalized = []
    for line, label in zip(lines, expected_labels, strict=True):
        match = re.match(r"^(?:[-*+]|\d+\.)\s+(.+)$", line)
        if not match:
            return None
        text = match.group(1)
        if not text.startswith(f"**{label}**") or text.count("**") < 4:
            return None
        if "…" in text or "http://" in text or "https://" in text:
            return None
        normalized.append(f"- {text}")
    return "\n".join(normalized)


def _generate_summary(
    messages: list[dict[str, str]],
    allowed_urls: set[str],
) -> str:
    response = call_llm(
        messages,
        temperature=0.4,
        max_tokens=600,
        json_mode=False,
    )
    content = _remove_unverified_links(
        _strip_code_fence(response["content"]),
        allowed_urls,
    )
    summary = _normalize_summary(content)
    if summary is not None:
        return summary

    retry = call_llm(
        [*messages, {"role": "user", "content": SUMMARY_REPAIR_PROMPT}],
        temperature=0.2,
        max_tokens=600,
        json_mode=False,
    )
    repaired = _remove_unverified_links(
        _strip_code_fence(retry["content"]),
        allowed_urls,
    )
    summary = _normalize_summary(repaired)
    if summary is None:
        raise AgentError("LLM摘要格式无效，自动重试后仍失败")
    return summary


def _market_context(
    db: Session,
    category: Category,
) -> tuple[dict[str, object], set[str]]:
    cutoff = datetime.now(UTC) - timedelta(days=30)
    hot_links = db.scalars(
        select(HotLink)
        .where(HotLink.category_id == category.id)
        .order_by(
            HotLink.is_hot.desc(),
            HotLink.hotness_score.desc(),
            HotLink.collected_at.desc(),
        )
        .limit(40)
    ).all()
    trend_signals = db.scalars(
        select(TrendSignal)
        .where(
            TrendSignal.category_id == category.id,
            TrendSignal.collected_at >= cutoff,
        )
        .order_by(
            TrendSignal.collected_at.desc(),
            TrendSignal.metric_value.desc(),
        )
        .limit(40)
    ).all()
    context = {
        "category": {
            "code": category.code,
            "name": category.name,
            "description": (category.description or "")[:500],
        },
        "hot_links": [
            {
                "platform": item.platform,
                "link_type": item.link_type,
                "title": item.title_zh or item.title,
                "description": (item.description_zh or item.description or "")[:500],
                "hotness_score": item.hotness_score,
                "is_hot": item.is_hot,
                "url": item.url,
            }
            for item in hot_links
        ],
        "trend_signals": [
            {
                "platform": item.platform,
                "signal_type": item.signal_type,
                "keyword": item.keyword,
                "title": item.title_zh or item.title,
                "metric_value": item.metric_value,
                "metric_unit": item.metric_unit,
                "trend_direction": item.trend_direction,
                "summary": (item.summary_zh or item.summary or "")[:500],
            }
            for item in trend_signals
        ],
    }
    return context, {item.url for item in hot_links if item.url}


def generate_market_brief(
    db: Session,
    *,
    category: Category,
    actor: str,
) -> EncyclopediaSection:
    section = db.scalar(
        select(EncyclopediaSection).where(
            EncyclopediaSection.category_id == category.id,
            EncyclopediaSection.section_key == "market",
        )
    )
    if section is None:
        raise ContentError("Unknown encyclopedia section")
    if section.locked_by_human and section.content.strip():
        raise ContentError(
            "Human-edited section is locked; apply the suggestion manually"
        )

    context, allowed_urls = _market_context(db, category)
    messages = [
        {"role": "system", "content": MARKET_BRIEF_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "请根据以下当前品类数据生成摘要：\n\n"
                + json.dumps(context, ensure_ascii=False, indent=2)
            ),
        },
    ]
    content = _generate_summary(messages, allowed_urls)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    original_content = _original_content(section.content)
    section.content = (
        "## 🤖 AI 生成摘要\n"
        f"> 生成时间：{today} · 以下内容由 AI 基于当前热点与趋势信号生成\n\n"
        f"{content}\n\n"
        "---\n\n"
        "## 原始分析正文\n"
        f"{original_content}"
    )
    section.generation_mode = "generated"
    section.locked_by_human = False
    section.updated_by = actor
    db.add(
        AuditEvent(
            actor=actor,
            action="section_summary_generated",
            entity_type="encyclopedia_section",
            entity_id=str(section.id),
            metadata_json={"section_key": "market", "mode": "generated"},
        )
    )
    db.commit()
    db.refresh(section)
    return section
