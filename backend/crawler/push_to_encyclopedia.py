#!/usr/bin/env python3
"""推送脚本 — 将爬取结果通过 Batch API 推送到品类百科后端。

调用:
  POST /api/v1/hot-links/batch (max 500 items per batch)
  POST /api/v1/trend-signals/batch (max 500 items per batch)

Usage:
    # 从 stdin 接收 JSON
    echo '{"hot_links": [...], "trend_signals": [...]}' | python push_to_encyclopedia.py

    # 从文件接收 JSON
    python push_to_encyclopedia.py --file results.json

    # 测试连接
    python push_to_encyclopedia.py --test
"""
from __future__ import annotations

import json
import os
import sys

import httpx

API_BASE = os.getenv("ENCYCLOPEDIA_API_BASE", "http://localhost:8010/api/v1")
BATCH_SIZE = 500
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")


def push_hot_links(items: list[dict], cookies: dict | None = None) -> dict:
    """推送 hot_links 到百科后端，分批每 500 条。"""
    total_inserted = 0
    total_skipped: list[str] = []
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i : i + BATCH_SIZE]
        payload = {"items": batch}
        try:
            resp = httpx.post(f"{API_BASE}/hot-links/batch", json=payload, timeout=30, cookies=cookies)
            resp.raise_for_status()
            result = resp.json()
            total_inserted += result.get("inserted_count", 0)
            total_skipped.extend(result.get("skipped", []))
        except Exception as e:
            print(f"  [ERROR] hot-links batch {i // BATCH_SIZE} failed: {e}", file=sys.stderr)
    return {"inserted": total_inserted, "skipped": total_skipped}


def push_trend_signals(items: list[dict], cookies: dict | None = None) -> dict:
    """推送 trend_signals 到百科后端。"""
    total_inserted = 0
    total_skipped: list[str] = []
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i : i + BATCH_SIZE]
        payload = {"items": batch}
        try:
            resp = httpx.post(f"{API_BASE}/trend-signals/batch", json=payload, timeout=30, cookies=cookies)
            resp.raise_for_status()
            result = resp.json()
            total_inserted += result.get("inserted_count", 0)
            total_skipped.extend(result.get("skipped", []))
        except Exception as e:
            print(f"  [ERROR] trend-signals batch {i // BATCH_SIZE} failed: {e}", file=sys.stderr)
    return {"inserted": total_inserted, "skipped": total_skipped}


def login(username: str | None = None, password: str | None = None) -> dict | None:
    """登录获取 session cookie。从环境变量读取凭证。"""
    username = username or os.getenv("CRAWLER_USERNAME", "admin")
    password = password or os.getenv("CRAWLER_PASSWORD", "")
    if not password:
        print("  [ERROR] CRAWLER_PASSWORD not set. Set it via env: export CRAWLER_PASSWORD=xxx", file=sys.stderr)
        return None
    try:
        resp = httpx.post(
            f"{API_BASE}/auth/local/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        resp.raise_for_status()
        # Extract cookies from response
        cookies = dict(resp.cookies)
        if cookies:
            print(f"  ✅ Logged in as {username}")
            return cookies
        print("  [WARN] Login succeeded but no cookies returned", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [ERROR] Login failed: {e}", file=sys.stderr)
        return None


def clear_category_hot_links(cookies: dict | None, category_code: str) -> int:
    """删除某品类的全部旧 hot_links，为新数据让路。每次爬取前调用，实现「覆盖」而非「累积」。"""
    try:
        resp = httpx.get(
            f"{API_BASE}/categories/{category_code}/hot-links?days=365",
            timeout=15, cookies=cookies,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        deleted = 0
        for item in items:
            link_id = item.get("id")
            if not link_id:
                continue
            try:
                dr = httpx.delete(f"{API_BASE}/hot-links/{link_id}", timeout=10, cookies=cookies)
                if dr.status_code == 200:
                    deleted += 1
            except Exception:
                pass
        return deleted
    except Exception as e:
        print(f"  [WARN] Clear hot_links for {category_code} failed: {e}", file=sys.stderr)
        return 0


def clear_category_trend_signals(cookies: dict | None, category_code: str) -> int:
    """删除某品类的全部旧 trend_signals，实现覆盖模式。"""
    try:
        resp = httpx.delete(
            f"{API_BASE}/categories/{category_code}/trend-signals",
            timeout=15, cookies=cookies,
        )
        resp.raise_for_status()
        return resp.json().get("deleted", 0)
    except Exception as e:
        print(f"  [WARN] Clear trend_signals for {category_code} failed: {e}", file=sys.stderr)
        return 0


def push_all(crawl_result: dict, cookies: dict | None = None) -> dict:
    """推送全部爬取结果，并发送飞书通知。

    流程：清理旧数据 → 推送新数据 → 飞书通知 → 更新时间戳。
    每品类最多保留 max_per_category 条（按热度排序）。
    """
    # Auto-login if no cookies provided and API requires auth
    if cookies is None:
        cookies = login()

    # 每品类最多保留条数
    max_per_category = int(os.getenv("MAX_HOTLINKS_PER_CATEGORY", "10"))

    # 收集本次爬取涉及的所有品类
    crawled_cats = set()
    for link in crawl_result.get("hot_links", []):
        crawled_cats.add(link.get("category_code", ""))
    for sig in crawl_result.get("trend_signals", []):
        crawled_cats.add(sig.get("category_code", ""))

    # Step 0: 清理旧数据（覆盖模式，不累积）
    print(f"\n🧹 Clearing old data for {len(crawled_cats)} categories...")
    total_cleared_hl = 0
    total_cleared_ts = 0
    for cat_code in sorted(crawled_cats):
        if not cat_code:
            continue
        cleared_hl = clear_category_hot_links(cookies, cat_code)
        cleared_ts = clear_category_trend_signals(cookies, cat_code)
        if cleared_hl or cleared_ts:
            print(f"  {cat_code}: cleared {cleared_hl} hot_links, {cleared_ts} trend_signals")
            total_cleared_hl += cleared_hl
            total_cleared_ts += cleared_ts
    print(f"  Total cleared: {total_cleared_hl} hot_links, {total_cleared_ts} trend_signals")

    # Step 1: 按品类分组，每品类取热度 top N
    from collections import defaultdict
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for link in crawl_result.get("hot_links", []):
        by_cat[link.get("category_code", "")].append(link)

    filtered_links: list[dict] = []
    for cat, links in by_cat.items():
        # 按热度降序排列，取前 max_per_category 条
        sorted_links = sorted(
            links,
            key=lambda x: x.get("hotness_score") or 0,
            reverse=True,
        )
        filtered_links.extend(sorted_links[:max_per_category])

    # trend_signals 按品类+类型分组截断，避免重复卡片噪音
    by_cat_ts: dict[str, list[dict]] = defaultdict(list)
    for sig in crawl_result.get("trend_signals", []):
        by_cat_ts[sig.get("category_code", "")].append(sig)
    filtered_signals: list[dict] = []
    for cat, sigs in by_cat_ts.items():
        # 按类型分组，每类型取不同数量
        by_type: dict[str, list[dict]] = defaultdict(list)
        for sig in sigs:
            by_type[sig.get("signal_type", "")].append(sig)
        for stype, type_sigs in by_type.items():
            # keyword_trend 保留多一些(8), 其他类型限 3
            limit = 8 if stype == "keyword_trend" else 3
            filtered_signals.extend(type_sigs[:limit])

    # Step 2: 推送新数据
    print(f"\n📤 Pushing to encyclopedia API ({API_BASE})...")
    print(f"  {len(filtered_links)} hot_links ({max_per_category}/cat max), {len(filtered_signals)} trend_signals")
    hl_result = push_hot_links(filtered_links, cookies=cookies)
    ts_result = push_trend_signals(filtered_signals, cookies=cookies)
    summary = {
        "hot_links_inserted": hl_result["inserted"],
        "hot_links_skipped": len(hl_result["skipped"]),
        "trend_signals_inserted": ts_result["inserted"],
        "trend_signals_skipped": len(ts_result["skipped"]),
        "old_links_cleared": total_cleared_hl,
        "old_trend_signals_cleared": total_cleared_ts,
    }
    print(f"  ✅ Hot links: {summary['hot_links_inserted']} inserted, {summary['hot_links_skipped']} skipped")
    print(f"  ✅ Trend signals: {summary['trend_signals_inserted']} inserted, {summary['trend_signals_skipped']} skipped")
    print(f"  🧹 Old links cleared: {total_cleared_hl}, old trend_signals cleared: {total_cleared_ts}")

    # 发送飞书通知
    send_feishu_notification(summary, {"hot_links": filtered_links, "trend_signals": filtered_signals})

    # 更新各品类 market section 顶部时间戳
    update_market_sections(cookies, {"hot_links": filtered_links, "trend_signals": filtered_signals})

    return summary


def update_market_sections(cookies: dict | None, crawl_result: dict) -> None:
    """更新各品类 market section 顶部的数据采集时间戳，替换静态占位符。"""
    from datetime import datetime, UTC

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    new_header = f"> ⏰ **数据采集时间**: {today} | **数据状态**: 爬取Agent已自动更新 ✅"

    # 收集本次爬取涉及的品类
    crawled_cats = set()
    for link in crawl_result.get("hot_links", []):
        crawled_cats.add(link.get("category_code", ""))
    for sig in crawl_result.get("trend_signals", []):
        crawled_cats.add(sig.get("category_code", ""))

    updated = 0
    for cat_code in crawled_cats:
        if not cat_code:
            continue
        try:
            # 读取当前 market section
            resp = httpx.get(f"{API_BASE}/categories/{cat_code}", timeout=10, cookies=cookies)
            resp.raise_for_status()
            data = resp.json()
            market_section = None
            for s in data.get("sections", []):
                if s["section_key"] == "market":
                    market_section = s
                    break
            if not market_section:
                continue

            content = market_section["content"]

            # 替换第一行 blockquote（以 > 开头的行）
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith(">"):
                    lines[i] = new_header
                    break
            else:
                # 如果没有 blockquote，在开头添加
                lines.insert(0, new_header)
                lines.insert(1, "")

            new_content = "\n".join(lines)

            # PUT 更新
            resp = httpx.put(
                f"{API_BASE}/categories/{cat_code}/sections/market",
                json={
                    "content": new_content,
                    "evidence_listing_ids": [],
                    "evidence_source_ids": [],
                    "generation_mode": "generated",
                },
                timeout=15,
                cookies=cookies,
            )
            if resp.status_code == 200:
                updated += 1
            else:
                print(f"  [WARN] Update market section for {cat_code}: {resp.status_code}", file=sys.stderr)
        except Exception as e:
            print(f"  [WARN] Update market section for {cat_code} failed: {e}", file=sys.stderr)

    if updated:
        print(f"  ✅ Updated {updated} market section timestamps")


def send_feishu_notification(summary: dict, crawl_result: dict) -> None:
    """向飞书群发送爬取摘要通知（自定义机器人 Webhook，不依赖 Hermes Gateway）。"""
    if not FEISHU_WEBHOOK_URL:
        return  # No webhook configured — skip silently

    from datetime import datetime, UTC

    total_hl = len(crawl_result.get("hot_links", []))
    total_ts = len(crawl_result.get("trend_signals", []))
    hot_count = sum(1 for l in crawl_result.get("hot_links", []) if l.get("is_hot"))

    # 按品类统计
    by_category: dict[str, dict] = {}
    for link in crawl_result.get("hot_links", []):
        cat = link.get("category_code", "UNKNOWN")
        by_category.setdefault(cat, {"hot_links": 0, "is_hot": 0})
        by_category[cat]["hot_links"] += 1
        if link.get("is_hot"):
            by_category[cat]["is_hot"] += 1

    cat_lines = "\n".join(
        f"  {cat}: {d['hot_links']} 条链接（{d['is_hot']} 条热点）"
        for cat, d in sorted(by_category.items())
    )

    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # 取 Top 3 最热链接
    top_hot = sorted(
        [l for l in crawl_result.get("hot_links", []) if l.get("is_hot")],
        key=lambda x: x.get("hotness_score") or 0,
        reverse=True
    )[:3]

    top_lines = ""
    if top_hot:
        top_lines = "\n\n**🔥 今日 Top 热点**:\n" + "\n".join(
            f"  {i+1}. [{l.get('platform','').upper()}] {l.get('title','')[:50]}"
            for i, l in enumerate(top_hot)
        )

    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "🔥 品类百科 — 每日热点爬取完成"},
                "template": "red",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**爬取时间**: {now_str}\n**写入数据**:\n  📌 Hot Links: {summary['hot_links_inserted']} 条入库（{summary['hot_links_skipped']} 条跳过）\n  📊 Trend Signals: {summary['trend_signals_inserted']} 条入库（{summary['trend_signals_skipped']} 条跳过）\n  🔥 is_hot 热点: {hot_count} 条\n\n**按品类分布**:\n{cat_lines}{top_lines}",
                    },
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "🔗 查看品类百科"},
                            "url": "http://localhost:4180",
                            "type": "primary",
                        },
                    ],
                },
            ],
        },
    }

    try:
        resp = httpx.post(FEISHU_WEBHOOK_URL, json=message, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            print(f"  ✅ 飞书通知已发送")
        else:
            print(f"  [WARN] 飞书返回: {result}", file=sys.stderr)
    except Exception as e:
        print(f"  [WARN] 飞书通知发送失败: {e}", file=sys.stderr)


def test_connection() -> bool:
    """测试后端 API 是否可达。"""
    try:
        resp = httpx.get(f"{API_BASE}/dashboard", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ API reachable. Categories: {data.get('category_count', '?')}, Listings: {data.get('listing_count', '?')}")
        return True
    except Exception as e:
        print(f"❌ API not reachable at {API_BASE}: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_connection()
        sys.exit(0)

    # 从 stdin 或文件读取爬取结果
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        filepath = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
        if not filepath:
            print("Error: --file requires a file path", file=sys.stderr)
            sys.exit(1)
        with open(filepath, "r", encoding="utf-8") as f:
            crawl_result = json.load(f)
    else:
        # 从 stdin 读取
        stdin_data = sys.stdin.read().strip()
        if not stdin_data:
            # 没有输入，运行测试
            print("No input provided. Running connection test...")
            test_connection()
            sys.exit(0)
        crawl_result = json.loads(stdin_data)

    result = push_all(crawl_result)
    print(json.dumps(result, indent=2))
