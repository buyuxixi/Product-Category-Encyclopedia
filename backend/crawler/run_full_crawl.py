#!/usr/bin/env python3
"""End-to-end runner: crawl → dedup → login → push → verify.

Runs all enabled crawlers sequentially, merges results, deduplicates,
authenticates with the encyclopedia backend, pushes via batch API,
and verifies data is readable.

默认运行: Google News + Reddit + YouTube (如有 API Key) + Google Trends (仅 trend_signals)
Amazon 是可选的 (需要 Playwright, 常被拦截)

Usage:
    # 默认运行所有爬取源
    python run_full_crawl.py

    # With env overrides
    ENCYCLOPEDIA_API_BASE=http://localhost:8010/api/v1 python run_full_crawl.py

    # Save output to file for inspection
    python run_full_crawl.py --save /tmp/crawl_output.json
"""
from __future__ import annotations

import json
import os
import sys

# Resolve scripts dir relative to this file
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

# Set API base from env or default
API_BASE = os.getenv("ENCYCLOPEDIA_API_BASE", "http://localhost:8010/api/v1")
os.environ["ENCYCLOPEDIA_API_BASE"] = API_BASE


def main():
    import httpx

    # Step 1: Crawl all enabled sources (sequential, each optional via try/except)
    print("=" * 60)
    print("Step 1: Crawling data sources...")
    print("=" * 60)

    all_results = []

    # P1: Google News (always works, no auth needed, fastest)
    try:
        from crawl_google_news import crawl_all
        r = crawl_all()
        all_results.append(r)
        print(f"  Google News: {len(r['hot_links'])} hot_links, {len(r['trend_signals'])} trend_signals")
    except Exception as e:
        print(f"  [SKIP] Google News failed: {e}")

    # P1: Reddit (JSON API with RSS fallback, rate-limited)
    try:
        from crawl_reddit import crawl_all
        r = crawl_all()
        all_results.append(r)
        print(f"  Reddit: {len(r['hot_links'])} hot_links, {len(r['trend_signals'])} trend_signals")
    except Exception as e:
        print(f"  [SKIP] Reddit: {e}")

    # P2: YouTube (NO API key needed — parses search results page HTML)
    try:
        from crawl_youtube import crawl_all
        r = crawl_all()
        all_results.append(r)
        print(f"  YouTube: {len(r['hot_links'])} hot_links, {len(r['trend_signals'])} trend_signals")
    except Exception as e:
        print(f"  [SKIP] YouTube: {e}")

    # P2: TikTok (requires Playwright browser, slower but gets trending videos)
    try:
        from crawl_tiktok import crawl_all
        r = crawl_all()
        all_results.append(r)
        print(f"  TikTok: {len(r['hot_links'])} hot_links, {len(r['trend_signals'])} trend_signals")
    except ImportError:
        print("  [SKIP] TikTok: playwright not installed")
    except Exception as e:
        print(f"  [SKIP] TikTok: {e}")

    # P0: Google Trends (trend_signals only, requires pytrends, often rate-limited)
    try:
        from crawl_google_trends import crawl_all
        r = crawl_all()
        all_results.append(r)
        print(f"  Google Trends: {len(r['hot_links'])} hot_links, {len(r['trend_signals'])} trend_signals")
    except ImportError:
        print("  [SKIP] Google Trends: pytrends not installed")
    except Exception as e:
        print(f"  [SKIP] Google Trends: {e}")

    # Amazon is optional (needs Playwright, often blocked) — not run by default
    # To enable: from crawl_amazon import crawl_all; r = crawl_all()

    if not all_results:
        print("\nFATAL: No crawlers succeeded. Exiting.")
        sys.exit(1)

    # Step 2: Merge and dedup
    print("\n" + "=" * 60)
    print("Step 2: Merging and deduplicating...")
    print("=" * 60)
    from dedup_and_score import merge_results
    merged = merge_results(*all_results)
    print(f"  Total: {len(merged['hot_links'])} hot_links, {len(merged['trend_signals'])} trend_signals")

    # Step 3: Login and push
    print("\n" + "=" * 60)
    print(f"Step 3: Pushing to {API_BASE}...")
    print("=" * 60)
    from push_to_encyclopedia import login, push_all
    cookies = login()
    if not cookies:
        print("FATAL: Cannot login. Exiting.")
        sys.exit(1)
    summary = push_all(merged, cookies=cookies)

    # Step 4: Verify
    print("\n" + "=" * 60)
    print("Step 4: Verifying...")
    print("=" * 60)
    categories = [
        "HEAT_THERAPY",
        "SHOULDER_NECK_HEAT_THERAPY",
        "FAR_INFRARED",
        "TENS_THERAPY",
        "NIGHT_LIGHT",
        "MEDICATION_MANAGEMENT",
        "SEAT_CUSHION",
    ]
    for cat in categories:
        try:
            resp = httpx.get(f"{API_BASE}/categories/{cat}/hot-links?days=1", timeout=10, cookies=cookies)
            if resp.status_code == 200:
                data = resp.json()
                count = len(data.get("items", []))
                hot = sum(1 for i in data.get("items", []) if i.get("is_hot"))
                print(f"  {cat}: {count} hot_links ({hot} is_hot)")
            else:
                print(f"  {cat}: {resp.status_code} (may not exist in DB)")
        except Exception as e:
            print(f"  {cat}: ERROR - {e}")

    # Save output if requested
    if "--save" in sys.argv:
        idx = sys.argv.index("--save")
        path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "/tmp/crawl_output.json"
        with open(path, "w") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        print(f"\n  Saved to {path}")

    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
