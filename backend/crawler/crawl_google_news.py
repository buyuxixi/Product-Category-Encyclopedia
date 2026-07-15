#!/usr/bin/env python3
"""Bing News RSS 爬取器 — 从 Bing News RSS 提取新闻热点。

Bing News RSS 的优势：
- 返回的文章 URL 是真实出版商链接（不是搜索页面）
- URL 格式: bing.com/news/apiclick.aspx?...&url=https://realsite.com/article
- 可以从 bing 重定向 URL 中提取出真实文章 URL

新鲜度窗口：
- B2B 品类关键词的新闻覆盖频率低，使用 30 天作为默认窗口
- 超过 30 天的文章跳过不推送

Usage:
    python crawl_google_news.py           # 爬取全品类
    python crawl_google_news.py --json    # 输出 JSON
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from urllib.parse import quote_plus, parse_qs, urlparse, unquote

import httpx
import re

# 品类 → 搜索关键词
NEWS_KEYWORDS: dict[str, list[str]] = {
    "HEAT_THERAPY": ["heating pad heat therapy", "heating pad review"],
    "SHOULDER_NECK_HEAT_THERAPY": ["neck heating pad", "shoulder heat wrap"],
    "FAR_INFRARED": ["far infrared heating pad", "far infrared therapy"],
    "TENS_THERAPY": ["TENS unit device", "TENS unit review"],
    "NIGHT_LIGHT": ["night light LED", "motion sensor night light"],
    "PILL_ORGANIZER": ["pill organizer medication", "pill dispenser review"],
    "PILL_SPLITTER": ["pill splitter review", "pill cutter medication"],
    "SEAT_CUSHION": ["seat cushion ergonomic", "tailbone cushion review"],
}

RSS_TEMPLATE = "https://www.bing.com/news/search?q={query}&format=rss"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# 权威出版商域名 — 匹配时获得额外热度加分
PUBLISHER_AUTHORITY = {
    "cnn.com", "nytimes.com", "nbcnews.com", "forbes.com", "wsj.com",
    "bbc.com", "reuters.com", "bloomberg.com", "techcrunch.com", "wired.com",
    "theverge.com", "cnet.com", "engadget.com", "esquire.com", "health.com",
    "goodhousekeeping.com", "webmd.com", "mayoclinic.org", "healthline.com",
    "medicalnewstoday.com", "verywellhealth.com", "npr.org", "usatoday.com",
    "foxnews.com", "aol.com", "msn.com", "yahoo.com", "chicagotribune.com",
    "nydailynews.com", "gearpatrol.com", "consumerreports.org",
    "reviewed.usatoday.com", "popularmechanics.com", "popsci.com",
}

# 新鲜度窗口（天）— 超过此天数的文章跳过
FRESHNESS_WINDOW_DAYS = 30


def _extract_real_url(bing_url: str) -> str:
    """从 Bing News 重定向 URL 中提取真实文章 URL。
    
    Bing News RSS 的链接格式:
    http://www.bing.com/news/apiclick.aspx?...&url=https%3a%2f%2fwww.realsite.com%2farticle...
    
    提取 url= 参数的值即为真实文章 URL。
    """
    try:
        parsed = urlparse(bing_url)
        params = parse_qs(parsed.query)
        real_url = params.get("url", [""])[0]
        if real_url:
            return unquote(real_url)
    except Exception:
        pass
    # 如果提取失败，返回原始 Bing URL（仍然可点击，只是体验差一些）
    return bing_url


def _extract_domain(url: str) -> str:
    """从 URL 中提取域名。"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # 去掉 www. 前缀
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def _strip_html(text: str) -> str:
    """清除 HTML 标签，返回纯文本。"""
    return re.sub(r'<[^>]+>', '', text).strip()


def _news_hotness(entry: dict, real_url: str) -> tuple[float, bool, str]:
    """计算新闻热度分和来源信息。
    
    评分:
    - 新鲜度: 7天内=+20, 30天内=+12, 90天内=+6
    - 来源权威: 权威出版商=+15, 其他=+5
    - 返回 (score, is_hot, publisher_domain)
    """
    published = None
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                published = datetime(*parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass
            break

    now = datetime.now(timezone.utc)
    score = 0.0

    # 新鲜度评分
    if published:
        days_ago = (now - published).days
        if days_ago <= 7:
            score += 20
        elif days_ago <= 30:
            score += 12
        elif days_ago <= 90:
            score += 6
        else:
            # 超过新鲜度窗口，返回 None 信号跳过
            return -1, False, ""

    # 来源权威度评分
    domain = _extract_domain(real_url)
    if domain in PUBLISHER_AUTHORITY:
        score += 15
    else:
        score += 5

    is_hot = score >= 30  # 权威出版商+7天内=35, 权威+30天内=27, 普通+7天内=25

    return round(score, 2), is_hot, domain


def _parse_bing_feed(text: str) -> list[dict]:
    """解析 Bing News RSS feed，提取真实文章 URL。"""
    import feedparser
    feed = feedparser.parse(text)
    items = []
    for entry in feed.entries[:15]:
        title = entry.get("title", "").strip()
        bing_link = entry.get("link", "").strip()
        desc = _strip_html((entry.get("summary", "") or entry.get("description", "")).strip())

        if not title or not bing_link:
            continue

        # 从 Bing 重定向 URL 提取真实文章 URL
        real_url = _extract_real_url(bing_link)

        # 计算热度和来源信息
        score, is_hot, domain = _news_hotness(entry, real_url)
        if score < 0:
            continue  # 超过新鲜度窗口，跳过

        # 从标题中提取出版商名称（Bing News 标题格式: "Article Title - Publisher Name"）
        publisher_name = ""
        if " - " in title:
            parts = title.rsplit(" - ", 1)
            if len(parts) == 2:
                publisher_name = parts[1].strip()

        items.append({
            "title": title[:500],
            "link": real_url,  # 使用真实文章 URL，不是 Bing 重定向
            "description": f"[{publisher_name or domain}] {desc}"[:500] if (publisher_name or domain) else desc[:500],
            "hotness_score": score,
            "is_hot": is_hot,
            "publisher_domain": domain,
            "publisher_name": publisher_name,
        })
    return items


def crawl_google_news(category_code: str, keywords: list[str]) -> dict:
    """爬取 Bing News RSS，返回 hot_links 和 trend_signals。"""
    hot_links: list[dict] = []
    trend_signals: list[dict] = []

    for keyword in keywords:
        url = RSS_TEMPLATE.format(query=quote_plus(keyword))
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
            resp.raise_for_status()
            entries = _parse_bing_feed(resp.text)
        except Exception as e:
            print(f"  [WARN] Bing News '{keyword}' failed: {e}", file=sys.stderr)
            entries = []

        for idx, entry in enumerate(entries):
            hotness = entry.get("hotness_score")
            is_hot = entry.get("is_hot", False)
            # 跨章节分布: 第1条→trends, 第2条→needs, 其余→market
            section_map = ["trends", "needs", "market", "market", "market"]
            section = section_map[idx] if idx < len(section_map) else "market"
            hot_links.append({
                "category_code": category_code,
                "section_key": section,
                "link_type": "news",
                "platform": "news",
                "title": entry["title"],
                "url": entry["link"],
                "description": entry["description"],
                "hotness_score": hotness,
                "is_hot": is_hot,
            })

        trend_signals.append({
            "category_code": category_code,
            "section_key": "market",
            "signal_type": "news_volume",
            "platform": "news",
            "keyword": keyword,
            "title": f"Bing News: {keyword}",
            "metric_value": float(len(entries)),
            "metric_unit": "articles",
            "trend_direction": "new" if len(entries) > 5 else "stable",
            "summary": f"找到 {len(entries)} 条相关新闻（{FRESHNESS_WINDOW_DAYS}天内）",
        })

    return {"hot_links": hot_links, "trend_signals": trend_signals}


def crawl_all() -> dict:
    """Crawl all categories, return merged result."""
    all_hot_links: list[dict] = []
    all_trend_signals: list[dict] = []
    for cat, kws in NEWS_KEYWORDS.items():
        result = crawl_google_news(cat, kws)
        all_hot_links.extend(result["hot_links"])
        all_trend_signals.extend(result["trend_signals"])
        print(f"  {cat}: {len(result['hot_links'])} hot_links, {len(result['trend_signals'])} trend_signals")
    return {"hot_links": all_hot_links, "trend_signals": all_trend_signals}


if __name__ == "__main__":
    from _guard import require_crawler_enabled

    require_crawler_enabled()
    result = crawl_all()
    total_hl = len(result["hot_links"])
    total_ts = len(result["trend_signals"])
    print(f"\nTotal: {total_hl} hot_links, {total_ts} trend_signals")
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2, ensure_ascii=False))
