#!/usr/bin/env python3
"""Reddit 单品类爬取器 — 每次只爬一个品类，避免 429 限流。

用法:
    python crawl_reddit_single.py HEAT_THERAPY
    python crawl_reddit_single.py TENS_THERAPY

设计:
    - 每次只发 2 个请求（1 个品类 × 2 个 subreddit）
    - 请求间隔 35 秒
    - 完成后直接登录 → 清旧 Reddit 数据 → 推送新数据
    - 配合 cron 错开执行：7 个品类 × 每天一次，间隔约 2 小时
"""
from __future__ import annotations

import json
import os
import sys
import time

# 必须先设置脚本路径
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

# 设置 API 地址
API_BASE = os.getenv("ENCYCLOPEDIA_API_BASE", "http://localhost:8010/api/v1")
os.environ["ENCYCLOPEDIA_API_BASE"] = API_BASE

from crawl_reddit import REDDIT_SOURCES, crawl_reddit, _try_rss_search


def crawl_single_category(category_code: str) -> dict:
    """爬取单个品类的 Reddit 数据。"""
    sources = REDDIT_SOURCES.get(category_code, [])
    if not sources:
        print(f"[ERROR] Unknown category: {category_code}")
        print(f"Available: {list(REDDIT_SOURCES.keys())}")
        return {"hot_links": [], "trend_signals": []}

    print(f"=== Reddit crawl: {category_code} ===")
    print(f"  Sources: {len(sources)} subreddit(s)")

    all_hot_links = []
    all_trend_signals = []

    for i, source in enumerate(sources):
        sub = source["subreddit"]
        kw = source["keyword"]

        # 第一个请求前也等 5 秒（防止和上一个 cron job 的请求撞车）
        if i == 0:
            time.sleep(5)

        print(f"  [{i+1}/{len(sources)}] r/{sub} q={kw} ...")
        posts = _try_rss_search(sub, kw)

        if not posts:
            print(f"    -> 0 posts (rate-limited or no results)")
            # 请求间隔 35 秒
            if i < len(sources) - 1:
                print(f"    waiting 35s before next request...")
                time.sleep(35)
            continue

        print(f"    -> {len(posts)} posts")
        for post in posts[:3]:
            print(f"       {post['title'][:60]}")

        # 用 crawl_reddit 的评分逻辑
        from crawl_reddit import _score_post
        total_interactions = 0
        valid_posts = 0

        for post in posts:
            comments = post.get("num_comments", 0)
            ups = post.get("ups", 0)
            days_ago = post.get("days_ago")

            score, is_hot = _score_post(comments, ups, days_ago)
            if score < 0:
                continue

            total_interactions += comments + ups
            valid_posts += 1

            all_hot_links.append({
                "category_code": category_code,
                "section_key": "users",
                "link_type": "discussion",
                "platform": "reddit",
                "title": post["title"][:500],
                "url": post["permalink"],
                "description": f"r/{sub} · {post.get('desc', '')[:200]}" if post.get("desc") else f"r/{sub}",
                "hotness_score": score,
                "is_hot": is_hot,
            })

        if valid_posts > 0:
            all_trend_signals.append({
                "category_code": category_code,
                "section_key": "market",
                "signal_type": "social_mention",
                "platform": "reddit",
                "keyword": kw,
                "title": f"Reddit r/{sub}: {kw}",
                "metric_value": float(total_interactions),
                "metric_unit": "interactions",
                "trend_direction": "up" if total_interactions > 10 else "stable",
                "summary": f"r/{sub}: {valid_posts} 帖, 总互动 {total_interactions}",
            })

        # 请求间隔 40 秒（Reddit 限流严格）
        if i < len(sources) - 1:
            print(f"    waiting 40s before next request...")
            time.sleep(40)

    print(f"\n  Total: {len(all_hot_links)} hot_links, {len(all_trend_signals)} trend_signals")
    return {"hot_links": all_hot_links, "trend_signals": all_trend_signals}


def push_single(category_code: str, crawl_result: dict) -> dict:
    """推送单品类 Reddit 数据到百科后端。

    只清理该品类的旧 Reddit hot_links（按 platform=reddit 过滤），
    不清理非 Reddit 数据。
    """
    import httpx

    # 登录
    username = os.getenv("CRAWLER_USERNAME", "admin")
    password = os.getenv("CRAWLER_PASSWORD", "")
    if not password:
        pass_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".crawler_password")
        if os.path.exists(pass_file):
            password = open(pass_file).read().strip()

    if not password:
        print("[ERROR] No CRAWLER_PASSWORD set")
        return {}

    print(f"\n=== Pushing {category_code} to {API_BASE} ===")
    resp = httpx.post(
        f"{API_BASE}/auth/local/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    cookies = dict(resp.cookies)
    print(f"  Logged in as {username}")

    # 清理该品类的旧 Reddit hot_links（只删 reddit 平台的，不删 YouTube/News）
    existing = httpx.get(
        f"{API_BASE}/categories/{category_code}/hot-links?days=365",
        timeout=15, cookies=cookies,
    )
    existing.raise_for_status()
    old_items = existing.json().get("items", [])
    reddit_old = [item for item in old_items if item.get("platform") == "reddit"]
    deleted = 0
    for item in reddit_old:
        link_id = item.get("id")
        if link_id:
            try:
                dr = httpx.delete(f"{API_BASE}/hot-links/{link_id}", timeout=10, cookies=cookies)
                if dr.status_code == 200:
                    deleted += 1
            except Exception:
                pass
    print(f"  Cleared {deleted} old Reddit links")

    # 清理该品类的旧 Reddit trend_signals
    # 通过删除整个品类的 trend_signals 然后只重推 Reddit 的会丢失其他平台数据
    # 所以改用：不删 trend_signals，直接追加（dedup_and_score 会去重）
    # 实际上 DELETE /categories/{code}/trend-signals 会删所有平台的，不能用
    # 只追加新的 Reddit 信号

    # 推送新的 hot_links
    hot_links = crawl_result.get("hot_links", [])
    trend_signals = crawl_result.get("trend_signals", [])

    if hot_links:
        resp = httpx.post(
            f"{API_BASE}/hot-links/batch",
            json={"items": hot_links},
            timeout=30, cookies=cookies,
        )
        resp.raise_for_status()
        hl_result = resp.json()
        print(f"  Hot links: {hl_result.get('inserted_count', 0)} inserted")

    if trend_signals:
        resp = httpx.post(
            f"{API_BASE}/trend-signals/batch",
            json={"items": trend_signals},
            timeout=30, cookies=cookies,
        )
        resp.raise_for_status()
        ts_result = resp.json()
        print(f"  Trend signals: {ts_result.get('inserted_count', 0)} inserted")

    return {"hot_links_pushed": len(hot_links), "trend_signals_pushed": len(trend_signals)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crawl_reddit_single.py <CATEGORY_CODE>")
        print(f"Available: {' '.join(REDDIT_SOURCES.keys())}")
        sys.exit(1)

    category_code = sys.argv[1].upper()

    # 1. Crawl
    result = crawl_single_category(category_code)

    # 2. Push
    if result["hot_links"] or result["trend_signals"]:
        push_single(category_code, result)
    else:
        print("\n  No data to push (all requests were rate-limited)")

    print("\n✅ Done")
