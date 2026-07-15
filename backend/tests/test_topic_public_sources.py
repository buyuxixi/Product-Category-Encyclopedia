"""话题公开源与趋势模式链接校验。"""

from __future__ import annotations

from app.services.agent_service import _validate_and_fix_links
from app.services.topic_public_sources import topic_search_queries


def test_topic_search_queries_sports_bottle():
    queries = topic_search_queries("运动水杯")
    joined = " ".join(queries).lower()
    assert "运动水杯" in queries
    assert "sports water bottle" in joined or "water bottle" in joined


def test_trends_mode_strips_unrelated_amazon_links():
    discoveries = [
        {
            "product_name": "Insulated Sports Bottle Trend",
            "keywords": ["water bottle"],
            "source_links": [
                {
                    "title": "Pill Organizer",
                    "url": "https://www.amazon.com/dp/B0B3HXDBJM",
                    "platform": "amazon",
                },
                {
                    "title": "Real news",
                    "url": "https://www.example.com/water-bottle-trend",
                    "platform": "news",
                },
            ],
        }
    ]
    data = {
        "insight_mode": "trends_discussion",
        "amazon_products": [
            {"title": "Pill", "url": "https://www.amazon.com/dp/B0B3HXDBJM"},
        ],
        "topic_links": [
            {"title": "Real news", "url": "https://www.example.com/water-bottle-trend", "platform": "news"},
        ],
        "live_news": [
            {"title": "Real news", "url": "https://www.example.com/water-bottle-trend"},
        ],
    }
    out = _validate_and_fix_links(discoveries, data)
    urls = [x["url"] for x in out[0]["source_links"]]
    assert "https://www.example.com/water-bottle-trend" in urls
    assert "https://www.amazon.com/dp/B0B3HXDBJM" not in urls


def test_trends_mode_fills_search_links_when_empty():
    discoveries = [
        {
            "product_name": "Muji & Xiaomi 运动水杯系列",
            "keywords": ["muji 运动水杯", "xiaomi 运动水杯"],
            "source_links": [],
        }
    ]
    data = {
        "insight_mode": "trends_discussion",
        "topic_links": [],
        "live_news": [],
    }
    out = _validate_and_fix_links(discoveries, data)
    links = out[0]["source_links"]
    assert links
    assert any("google.com/search" in (x["url"] or "") for x in links)
    assert any("bing.com/news" in (x["url"] or "") for x in links)
    assert all("/dp/" not in (x["url"] or "") for x in links)
