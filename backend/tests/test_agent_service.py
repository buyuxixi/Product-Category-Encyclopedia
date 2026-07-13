from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.models import AgentScan, ProductDiscovery
from app.schemas import AgentScanRequest
from app.services import agent_service


def test_agent_scan_scope_requires_matching_input():
    with pytest.raises(ValidationError):
        AgentScanRequest(scan_type="category")
    with pytest.raises(ValidationError):
        AgentScanRequest(scan_type="topic", topic=" ")
    with pytest.raises(ValidationError):
        AgentScanRequest(scan_type="full", category_code="HEAT_THERAPY")


def test_parse_discoveries_accepts_code_fence_and_trailing_comma():
    content = """```json
    {"summary": "ok", "market_overview": {}, "discoveries": [], "recommendations": [],}
    ```"""

    assert agent_service.parse_discoveries(content)["summary"] == "ok"


def test_invalid_llm_json_is_retried_once(monkeypatch):
    valid = json.dumps(
        {"summary": "recovered", "market_overview": {}, "discoveries": [], "recommendations": []}
    )
    responses = iter(
        [
            {"content": "{not valid json", "usage": {}},
            {"content": valid, "usage": {"total_tokens": 2}},
        ]
    )
    calls = []

    def fake_call(messages, **kwargs):
        calls.append((messages, kwargs))
        return next(responses)

    monkeypatch.setattr(agent_service, "call_llm", fake_call)

    report, result = agent_service._call_and_parse_report(
        [{"role": "user", "content": "test"}]
    )

    assert report["summary"] == "recovered"
    assert result["usage"]["total_tokens"] == 2
    assert len(calls) == 2
    assert "合法 JSON" in calls[1][0][-1]["content"]


def test_failed_agent_scan_rolls_back_partial_discoveries(db, monkeypatch):
    data = {
        "categories": [{"code": "HEAT_THERAPY", "children": []}],
        "amazon_products": [],
        "youtube_videos": [],
        "reddit_posts": [],
        "trend_signals": [],
    }
    monkeypatch.setattr(agent_service, "collect_data", lambda *args, **kwargs: data)
    monkeypatch.setattr(
        agent_service,
        "call_llm",
        lambda *args, **kwargs: {
            "content": json.dumps(
                {
                    "summary": "invalid test response",
                    "discoveries": [
                        {
                            "product_name": "invalid score",
                            "opportunity_type": "hot_product",
                            "opportunity_score": 101,
                        }
                    ],
                }
            ),
            "usage": {},
        },
    )

    with pytest.raises(agent_service.AgentError):
        agent_service.run_scan(db, actor="tester")

    scan = db.scalar(select(AgentScan).order_by(AgentScan.id.desc()))
    assert scan is not None
    assert scan.status == "failed"
    assert scan.stats == {
        "products_analyzed": 0,
        "videos_analyzed": 0,
        "posts_analyzed": 0,
        "trends_analyzed": 0,
    }
    assert db.scalar(select(func.count()).select_from(ProductDiscovery)) == 0


def test_missing_source_links_are_recovered_from_real_source_data():
    data = {
        "amazon_products": [
            {
                "title": "Wireless TENS Unit Two Portable Muscle Stimulators",
                "description": "$64.68 — BSR #4",
                "url": "https://www.amazon.com/dp/B0FLX9HY17",
                "category_code": "TENS_THERAPY",
            }
        ]
    }
    discoveries = [
        {
            "product_name": "Wireless TENS Unit (Bluetooth-enabled)",
            "keywords": ["wireless tens", "bluetooth tens unit"],
            "category_code": "TENS_THERAPY",
            "source_links": [],
        }
    ]

    repaired = agent_service._validate_and_fix_links(discoveries, data)

    assert repaired[0]["source_links"] == [
        {
            "title": "Wireless TENS Unit Two Portable Muscle Stimulators",
            "url": "https://www.amazon.com/dp/B0FLX9HY17",
            "platform": "amazon",
        }
    ]


def test_topic_search_expands_common_chinese_terms():
    terms = agent_service._topic_search_terms("无线tens")

    assert {"wireless", "cordless", "bluetooth", "tens"}.issubset(terms)
