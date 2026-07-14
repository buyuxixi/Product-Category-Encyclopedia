from __future__ import annotations

import json

from sqlalchemy import func, select

from app.api import router
from app.models import HotLink, TrendSignal
from app.services import listing_suggestion_service
from app.services.listing_suggestion_service import (
    generate_listing_suggestion_preview,
)


def _add_demo_data(db):
    category = db.scalar(
        select(listing_suggestion_service.Category).where(
            listing_suggestion_service.Category.code == "SEAT_CUSHION"
        )
    )
    assert category is not None
    product = HotLink(
        category_id=category.id,
        section_key="market",
        link_type="product",
        platform="amazon",
        title="Ergonomic Memory Foam Seat Cushion for Office Chair",
        url="https://example.com/amazon",
        description="ASIN: DEMO | Price: $39.99 | Ratings: 4.3",
        hotness_score=95,
    )
    xhs = HotLink(
        category_id=category.id,
        section_key="market",
        link_type="social_post",
        platform="xiaohongshu",
        title="坐垫久坐实测",
        url="https://example.com/xhs",
        description="用户关注久坐闷热和尾骨压力",
        hotness_score=90,
    )
    reddit = HotLink(
        category_id=category.id,
        section_key="market",
        link_type="discussion",
        platform="reddit",
        title="Office chair cushion discussion",
        url="https://example.com/reddit",
        description="Users discuss firmness and fit on different chairs",
        hotness_score=80,
    )
    db.add_all([product, xhs, reddit])
    db.flush()
    db.add(
        TrendSignal(
            category_id=category.id,
            section_key="market",
            signal_type="user_pain_point",
            platform="xiaohongshu",
            keyword="久坐闷热",
            title="久坐后容易闷热",
            summary=f"用户反馈透气性重要。原文链接: {xhs.url}",
            metric_value=100,
        )
    )
    db.commit()
    return product, xhs, reddit


def _valid_response(xhs_id: int, reddit_id: int) -> dict[str, object]:
    return {
        "keyword_directions": [
            {
                "keyword": "透气久坐",
                "reason": "匹配用户对闷热问题的关注",
                "evidence_ids": [xhs_id],
            }
        ],
        "selling_points": [
            {
                "headline": "兼顾支撑与适配",
                "reason": "不同椅型用户关注软硬度和尺寸适配",
                "evidence_ids": [reddit_id],
            }
        ],
        "improvement_points": [
            {
                "pain_point": "久坐闷热",
                "suggestion": "补充透气结构的可验证说明",
                "evidence_ids": [xhs_id],
            }
        ],
        "limitations": ["未使用该产品的 Amazon 差评，结论属于跨平台品类推断"],
    }


def test_listing_suggestion_preview_route_is_registered():
    assert any(
        route.path == "/api/v1/hot-links/{link_id}/listing-suggestion-preview"
        and "POST" in route.methods
        for route in router.routes
    )


def test_generate_listing_preview_uses_external_sources_without_writes(
    db,
    monkeypatch,
):
    product, xhs, reddit = _add_demo_data(db)
    before_counts = (
        db.scalar(select(func.count()).select_from(HotLink)),
        db.scalar(select(func.count()).select_from(TrendSignal)),
    )

    def fake_call(messages, **kwargs):
        context = json.loads(messages[1]["content"].split("\n\n", 1)[1])
        assert context["target_product"]["id"] == product.id
        assert {item["platform"] for item in context["source_candidates"]} == {
            "xiaohongshu",
            "reddit",
        }
        return {
            "content": json.dumps(
                _valid_response(xhs.id, reddit.id),
                ensure_ascii=False,
            )
        }

    monkeypatch.setattr(listing_suggestion_service, "call_llm", fake_call)
    result = generate_listing_suggestion_preview(db, product=product)

    assert result["basis"] == "cross_platform_category_insights"
    assert result["improvement_points"][0]["pain_point"] == "久坐闷热"
    assert {item["url"] for item in result["evidence"]} == {
        xhs.url,
        reddit.url,
    }
    assert (
        db.scalar(select(func.count()).select_from(HotLink)),
        db.scalar(select(func.count()).select_from(TrendSignal)),
    ) == before_counts
