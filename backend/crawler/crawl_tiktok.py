#!/usr/bin/env python3
"""TikTok 爬取器 — 通过 Playwright 浏览器自动化搜索 TikTok 视频。

TikTok 的搜索数据无法通过简单 HTTP 请求获取（需要 JS 渲染）。
使用 Playwright headless 浏览器加载搜索页面，等待 JS 执行后提取视频数据。

提取: 视频描述、播放量、点赞数、作者、视频链接
写入: HotLink(link_type="video", platform="tiktok")

Requirements:
    pip install playwright
    python -m playwright install chromium

Usage:
    python crawl_tiktok.py           # 爬取全品类
    python crawl_tiktok.py --json    # 输出 JSON
"""
from __future__ import annotations

import json
import re
import sys
import time
from urllib.parse import quote_plus

# 品类 → TikTok 搜索关键词（用更口语化的词，TikTok 用户偏年轻）
TIKTOK_KEYWORDS: dict[str, list[str]] = {
    "TENS_THERAPY": ["TENS unit", "TENS machine pain relief"],
    "HEAT_THERAPY": ["heating pad", "heat therapy hack"],
    "SHOULDER_NECK_HEAT_THERAPY": ["neck heating pad", "shoulder pain relief"],
    "FAR_INFRARED": ["infrared sauna blanket", "far infrared"],
    "NIGHT_LIGHT": ["night light aesthetic", "motion sensor night light"],
    "PILL_ORGANIZER": ["pill organizer", "medicine organizer"],
    "PILL_SPLITTER": ["pill splitter", "pill cutter"],
    "SEAT_CUSHION": ["seat cushion", "ergonomic cushion"],
}


def search_tiktok(keyword: str, max_results: int = 5) -> list[dict]:
    """使用 Playwright 搜索 TikTok，提取视频数据。"""
    from playwright.sync_api import sync_playwright

    videos: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = context.new_page()

        url = f"https://www.tiktok.com/search?q={quote_plus(keyword)}"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            # Wait for video cards to load
            page.wait_for_selector("div[data-e2e='search_video-item']", timeout=10000)
            time.sleep(2)  # Extra time for data to populate
        except Exception as e:
            print(f"  [WARN] TikTok page load '{keyword}' failed: {e}", file=sys.stderr)
            browser.close()
            return []

        # Extract video data from page
        items = page.query_selector_all("div[data-e2e='search_video-item']")
        for item in items[:max_results]:
            try:
                # Get video link
                link_el = item.query_selector("a[href*='/video/']")
                video_url = link_el.get_attribute("href") if link_el else ""

                # Get author
                author_el = item.query_selector("a[href*='/@']")
                author = ""
                if author_el:
                    author = author_el.get_attribute("href", "").split("/@")[1].split("/")[0] if "/@" in (author_el.get_attribute("href") or "") else ""

                # Get description/title
                title_el = item.query_selector("div[data-e2e='search-card-desc-1'], div[data-e2e='search-card-desc']")
                title = title_el.inner_text() if title_el else ""

                # Get play count
                plays_el = item.query_selector("span[data-e2e='video-views']")
                plays_text = plays_el.inner_text() if plays_el else "0"
                plays = parse_count(plays_text)

                # Get like count
                likes_el = item.query_selector("span[data-e2e='like-count']")
                likes_text = likes_el.inner_text() if likes_el else "0"
                likes = parse_count(likes_text)

                if video_url and title:
                    videos.append({
                        "title": title[:500],
                        "url": video_url.split("?")[0],  # Clean URL
                        "views": plays,
                        "likes": likes,
                        "author": author,
                        "description": f"@{author} | 👀 {plays_text} ❤️ {likes_text}",
                    })
            except Exception:
                continue

        browser.close()

    return videos


def parse_count(text: str) -> int:
    """Parse TikTok count text like '1.2M', '15.3K', '350' into int."""
    text = text.strip().upper()
    try:
        if "M" in text:
            return int(float(text.replace("M", "")) * 1_000_000)
        elif "K" in text:
            return int(float(text.replace("K", "")) * 1_000)
        else:
            return int(re.sub(r"[^0-9]", "", text) or 0)
    except Exception:
        return 0


def crawl_tiktok(category_code: str, keywords: list[str]) -> dict:
    """爬取 TikTok 搜索结果。"""
    hot_links: list[dict] = []
    trend_signals: list[dict] = []

    for keyword in keywords:
        videos = search_tiktok(keyword, max_results=5)
        time.sleep(1)

        for v in videos:
            views = v["views"]
            likes = v["likes"]
            # 热度评分：播放量 + 点赞数
            # 100K 播放 = 10分, 1M = 20分, 5M+ = 30分
            hotness = min(views / 100000 * 10, 30)
            # 10K 点赞 = 10分, 100K = 20分
            hotness += min(likes / 10000 * 10, 20)
            is_hot = hotness >= 15

            hot_links.append({
                "category_code": category_code,
                "section_key": "market",
                "link_type": "video",
                "platform": "tiktok",
                "title": v["title"],
                "url": v["url"],
                "description": v["description"][:500],
                "hotness_score": round(hotness, 2),
                "is_hot": is_hot,
            })

        total_views = sum(v["views"] for v in videos)
        trend_signals.append({
            "category_code": category_code,
            "section_key": "market",
            "signal_type": "social_mention",
            "platform": "tiktok",
            "keyword": keyword,
            "title": f"TikTok: {keyword}",
            "metric_value": float(total_views),
            "metric_unit": "views",
            "trend_direction": "up" if total_views > 500000 else "stable",
            "summary": f"TikTok 搜索 '{keyword}': {len(videos)} 个热门视频, 总播放 {total_views:,}",
        })

    return {"hot_links": hot_links, "trend_signals": trend_signals}


def crawl_all() -> dict:
    """Crawl all categories, return merged result."""
    all_hot_links: list[dict] = []
    all_trend_signals: list[dict] = []
    for cat, kws in TIKTOK_KEYWORDS.items():
        result = crawl_tiktok(cat, kws)
        all_hot_links.extend(result["hot_links"])
        all_trend_signals.extend(result["trend_signals"])
        hot_count = sum(1 for l in result["hot_links"] if l["is_hot"])
        print(f"  {cat}: {len(result['hot_links'])} hot_links ({hot_count} hot), {len(result['trend_signals'])} trend_signals")
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
