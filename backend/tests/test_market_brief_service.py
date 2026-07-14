from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from app.api import router
from app.models import Category, EncyclopediaSection, HotLink, TrendSignal
from app.services import market_brief_service
from app.services.agent_service import AgentError
from app.services.content_service import ContentError, save_section


def _category_and_market_section(db):
    category = db.scalar(
        select(Category).where(Category.code == "TENS_THERAPY")
    )
    assert category is not None
    section = db.scalar(
        select(EncyclopediaSection).where(
            EncyclopediaSection.category_id == category.id,
            EncyclopediaSection.section_key == "market",
        )
    )
    assert section is not None
    return category, section


def test_generate_section_route_is_registered():
    assert any(
        route.path == "/api/v1/categories/{code}/generate-section"
        and "POST" in route.methods
        for route in router.routes
    )


def test_generate_market_brief_uses_current_data_and_saves_generated(db, monkeypatch):
    category, section = _category_and_market_section(db)
    original_content = "### 6.1 原始市场数据\n\n这段正文必须保留。"
    section.content = original_content
    db.commit()
    source_url = "https://example.com/real"
    db.add_all(
        [
            HotLink(
                category_id=category.id,
                section_key="market",
                link_type="social_post",
                platform="xiaohongshu",
                title="热门理疗仪讨论",
                url=source_url,
                description="用户关注档位和安全性",
                hotness_score=100,
                is_hot=True,
            ),
            TrendSignal(
                category_id=category.id,
                section_key="market",
                signal_type="user_pain_point",
                platform="xiaohongshu",
                keyword="理疗仪档位",
                title="新手不知道如何选择档位",
                metric_value=30,
                metric_unit="likes",
                trend_direction="up",
                summary="安全使用讨论增加",
            ),
        ]
    )
    db.commit()
    captured: dict[str, object] = {}

    def fake_call(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return {
            "content": (
                "```markdown\n"
                "- **市场热度**：讨论集中在**安全使用**。\n"
                "- **用户关注**：用户重点关注**档位选择**。\n"
                "- **趋势判断**：相关讨论呈现**上升趋势**。\n"
                "```"
            ),
            "usage": {"total_tokens": 10},
        }

    monkeypatch.setattr(market_brief_service, "call_llm", fake_call)

    saved = market_brief_service.generate_market_brief(
        db,
        category=category,
        actor="researcher",
    )

    prompt = captured["messages"][1]["content"]
    context = json.loads(prompt.split("\n\n", 1)[1])
    assert context["hot_links"][0]["url"] == source_url
    assert context["trend_signals"][0]["keyword"] == "理疗仪档位"
    assert captured["kwargs"]["json_mode"] is False
    assert saved.generation_mode == "generated"
    assert saved.locked_by_human is False
    assert saved.content.startswith("## 🤖 AI 生成摘要")
    assert saved.content.endswith(original_content)
    assert saved.content.count(original_content) == 1
    assert "## 原始分析正文" in saved.content
    summary = saved.content.split("---", 1)[0]
    assert "**安全使用**" in summary
    assert "…" not in summary


def test_generate_market_brief_checks_human_lock_before_llm(db, monkeypatch):
    category, section = _category_and_market_section(db)
    save_section(
        db,
        category=category,
        section_key=section.section_key,
        content="人工分析内容",
        generation_mode="human",
        actor="researcher",
    )
    monkeypatch.setattr(
        market_brief_service,
        "call_llm",
        lambda *args, **kwargs: pytest.fail("locked section must not call LLM"),
    )

    with pytest.raises(ContentError, match="locked"):
        market_brief_service.generate_market_brief(
            db,
            category=category,
            actor="researcher",
        )


def test_llm_failure_preserves_existing_generated_content(db, monkeypatch):
    category, section = _category_and_market_section(db)
    section.content = "已有自动分析"
    section.generation_mode = "generated"
    db.commit()
    monkeypatch.setattr(
        market_brief_service,
        "call_llm",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AgentError("LLM服务暂时不可用")
        ),
    )

    with pytest.raises(AgentError, match="暂时不可用"):
        market_brief_service.generate_market_brief(
            db,
            category=category,
            actor="researcher",
        )

    db.refresh(section)
    assert section.content == "已有自动分析"
    assert section.generation_mode == "generated"


def test_regeneration_replaces_only_existing_ai_summary(db, monkeypatch):
    category, section = _category_and_market_section(db)
    original_content = "### 6.1 原始数据\n\n原文保持不变。"
    section.content = (
        "## 🤖 AI 生成摘要\n"
        "> 生成时间：2026-07-13 · 以下内容由 AI 基于当前热点与趋势信号生成\n\n"
        "- 旧摘要\n\n"
        "---\n\n"
        "## 原始分析正文\n"
        f"{original_content}"
    )
    db.commit()
    monkeypatch.setattr(
        market_brief_service,
        "call_llm",
        lambda *args, **kwargs: {
            "content": (
                "- **市场热度**：出现**新摘要**。\n"
                "- **用户关注**：出现**新摘要**。\n"
                "- **趋势判断**：出现**新摘要**。"
            ),
            "usage": {},
        },
    )

    saved = market_brief_service.generate_market_brief(
        db,
        category=category,
        actor="researcher",
    )

    assert "旧摘要" not in saved.content
    assert saved.content.count("## 🤖 AI 生成摘要") == 1
    assert saved.content.count("## 原始分析正文") == 1
    assert saved.content.endswith(original_content)


def test_normalize_summary_preserves_complete_highlighted_text():
    long_text = "完整展示这段较长的摘要内容，不应在服务端被截断或添加省略号"
    summary = market_brief_service._normalize_summary(
        f"- **市场热度**：**{long_text}**。\n"
        "- **用户关注**：重点关注**安全与价格**。\n"
        "- **趋势判断**：整体保持**稳定增长**。"
    )

    assert summary is not None
    assert long_text in summary
    assert "…" not in summary


def test_invalid_summary_format_retries_once(monkeypatch):
    responses = iter(
        [
            {"content": "未按格式输出", "usage": {}},
            {
                "content": (
                    "- **市场热度**：讨论呈现**高热度**。\n"
                    "- **用户关注**：重点关注**安全性**。\n"
                    "- **趋势判断**：需求保持**稳定**。"
                ),
                "usage": {},
            },
        ]
    )
    calls = []
    monkeypatch.setattr(
        market_brief_service,
        "call_llm",
        lambda messages, **kwargs: calls.append(messages) or next(responses),
    )

    summary = market_brief_service._generate_summary(
        [{"role": "user", "content": "context"}],
        set(),
    )

    assert len(calls) == 2
    assert summary.count("\n") == 2
    assert "**安全性**" in summary
