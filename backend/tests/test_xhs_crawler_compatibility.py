from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import func, select

from app.api import (
    clear_trend_signals,
    create_hot_links_batch,
    create_trend_signals_batch,
)
from app.models import Category, HotLink, TrendSignal
from app.schemas import (
    HotLinkBatch,
    HotLinkCreate,
    TrendSignalBatch,
    TrendSignalCreate,
)
from app.security import Actor
from crawler import push_to_encyclopedia
from scripts.import_cleaned_xhs import (
    CategorySource,
    build_crawl_result,
    engagement_score,
    hotness_from_metrics,
    parse_metrics_from_description,
)


FIXTURES = Path(__file__).parent / "fixtures" / "xhs"


def actor() -> Actor:
    return Actor(id=1, name="测试", role="admin", provider="local")


def test_xhs_hotness_normalized_0_100():
    # 中等帖：赞1200/评30/藏80 → 12+1+3=16，非 is_hot
    score, is_hot = hotness_from_metrics(1200, 30, 80)
    assert score == 16.0
    assert is_hot is False

    # 截图坐垫爆帖：封顶 40+30+20=90
    score, is_hot = hotness_from_metrics(25777, 209, 14411)
    assert score == 90.0
    assert is_hot is True
    # 原始 engagement 仍可用于选帖，不等于入库热度
    assert engagement_score(25777, 209, 14411) == 40606

    parsed = parse_metrics_from_description(
        "[郑原里美] | ❤ 25777 | 💬 209 | ⭐ 14411 | 搜索词: 坐垫推荐"
    )
    assert parsed == (25777, 209, 14411)
    assert parse_metrics_from_description("无指标描述") is None


def test_build_crawl_result_supports_api_and_grouped_comments():
    sources = [
        CategorySource(
            "TENS_THERAPY",
            "notes.json",
            "api_comments.json",
            "api",
            re.compile(r"TENS", re.I),
            comment_include=re.compile(r"档|麻", re.I),
        ),
        CategorySource(
            "NIGHT_LIGHT",
            "notes.json",
            "grouped_comments.json",
            "grouped",
            re.compile(r"起夜|感应灯", re.I),
            comment_include=re.compile(r"好用|感应", re.I),
        ),
    ]

    result = build_crawl_result(
        FIXTURES,
        note_limit=1,
        comment_limit=1,
        sources=sources,
    )

    assert len(result["hot_links"]) == 2
    assert len(result["trend_signals"]) == 2
    assert {item["category_code"] for item in result["hot_links"]} == {
        "TENS_THERAPY",
        "NIGHT_LIGHT",
    }
    assert all(item["platform"] == "xiaohongshu" for item in result["hot_links"])
    assert all(item["link_type"] == "social_post" for item in result["hot_links"])
    by_code = {item["category_code"]: item for item in result["hot_links"]}
    # TENS: min(12,40)+min(1,30)+min(3,20)=16
    assert by_code["TENS_THERAPY"]["hotness_score"] == 16.0
    assert by_code["TENS_THERAPY"]["is_hot"] is False
    # night light: min(0.9,40)+min(0.5,30)+min(1.2,20)=2.6
    assert by_code["NIGHT_LIGHT"]["hotness_score"] == 2.6
    assert by_code["NIGHT_LIGHT"]["is_hot"] is False
    assert {item["title"] for item in result["trend_signals"]} == {
        "档位太强会麻，建议从低档开始",
        "晚上起夜很好用，感应也很灵敏",
    }


def test_xhs_batches_update_existing_rows(db):
    category = db.scalar(select(Category).where(Category.code == "TENS_THERAPY"))
    assert category is not None
    hot_link = HotLinkCreate(
        category_code=category.code,
        section_key="market",
        link_type="social_post",
        platform="xiaohongshu",
        title="初始标题",
        title_zh="初始标题",
        url="https://www.xiaohongshu.com/explore/upsert1",
        description="初始描述",
        description_zh="初始描述",
        hotness_score=10,
    )
    signal = TrendSignalCreate(
        category_code=category.code,
        section_key="market",
        signal_type="user_pain_point",
        platform="xiaohongshu",
        keyword="初始词",
        title="同一条评论",
        title_zh="同一条评论",
        metric_value=1,
        metric_unit="likes",
        trend_direction="stable",
        summary="初始摘要",
        summary_zh="初始摘要",
    )

    first_links = create_hot_links_batch(
        HotLinkBatch(items=[hot_link]), db, actor()
    )
    first_signals = create_trend_signals_batch(
        TrendSignalBatch(items=[signal]), db, actor()
    )
    hot_link.description = "更新描述"
    hot_link.hotness_score = 99
    signal.summary = "更新摘要"
    signal.metric_value = 20
    second_links = create_hot_links_batch(
        HotLinkBatch(items=[hot_link]), db, actor()
    )
    second_signals = create_trend_signals_batch(
        TrendSignalBatch(items=[signal]), db, actor()
    )

    assert first_links["inserted_count"] == 1
    assert first_signals["inserted_count"] == 1
    assert second_links["updated_count"] == 1
    assert second_signals["updated_count"] == 1
    assert db.scalar(select(func.count(HotLink.id))) == 1
    assert db.scalar(select(func.count(TrendSignal.id))) == 1
    assert db.scalar(select(HotLink.description)) == "更新描述"
    assert db.scalar(select(TrendSignal.summary)) == "更新摘要"


def test_platform_scoped_clear_preserves_xhs_signals(db):
    category = db.scalar(select(Category).where(Category.code == "TENS_THERAPY"))
    assert category is not None
    db.add_all(
        [
            TrendSignal(
                category_id=category.id,
                section_key="market",
                signal_type="social_mention",
                platform="youtube",
                title="YouTube signal",
            ),
            TrendSignal(
                category_id=category.id,
                section_key="market",
                signal_type="user_pain_point",
                platform="xiaohongshu",
                title="XHS signal",
            ),
        ]
    )
    db.commit()

    result = clear_trend_signals(
        category.code,
        db,
        actor(),
        platform="youtube",
    )

    assert result["deleted"] == 1
    assert db.scalars(select(TrendSignal.platform)).all() == ["xiaohongshu"]


def test_full_push_clears_only_platforms_in_result(monkeypatch):
    cleared_links: list[tuple[str, str | None]] = []
    cleared_signals: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        push_to_encyclopedia,
        "clear_category_hot_links",
        lambda cookies, category, platform=None: (
            cleared_links.append((category, platform)) or 0
        ),
    )
    monkeypatch.setattr(
        push_to_encyclopedia,
        "clear_category_trend_signals",
        lambda cookies, category, platform=None: (
            cleared_signals.append((category, platform)) or 0
        ),
    )
    push_result = {"inserted": 1, "updated": 0, "skipped": []}
    monkeypatch.setattr(
        push_to_encyclopedia, "push_hot_links", lambda items, cookies=None: push_result
    )
    monkeypatch.setattr(
        push_to_encyclopedia,
        "push_trend_signals",
        lambda items, cookies=None: push_result,
    )
    monkeypatch.setattr(
        push_to_encyclopedia, "send_feishu_notification", lambda *args: None
    )
    monkeypatch.setattr(
        push_to_encyclopedia, "update_market_sections", lambda *args: None
    )
    crawl_result = {
        "hot_links": [
            {
                "category_code": "TENS_THERAPY",
                "platform": "youtube",
                "hotness_score": 10,
            }
        ],
        "trend_signals": [
            {
                "category_code": "TENS_THERAPY",
                "platform": "youtube",
                "signal_type": "social_mention",
            }
        ],
    }

    push_to_encyclopedia.push_all(crawl_result, cookies={})

    assert cleared_links == [("TENS_THERAPY", "youtube")]
    assert cleared_signals == [("TENS_THERAPY", "youtube")]
    assert ("TENS_THERAPY", "xiaohongshu") not in cleared_links


def test_incremental_push_never_clears(monkeypatch):
    push_result = {"inserted": 0, "updated": 1, "skipped": []}
    monkeypatch.setattr(
        push_to_encyclopedia, "push_hot_links", lambda items, cookies=None: push_result
    )
    monkeypatch.setattr(
        push_to_encyclopedia,
        "push_trend_signals",
        lambda items, cookies=None: push_result,
    )
    monkeypatch.setattr(
        push_to_encyclopedia, "update_market_sections", lambda *args: None
    )
    monkeypatch.setattr(
        push_to_encyclopedia,
        "clear_category_hot_links",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not clear")),
    )

    summary = push_to_encyclopedia.push_incremental(
        {"hot_links": [{}], "trend_signals": [{}]},
        cookies={},
    )

    assert summary["hot_links_updated"] == 1
    assert summary["trend_signals_updated"] == 1
