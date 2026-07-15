"""话题扫描的轻量公开源采集（Bing News RSS + Google Suggest）。

不依赖 Amazon 实时爬取，降低封 IP 风险；失败时静默降级为空结果。
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import feedparser
import httpx

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
}

BING_NEWS_RSS = "https://www.bing.com/news/search?q={query}&format=rss"
GOOGLE_SUGGEST = "https://suggestqueries.google.com/complete/search?client=firefox&q={query}"
FRESHNESS_DAYS = 45

# 中文话题 → 英文检索词（公开源多为英文）
_TOPIC_EN_QUERIES: dict[str, tuple[str, ...]] = {
    "运动水杯": ("sports water bottle", "gym water bottle", "insulated water bottle"),
    "水杯": ("water bottle", "sports bottle", "tumbler"),
    "保温杯": ("insulated tumbler", "thermos bottle"),
    "坐垫": ("seat cushion", "office cushion"),
    "夜灯": ("night light", "motion sensor night light"),
    "药盒": ("pill organizer", "pill box"),
    "热敷": ("heating pad", "heat therapy"),
    "风扇": ("portable fan", "neck fan"),
}


def topic_search_queries(topic: str) -> list[str]:
    """生成公开源检索词：原词 + 英文别名 + 简单分词。"""
    raw = (topic or "").strip()
    if not raw:
        return []
    queries: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        q = q.strip()
        if not q:
            return
        key = q.lower()
        if key in seen:
            return
        seen.add(key)
        queries.append(q)

    add(raw)
    lower = raw.lower()
    for zh, en_list in _TOPIC_EN_QUERIES.items():
        if zh in raw:
            for en in en_list:
                add(en)
    # 已有英文则保留；纯中文时至少尝试 pinyin-less English from aliases only
    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9\- ]{1,40}", raw):
        add(token)
    if lower not in seen and re.search(r"[a-zA-Z]", raw):
        add(lower)
    return queries[:5]


def _extract_real_url(bing_url: str) -> str:
    try:
        params = parse_qs(urlparse(bing_url).query)
        real = params.get("url", [""])[0]
        if real:
            return unquote(real)
    except Exception:
        pass
    return bing_url


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _fetch_bing_news(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    url = BING_NEWS_RSS.format(query=quote_plus(query))
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Bing News 失败 query=%s: %s", query, exc)
        return []

    feed = feedparser.parse(resp.text)
    now = datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []
    for entry in feed.entries[:15]:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            continue
        published = None
        for field in ("published_parsed", "updated_parsed"):
            parsed = entry.get(field)
            if parsed:
                try:
                    published = datetime(*parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    published = None
                break
        if published and (now - published).days > FRESHNESS_DAYS:
            continue
        real_url = _extract_real_url(link)
        desc = _strip_html(entry.get("summary") or entry.get("description") or "")[:300]
        items.append({
            "title": title[:500],
            "url": real_url[:2000],
            "platform": "news",
            "description": desc,
            "source_query": query,
        })
        if len(items) >= limit:
            break
    return items


def _fetch_google_suggestions(query: str) -> list[str]:
    url = GOOGLE_SUGGEST.format(query=quote_plus(query))
    try:
        resp = httpx.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        suggestions = data[1] if isinstance(data, list) and len(data) > 1 else []
        # 优先保留含拉丁字符的建议（跨境电商语境）
        en = [s for s in suggestions if isinstance(s, str) and any(ord(c) < 128 and c.isalpha() for c in s)]
        return (en or [s for s in suggestions if isinstance(s, str)])[:8]
    except Exception as exc:
        logger.warning("Google Suggest 失败 query=%s: %s", query, exc)
        return []


def fetch_topic_public_sources(topic: str) -> dict[str, Any]:
    """拉取话题相关新闻与搜索建议。任一源失败不影响另一源。"""
    queries = topic_search_queries(topic)
    news: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    keyword_trends: list[dict[str, Any]] = []

    for q in queries[:3]:
        for item in _fetch_bing_news(q, limit=6):
            url = item.get("url") or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            news.append(item)
        time.sleep(0.3)

        suggestions = _fetch_google_suggestions(q)
        if suggestions:
            keyword_trends.append({
                "keyword": q,
                "platform": "google",
                "trend_direction": "stable",
                "summary": f"相关搜索词: {', '.join(suggestions[:6])}",
                "related_keywords": suggestions[:6],
            })
        time.sleep(0.3)

    return {
        "query_terms": queries,
        "news": news[:20],
        "keyword_trends": keyword_trends,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
