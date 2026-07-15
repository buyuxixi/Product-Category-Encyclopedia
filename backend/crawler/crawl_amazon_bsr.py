#!/usr/bin/env python3
"""Amazon Best Sellers 爬取器 — 爬取品类热销榜数据。

策略:
- 通过 Amazon Best Sellers 页面爬取 Top 20 产品
- 提取: BSR 排名、标题、价格、评分、评论数、ASIN
- 代理: HTTP_PROXY=http://127.0.0.1:7897
- 限流: 每个品类间隔 15 秒

数据推送到百科后端:
- hot_links: Amazon 产品链接 (link_type=product, platform=amazon)
- trend_signals: BSR 排名 + 评论数 + 评分

Usage:
    python crawl_amazon_bsr.py            # 爬取全品类
    python crawl_amazon_bsr.py --json     # 输出 JSON
    python crawl_amazon_bsr.py TENS_THERAPY # 单品类
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, UTC
from urllib.parse import quote_plus

import httpx

# 品类 → Amazon Best Sellers 节点 URL
# Amazon Best Sellers URL 格式: /Best-Sellers/zgbs/{node_id}
AMAZON_BSR_NODES: dict[str, dict] = {
    "TENS_THERAPY": {
        "node": "3760951",  # Health & Household > Health Care
        "keywords": ["TENS unit", "TENS machine"],
    },
    "HEAT_THERAPY": {
        "node": "3760961",  # Health & Household > Health Care > Pain Relief
        "keywords": ["heating pad", "heat therapy"],
    },
    "SHOULDER_NECK_HEAT_THERAPY": {
        "node": "3760961",
        "keywords": ["neck heating pad", "shoulder heating pad"],
    },
    "FAR_INFRARED": {
        "node": "3760961",
        "keywords": ["far infrared heating pad", "infrared sauna"],
    },
    "NIGHT_LIGHT": {
        "node": "228013",  # Tools & Home Improvement > Lighting
        "keywords": ["night light", "motion sensor night light"],
    },
    "PILL_ORGANIZER": {
        "node": "3760991",
        "keywords": ["pill organizer", "medicine organizer box", "weekly pill box"],
    },
    "PILL_SPLITTER": {
        "node": "8626404011",
        "keywords": ["pill splitter", "pill cutter", "pill crusher"],
    },
    "SEAT_CUSHION": {
        "node": "228013",
        "keywords": ["seat cushion", "tailbone cushion"],
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "DNT": "1",
}

REQUEST_INTERVAL = 15  # 秒，品类间间隔


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    # 支持美元 $29.99 和日元 JPY 3,230 格式
    text = text.replace('\xa0', ' ').strip()
    m = re.search(r"\$\s*([\d,]+\.?\d*)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"JPY\s*([\d,]+)", text)
    if m:
        # 日元转美元（粗略汇率 1 USD ≈ 150 JPY）
        jpy = float(m.group(1).replace(",", ""))
        return round(jpy / 150, 2)
    m = re.search(r"([\d,]+\.?\d*)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def parse_rating(text: str | None) -> float | None:
    if not text:
        return None
    m = re.search(r"(\d+\.?\d?)\s*out of\s*5", text, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+\.?\d?)\s*stars", text, re.I)
    if m:
        return float(m.group(1))
    return None


def parse_review_count(text: str | None) -> int:
    if not text:
        return 0
    # "1,234" or "1234" or "1.2K"
    text = text.strip().replace(",", "")
    if "K" in text.upper():
        m = re.search(r"(\d+\.?\d*)\s*K", text, re.I)
        if m:
            return int(float(m.group(1)) * 1000)
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    return 0


def extract_asin(url: str) -> str | None:
    m = re.search(r"/dp/([A-Z0-9]{10})", url)
    if m:
        return m.group(1)
    m = re.search(r"product\%2F([A-Z0-9]{10})", url)
    if m:
        return m.group(1)
    return None


def crawl_category_bs(category_code: str) -> list[dict]:
    """爬取 Amazon 搜索结果页 Top 产品 — 提取 ASIN/标题/价格/评分/评论数"""
    config = AMAZON_BSR_NODES.get(category_code)
    if not config:
        print(f"  [WARN] No BSR config for {category_code}")
        return []

    results = []
    client = httpx.Client(
        headers=HEADERS, timeout=30, follow_redirects=True,
        verify=False, proxy='http://127.0.0.1:7897',
    )

    for keyword in config["keywords"]:
        url = f"https://www.amazon.com/s?k={quote_plus(keyword)}&s=salesrank"
        print(f"  [Amazon] Searching: {keyword}")
        try:
            resp = client.get(url)
            if resp.status_code != 200:
                print(f"    -> HTTP {resp.status_code}")
                continue

            html = resp.text

            # 提取产品卡片 — 每个 data-asin 对应一个产品
            # 用正则找到每个产品区块的 ASIN，然后在区块内提取价格/评分/评论数
            asin_positions = [(m.start(), m.group(1)) for m in re.finditer(r'data-asin="([A-Z0-9]{10})"', html)]
            seen_asins = set()

            for pos, asin in asin_positions:
                if asin in seen_asins:
                    continue
                seen_asins.add(asin)

                # 提取该 ASIN 后面 12000 字符的产品区块
                block = html[pos:pos + 12000]

                # 跳过赞助产品
                if "Sponsored" in block[:1000] or "sponsored" in block[:1000].lower():
                    continue

                # 提取标题 — h2 > span 内的文本
                title_match = re.search(r'<h2[^>]*>.*?<span[^>]*>(.*?)</span>', block, re.S | re.I)
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else f"Amazon Product {asin}"

                # 提取价格 — <span class="a-offscreen">JPY 3,230</span> 或 <span class="a-offscreen">$29.99</span>
                price_match = re.search(r'class="a-offscreen"[^>]*>([^<]+)<', block)
                price = parse_price(price_match.group(1)) if price_match else None

                # 提取评分 — <span class="a-icon-alt">4.1 out of 5 stars</span>
                rating_match = re.search(r'class="a-icon-alt"[^>]*>(\d+\.?\d*)\s*out of\s*5', block, re.I)
                rating = float(rating_match.group(1)) if rating_match else None

                # 提取评论数 — aria-label="12,720 ratings" 或 aria-label="4.3 out of 5 stars, rating details"
                review_match = re.search(r'aria-label="([\d,]+)\s*(?:ratings?|reviews?)"', block, re.I)
                if not review_match:
                    review_match = re.search(r'aria-label="[\d.]+\s*out of\s*5\s*stars,\s*rating[^"]*?([\d,]+)\s*(?:ratings?|reviews?)"', block, re.I)
                if not review_match:
                    review_match = re.search(r'class="a-size-base[^"]*s-underline[^"]*"[^>]*>\s*([\d,]+)\s*<', block)
                review_count = parse_review_count(review_match.group(1)) if review_match else 0

                # BSR rank = 在非赞助产品中的排名
                rank = len([a for a in seen_asins if a == asin]) + len(results)

                product_url = f"https://www.amazon.com/dp/{asin}"

                results.append({
                    "asin": asin,
                    "title": title[:200],
                    "url": product_url,
                    "price": price,
                    "rating": rating,
                    "review_count": review_count,
                    "bsr_rank": len(results) + 1,
                    "keyword": keyword,
                    "category_code": category_code,
                })
                if price or rating or review_count:
                    print(f"    [{len(results)}] {title[:40]}... ${price or '?'} ⭐{rating or '?'} ({review_count} reviews)")
                else:
                    print(f"    [{len(results)}] {title[:40]}... (no price/rating data)")

            time.sleep(3)

        except Exception as e:
            print(f"    -> Error: {e}")

        time.sleep(REQUEST_INTERVAL)

    client.close()
    return results


def to_hot_links(products: list[dict]) -> list[dict]:
    """转换为 hot_links 格式"""
    hot_links = []
    for p in products:
        # 热度 = 评论数/10 + 评分*5 + 价格因素
        hotness = 0
        if p["review_count"]:
            hotness += min(p["review_count"] / 100, 30)
        if p["rating"]:
            hotness += p["rating"] * 3
        if p["bsr_rank"] <= 3:
            hotness += 15  # Top 3 加分
        elif p["bsr_rank"] <= 10:
            hotness += 5

        hot_links.append({
            "category_code": p["category_code"],
            "section_key": "market",
            "link_type": "product",
            "platform": "amazon",
            "title": p["title"],
            "url": p["url"],
            "description": f"${p['price'] or '?'} ⭐{p['rating'] or '?'} ({p['review_count']} reviews) — BSR #{p['bsr_rank']}",
            "hotness_score": round(hotness),
            "is_hot": hotness >= 20,
            "collected_at": datetime.now(UTC).isoformat(),
        })
    return hot_links


def to_trend_signals(products: list[dict]) -> list[dict]:
    """转换为 trend_signals 格式"""
    signals = []
    # 按关键词聚合统计
    kw_groups: dict[str, list[dict]] = {}
    for p in products:
        kw = p["keyword"]
        if kw not in kw_groups:
            kw_groups[kw] = []
        kw_groups[kw].append(p)

    for kw, items in kw_groups.items():
        if not items:
            continue
        avg_price = sum(p["price"] for p in items if p["price"]) / max(len([p for p in items if p["price"]]), 1)
        total_reviews = sum(p["review_count"] for p in items)
        avg_rating = sum(p["rating"] for p in items if p["rating"]) / max(len([p for p in items if p["rating"]]), 1)

        signals.append({
            "category_code": items[0]["category_code"],
            "section_key": "market",
            "signal_type": "product_insight",
            "platform": "amazon",
            "keyword": kw,
            "title": f"Amazon BSR: {kw}",
            "metric_value": round(avg_price, 2) if avg_price else 0,
            "metric_unit": "avg_price_usd",
            "trend_direction": "stable",
            "summary": f"Top {len(items)} products: avg ${avg_price:.2f}, avg ⭐{avg_rating:.1f}, total {total_reviews} reviews",
            "collected_at": datetime.now(UTC).isoformat(),
        })
    return signals


def crawl_all() -> tuple[list[dict], list[dict]]:
    """爬取所有品类的 Amazon BSR 数据"""
    all_hot_links = []
    all_trend_signals = []

    categories = list(AMAZON_BSR_NODES.keys())
    for i, code in enumerate(categories):
        if i > 0:
            print(f"  Waiting {REQUEST_INTERVAL}s...")
            time.sleep(REQUEST_INTERVAL)
        print(f"=== {code} ===")
        products = crawl_category_bs(code)
        print(f"  Found {len(products)} products")
        all_hot_links.extend(to_hot_links(products))
        all_trend_signals.extend(to_trend_signals(products))

    return all_hot_links, all_trend_signals


if __name__ == "__main__":
    from _guard import require_crawler_enabled

    require_crawler_enabled()
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        hl, ts = crawl_all()
        print(json.dumps({"hot_links": hl, "trend_signals": ts}, ensure_ascii=False, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] in AMAZON_BSR_NODES:
        products = crawl_category_bs(sys.argv[1])
        hl = to_hot_links(products)
        ts = to_trend_signals(products)
        print(json.dumps({"hot_links": hl, "trend_signals": ts}, ensure_ascii=False, indent=2))
    else:
        hl, ts = crawl_all()
        print(f"\nTotal: {len(hl)} hot_links, {len(ts)} trend_signals")
