from sqlalchemy import select

from app.api import (
    create_hot_link,
    create_trend_signal,
    list_hot_links,
    list_trend_signals,
    search,
)
from app.models import Category
from app.schemas import HotLinkCreate, TrendSignalCreate
from app.security import Actor


def test_chinese_labels_round_trip_through_create_and_list_apis(db):
    category = db.scalar(select(Category).order_by(Category.id))
    assert category is not None
    actor = Actor(id=1, name="测试", role="admin", provider="local")

    create_hot_link(
        HotLinkCreate(
            category_code=category.code,
            section_key="market",
            link_type="video",
            platform="youtube",
            title="English title",
            title_zh="中文标题",
            url="https://example.com/video",
            description="English description",
            description_zh="中文描述",
        ),
        db,
        actor,
    )
    create_trend_signal(
        TrendSignalCreate(
            category_code=category.code,
            section_key="market",
            signal_type="user_pain_point",
            platform="youtube",
            title="English signal",
            title_zh="中文信号",
            summary="English summary",
            summary_zh="中文摘要",
        ),
        db,
        actor,
    )

    hot_links = list_hot_links(
        category.code,
        db,
        actor,
        section_key=None,
        platform=None,
        only_hot=False,
        days=30,
    )
    trend_signals = list_trend_signals(
        category.code,
        db,
        actor,
        section_key=None,
        platform=None,
        days=30,
    )

    assert hot_links["items"][0]["title_zh"] == "中文标题"
    assert hot_links["items"][0]["description_zh"] == "中文描述"
    assert trend_signals["items"][0]["title_zh"] == "中文信号"
    assert trend_signals["items"][0]["summary_zh"] == "中文摘要"

    hot_link_search = search("中文标题", db, actor, limit=30)
    trend_search = search("中文摘要", db, actor, limit=30)
    assert any(item["title"] == "🔗 中文标题" for item in hot_link_search["items"])
    assert any(item["title"] == "📊 中文信号" for item in trend_search["items"])
