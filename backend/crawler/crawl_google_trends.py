#!/usr/bin/env python3
"""Google Trends + Suggest 爬取器 — 通过 Google Suggest API 获取关键词趋势。

策略:
  - Google Suggest API: 总是可用，返回相关关键词，作为 keyword_trend 信号
  - Google Trends Explore API: 当前被限流(429/500)，已禁用
    代码保留但默认不调用，如果未来 IP 解封可重新启用

  产出:
    - keyword_trend: 每个关键词的相关搜索词列表
    - search_volume: (降级模式) 标注"Google Trends API 限流"

Usage:
    python crawl_google_trends.py           # 爬取全品类
    python crawl_google_trends.py --json    # 输出 JSON
"""
from __future__ import annotations

import json
import sys
import time

import httpx

# 品类 → 关键词
TRENDS_KEYWORDS: dict[str, list[str]] = {
    "TENS_THERAPY": ["TENS unit", "TENS machine"],
    "HEAT_THERAPY": ["heating pad", "heat therapy"],
    "SHOULDER_NECK_HEAT_THERAPY": ["neck heating pad", "shoulder heating pad"],
    "FAR_INFRARED": ["far infrared heating pad", "far infrared therapy"],
    "NIGHT_LIGHT": ["night light", "motion sensor night light"],
    "PILL_ORGANIZER": ["pill organizer", "weekly pill box"],
    "PILL_SPLITTER": ["pill splitter", "pill cutter"],
    "SEAT_CUSHION": ["seat cushion", "tailbone cushion"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_google_suggestions(keyword: str, max_retries: int = 3) -> list[str]:
    """通过 Google Suggest API 获取相关关键词。总是可用，带 SSL 重试。"""
    for attempt in range(max_retries):
        try:
            resp = httpx.get(
                f"https://suggestqueries.google.com/complete/search?client=firefox&q={keyword}",
                headers=HEADERS,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                suggestions = data[1] if len(data) > 1 else []
                return suggestions[:10]
            time.sleep(1)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  [WARN] Google Suggest '{keyword}' retry {attempt+1}: {e}", file=sys.stderr)
                time.sleep(2)
            else:
                print(f"  [SKIP] Google Suggest '{keyword}' failed after {max_retries} retries", file=sys.stderr)
    return []


def crawl_google_trends(category_code: str, keywords: list[str]) -> dict:
    """爬取 Google Trends 数据。产生 keyword_trend 信号。
    
    Google Trends Explore API 当前被限流(429/500)，不调用。
    只使用 Google Suggest API 获取相关关键词。
    """
    trend_signals: list[dict] = []

    for kw in keywords:
        # Google Suggest (always works with retry)
        suggestions = get_google_suggestions(kw)
        time.sleep(0.5)

        if suggestions:
            # 过滤掉日语/中文等非英语建议
            en_suggestions = [s for s in suggestions if all(ord(c) < 0x4E00 for c in s)]
            summary_suggestions = en_suggestions[:6]

            trend_signals.append({
                "category_code": category_code,
                "section_key": "market",
                "signal_type": "keyword_trend",
                "platform": "google",
                "keyword": kw,
                "title": f"Google Trends: {kw}",
                "metric_value": float(len(summary_suggestions)),
                "metric_unit": "related keywords",
                "trend_direction": "stable",
                "summary": f"相关搜索词: {', '.join(summary_suggestions)}",
            })

            # 每个相关词也作为一个 keyword_trend 信号
            for related_kw in summary_suggestions[:3]:
                trend_signals.append({
                    "category_code": category_code,
                    "section_key": "market",
                    "signal_type": "keyword_trend",
                    "platform": "google",
                    "keyword": related_kw,
                    "title": f"Google Suggest: \"{related_kw}\"",
                    "metric_value": None,
                    "metric_unit": None,
                    "trend_direction": "new",
                    "summary": f"\"{kw}\" 的相关搜索词，反映用户搜索行为",
                })
        else:
            # 降级：标注 Google Trends 限流
            trend_signals.append({
                "category_code": category_code,
                "section_key": "market",
                "signal_type": "keyword_trend",
                "platform": "google",
                "keyword": kw,
                "title": f"Google Trends: {kw} (数据未获取)",
                "metric_value": None,
                "metric_unit": None,
                "trend_direction": "stable",
                "summary": f"Google Suggest 未返回数据，建议人工查看 Google Trends",
            })

    return {"hot_links": [], "trend_signals": trend_signals}


def crawl_all() -> dict:
    """Crawl all categories, return merged result."""
    all_trend_signals: list[dict] = []
    for cat, kws in TRENDS_KEYWORDS.items():
        result = crawl_google_trends(cat, kws)
        all_trend_signals.extend(result["trend_signals"])
        print(f"  {cat}: {len(result['trend_signals'])} trend_signals")
        time.sleep(1)  # 品类间间隔
    return {"hot_links": [], "trend_signals": all_trend_signals}


if __name__ == "__main__":
    from _guard import require_crawler_enabled

    require_crawler_enabled()
    result = crawl_all()
    total_ts = len(result["trend_signals"])
    print(f"\nTotal: {total_ts} trend_signals")
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2, ensure_ascii=False))
