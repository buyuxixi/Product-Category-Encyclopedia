from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from app.api import _section_payload, router
from app.models import Category, EncyclopediaSection, EvidenceLink, HotLink, TrendSignal
from app.services import audience_insight_service
from app.services.content_service import ContentError


def _category(db):
    category = db.scalar(select(Category).where(Category.code == "TENS_THERAPY"))
    assert category is not None
    return category


def _add_sources_and_signals(db, category):
    xhs = HotLink(
        category_id=category.id,
        section_key="market",
        link_type="social_post",
        platform="xiaohongshu",
        title="新手误开高档位",
        url="https://example.com/xhs",
        description="用户讨论档位选择",
        hotness_score=90,
    )
    youtube = HotLink(
        category_id=category.id,
        section_key="market",
        link_type="video",
        platform="youtube",
        title="TENS Unit Review",
        url="https://example.com/youtube",
        description="评论关注使用指导",
        hotness_score=80,
    )
    db.add_all([xhs, youtube])
    db.flush()
    db.add_all(
        [
            TrendSignal(
                category_id=category.id,
                section_key="market",
                signal_type="user_pain_point",
                platform="xiaohongshu",
                keyword="档位",
                title="一上来就开15档",
                summary=f"新手误用高档位。原文链接: {xhs.url}",
                metric_value=100,
            ),
            TrendSignal(
                category_id=category.id,
                section_key="market",
                signal_type="user_pain_point",
                platform="youtube",
                keyword="TENS unit review",
                title="YouTube 评论分析: TENS Unit Review",
                summary="用户不清楚贴片位置",
                metric_value=50,
            ),
        ]
    )
    db.commit()
    return xhs, youtube


def _clear_target_sections(db, category):
    sections = db.scalars(
        select(EncyclopediaSection).where(
            EncyclopediaSection.category_id == category.id,
            EncyclopediaSection.section_key.in_(("users", "needs")),
        )
    ).all()
    for section in sections:
        section.content = ""
        section.generation_mode = "empty"
        section.locked_by_human = False
    db.commit()


def test_generate_audience_route_is_registered():
    assert any(
        route.path == "/api/v1/categories/{code}/generate-audience-sections"
        and "POST" in route.methods
        for route in router.routes
    )


def test_generate_audience_insights_saves_sections_and_post_evidence(db, monkeypatch):
    category = _category(db)
    xhs, youtube = _add_sources_and_signals(db, category)
    _clear_target_sections(db, category)

    def fake_call(messages, **kwargs):
        context = json.loads(messages[1]["content"].split("\n\n", 1)[1])
        assert {item["id"] for item in context["source_candidates"]} == {
            xhs.id,
            youtube.id,
        }
        return {
            "content": json.dumps(
                {
                    "personas": [
                        {
                            "name": "TENS 新手",
                            "traits": "缺乏参数知识",
                            "scenarios": "首次居家使用",
                            "needs": "清晰档位指导",
                            "evidence_ids": [xhs.id, youtube.id],
                        }
                    ],
                    "pain_points": [
                        {
                            "name": "高档位误用",
                            "description": "首次使用直接选择过高档位",
                            "scenarios": "居家止痛",
                            "opportunity": "提供渐进档位引导",
                            "evidence_ids": [xhs.id],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            "usage": {},
        }

    monkeypatch.setattr(audience_insight_service, "call_llm", fake_call)
    sections = audience_insight_service.generate_audience_insights(
        db,
        category=category,
        actor="researcher",
    )
    section_by_key = {section.section_key: section for section in sections}

    assert "[新手误开高档位](https://example.com/xhs)" in section_by_key["users"].content
    assert "### 3.1 Top 用户痛点" in section_by_key["needs"].content
    assert "高档位误用" in section_by_key["needs"].content
    needs_evidence = db.scalars(
        select(EvidenceLink).where(EvidenceLink.section_id == section_by_key["needs"].id)
    ).all()
    assert [(item.source_type, item.source_id) for item in needs_evidence] == [
        ("hot_link", xhs.id)
    ]
    payload = _section_payload(section_by_key["needs"], db)
    assert payload["evidence"][0]["source"]["url"] == xhs.url


def test_generate_audience_insights_respects_human_lock(db, monkeypatch):
    category = _category(db)
    _add_sources_and_signals(db, category)
    users = db.scalar(
        select(EncyclopediaSection).where(
            EncyclopediaSection.category_id == category.id,
            EncyclopediaSection.section_key == "users",
        )
    )
    users.content = "人工画像"
    users.locked_by_human = True
    users.generation_mode = "human"
    db.commit()
    monkeypatch.setattr(
        audience_insight_service,
        "call_llm",
        lambda *args, **kwargs: pytest.fail("locked sections must not call LLM"),
    )

    with pytest.raises(ContentError, match="locked"):
        audience_insight_service.generate_audience_insights(
            db,
            category=category,
            actor="researcher",
        )


def test_generate_audience_insights_never_overwrites_existing_content(db, monkeypatch):
    category = _category(db)
    _add_sources_and_signals(db, category)
    users = db.scalar(
        select(EncyclopediaSection).where(
            EncyclopediaSection.category_id == category.id,
            EncyclopediaSection.section_key == "users",
        )
    )
    users.content = "已有用户画像正文"
    users.generation_mode = "generated"
    db.commit()
    monkeypatch.setattr(
        audience_insight_service,
        "call_llm",
        lambda *args, **kwargs: pytest.fail("existing content must not call LLM"),
    )

    with pytest.raises(ContentError, match="cannot be overwritten"):
        audience_insight_service.generate_audience_insights(
            db,
            category=category,
            actor="researcher",
        )


def test_invalid_evidence_ids_trigger_one_retry(monkeypatch):
    responses = iter(
        [
            {
                "content": json.dumps(
                    {
                        "personas": [
                            {
                                "name": "用户",
                                "traits": "特征",
                                "scenarios": "场景",
                                "needs": "需求",
                                "evidence_ids": [999],
                            }
                        ],
                        "pain_points": [],
                    }
                )
            },
            {
                "content": json.dumps(
                    {
                        "personas": [
                            {
                                "name": "用户",
                                "traits": "特征",
                                "scenarios": "场景",
                                "needs": "需求",
                                "evidence_ids": [1],
                            }
                        ],
                        "pain_points": [
                            {
                                "name": "痛点",
                                "description": "描述",
                                "scenarios": "场景",
                                "opportunity": "机会",
                                "evidence_ids": [1],
                            }
                        ],
                    }
                )
            },
        ]
    )
    calls = []
    monkeypatch.setattr(
        audience_insight_service,
        "call_llm",
        lambda messages, **kwargs: calls.append(messages) or next(responses),
    )

    result = audience_insight_service._call_and_parse(
        [{"role": "user", "content": "context"}],
        {1},
    )

    assert len(calls) == 2
    assert result["personas"][0]["evidence_ids"] == [1]
