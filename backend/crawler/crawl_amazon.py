#!/usr/bin/env python3
"""Amazon 搜索页爬取器 — 通过 Playwright 浏览器自动化提取搜索结果。

提取: 商品标题、ASIN、价格、评分数、跳转链接
反爬策略: 随机 User-Agent、页面滚动延迟、请求间隔
写入: HotLink(link_type="product") + TrendSignal(signal_type="social_mention")

Requirements:
    pip install playwright
    python -m playwright install chromium

Usage:
    python crawl_amazon.py
    python crawl_amazon.py --json
"""
from __future__ import annotations

import asyncio
import json
import random
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("[ERROR] playwright not installed. Run: pip install playwright && python -m playwright install chromium", file=sys.stderr)
    sys.exit(1)

# 品类 → Amazon 搜索关键词
AMAZON_KEYWORDS: dict[str, list[str]] = {
    "TENS_THERAPY": ["TENS unit", "TENS unit pads"],
    "HEAT_THERAPY": ["heat wrap neck shoulder", "far infrared heating pad"],
    "NIGHT_LIGHT": ["night light motion sensor", "baby night light"],
    "MEDICATION_MANAGEMENT": ["pill organizer weekly", "pill splitter"],
    "SEAT_CUSHION": ["seat cushion office chair", "tailbone cushion"],
}

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


async def crawl_amazon_search(page, keyword: str) -> list[dict]:
    """爬取单个 Amazon 搜索关键词。"""
    url = f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}"
    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(random.uniform(2, 4))  # 随机延迟

    # 滚动页面加载更多
    await page.evaluate("window.scrollBy(0, 800)")
    await asyncio.sleep(1)

    results: list[dict] = []
    items = await page.query_selector_all('[data-component-type="s-search-result"]')
    for item in items[:10]:  # 每个关键词取前 10 个
        try:
            asin = await item.get_attribute("data-asin") or ""
            if not asin:
                continue

            title_el = await item.query_selector("h2 a span")
            title = await title_el.inner_text() if title_el else ""

            price_whole = await item.query_selector(".a-price-whole")
            price_frac = await item.query_selector(".a-price-fraction")
            price = ""
            if price_whole:
                whole = await price_whole.inner_text()
                frac = await price_frac.inner_text() if price_frac else ""
                price = f"{whole}{frac}"

            rating_count_el = await item.query_selector("span.a-size-base.s-underline-text")
            rating_count_str = await rating_count_el.inner_text() if rating_count_el else "0"
            rating_count_int = int(rating_count_str.replace(",", "")) if rating_count_str.replace(",", "").isdigit() else 0

            hotness = min(rating_count_int / 100, 30)
            is_hot = hotness >= 60

            results.append({
                "asin": asin,
                "title": title[:500],
                "url": f"https://www.amazon.com/dp/{asin}",
                "price": price,
                "rating_count": rating_count_int,
                "hotness_score": round(hotness, 2),
                "is_hot": is_hot,
            })
        except Exception:
            continue

    return results


async def crawl_amazon(category_code: str, keywords: list[str]) -> dict:
    """爬取 Amazon 搜索结果。"""
    hot_links: list[dict] = []
    trend_signals: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        for kw in keywords:
            products = await crawl_amazon_search(page, kw)

            for prod in products:
                hot_links.append({
                    "category_code": category_code,
                    "section_key": "market",
                    "link_type": "product",
                    "platform": "amazon",
                    "title": prod["title"],
                    "url": prod["url"],
                    "description": f"ASIN: {prod['asin']}, Price: {prod['price']}, Ratings: {prod['rating_count']}",
                    "hotness_score": prod["hotness_score"],
                    "is_hot": prod["is_hot"],
                })

            if products:
                total_ratings = sum(p["rating_count"] for p in products)
                trend_signals.append({
                    "category_code": category_code,
                    "section_key": "market",
                    "signal_type": "social_mention",
                    "platform": "amazon",
                    "keyword": kw,
                    "title": f"Amazon Search: {kw}",
                    "metric_value": float(total_ratings),
                    "metric_unit": "ratings",
                    "trend_direction": "stable",
                    "summary": f"Amazon 搜索 '{kw}': {len(products)} 个热门商品, 总评分数 {total_ratings}",
                })

            await asyncio.sleep(random.uniform(3, 5))  # 请求间隔

        await browser.close()

    return {"hot_links": hot_links, "trend_signals": trend_signals}


async def crawl_all() -> dict:
    """Crawl all categories, return merged result."""
    all_hot_links: list[dict] = []
    all_trend_signals: list[dict] = []
    for cat, kws in AMAZON_KEYWORDS.items():
        result = await crawl_amazon(cat, kws)
        all_hot_links.extend(result["hot_links"])
        all_trend_signals.extend(result["trend_signals"])
        hot_count = sum(1 for l in result["hot_links"] if l["is_hot"])
        print(f"  {cat}: {len(result['hot_links'])} hot_links ({hot_count} hot), {len(result['trend_signals'])} trend_signals")
    return {"hot_links": all_hot_links, "trend_signals": all_trend_signals}


if __name__ == "__main__":
    result = asyncio.run(crawl_all())
    total_hl = len(result["hot_links"])
    total_ts = len(result["trend_signals"])
    print(f"\nTotal: {total_hl} hot_links, {total_ts} trend_signals")
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2, ensure_ascii=False))
