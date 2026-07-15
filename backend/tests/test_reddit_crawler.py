from __future__ import annotations

from types import SimpleNamespace

from crawler import crawl_reddit, crawl_reddit_single


def test_rss_empty_body_preserves_429_status(monkeypatch) -> None:
    monkeypatch.setattr(crawl_reddit, "MAX_RETRIES", 0)
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout="\n429"),
    )

    assert crawl_reddit._try_rss_search("Health", "pill box") == []


def test_single_category_reuses_shared_oauth_aware_crawler(monkeypatch) -> None:
    expected = {"hot_links": [{"title": "test"}], "trend_signals": []}
    captured: dict[str, object] = {}

    def fake_crawl(category_code: str, sources: list[dict]) -> dict:
        captured["category_code"] = category_code
        captured["sources"] = sources
        return expected

    monkeypatch.setattr(crawl_reddit_single, "crawl_reddit", fake_crawl)

    assert crawl_reddit_single.crawl_single_category("PILL_ORGANIZER") == expected
    assert captured["category_code"] == "PILL_ORGANIZER"
    assert captured["sources"] == crawl_reddit.REDDIT_SOURCES["PILL_ORGANIZER"]


def test_shared_crawler_prefers_oauth_before_rss(monkeypatch) -> None:
    monkeypatch.setattr(crawl_reddit, "REDDIT_CLIENT_ID", "client-id")
    monkeypatch.setattr(crawl_reddit, "REDDIT_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(crawl_reddit.time, "sleep", lambda *_: None)
    monkeypatch.setattr(
        crawl_reddit,
        "_try_oauth_api",
        lambda sub, keyword: [
            {
                "title": "Best pill organizer?",
                "permalink": "https://www.reddit.com/r/Health/comments/example",
                "num_comments": 3,
                "ups": 4,
                "score": 4,
                "desc": "Looking for a daily pill organizer.",
                "days_ago": 2,
            }
        ],
    )
    monkeypatch.setattr(
        crawl_reddit,
        "_try_rss_search",
        lambda *args: (_ for _ in ()).throw(AssertionError("RSS should not run")),
    )

    result = crawl_reddit.crawl_reddit(
        "PILL_ORGANIZER",
        [{"subreddit": "Health", "keyword": "pill organizer"}],
    )

    assert len(result["hot_links"]) == 1
    assert len(result["trend_signals"]) == 1
