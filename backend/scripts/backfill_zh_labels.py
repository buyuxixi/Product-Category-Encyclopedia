#!/usr/bin/env python3
"""回填脚本 — 为数据库中已有的 hot_links / trend_signals 记录批量生成中文标签。

执行前提：已执行 DB Migration (add_zh_label_columns.sql)。

使用方式：
    cd backend
    # 确保环境有 LLM_API_KEY；DATABASE_URL 默认连 localhost:3308
    python scripts/backfill_zh_labels.py            # 回填缺标签的记录
    python scripts/backfill_zh_labels.py --force     # 覆盖已有中文标签（改 prompt 后重跑）
    python scripts/backfill_zh_labels.py --dry-run  # 只统计不写入
    python scripts/backfill_zh_labels.py --hot-links-only
    python scripts/backfill_zh_labels.py --trend-signals-only

注意：此脚本不触发爬虫，只处理已有数据；读写均走数据库。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 添加 backend 到 sys.path，以便导入 app 模块
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "crawler"))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from translate_zh import translate_hot_links, translate_trend_signals  # noqa: E402


def _fetch_hot_links() -> list[dict]:
    """从 DB 拉取全部 hot_links。"""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, platform, title, description, title_zh, description_zh
                FROM hot_links
                ORDER BY id
                """
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def _fetch_trend_signals() -> list[dict]:
    """从 DB 拉取全部 trend_signals。"""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, signal_type, keyword, title, summary, title_zh, summary_zh
                FROM trend_signals
                ORDER BY id
                """
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def _patch_via_db_hot_links(links: list[dict]) -> int:
    """直接通过数据库更新 hot_links 的中文字段。"""
    updated = 0
    with engine.connect() as conn:
        for link in links:
            title_zh = link.get("title_zh")
            desc_zh = link.get("description_zh")
            link_id = link.get("id")
            if not link_id or not title_zh:
                continue
            conn.execute(
                text("UPDATE hot_links SET title_zh = :t, description_zh = :d WHERE id = :id"),
                {"t": str(title_zh)[:200], "d": desc_zh or "", "id": link_id},
            )
            updated += 1
        conn.commit()
    return updated


def _patch_via_db_trend_signals(signals: list[dict]) -> int:
    """直接通过数据库更新 trend_signals 的中文字段。"""
    updated = 0
    with engine.connect() as conn:
        for sig in signals:
            title_zh = sig.get("title_zh")
            summary_zh = sig.get("summary_zh")
            sig_id = sig.get("id")
            if not sig_id or not title_zh:
                continue
            conn.execute(
                text("UPDATE trend_signals SET title_zh = :t, summary_zh = :s WHERE id = :id"),
                {"t": str(title_zh)[:200], "s": summary_zh or "", "id": sig_id},
            )
            updated += 1
        conn.commit()
    return updated


def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    hot_only = "--hot-links-only" in sys.argv
    trend_only = "--trend-signals-only" in sys.argv

    print("=" * 60)
    print("中文标签回填脚本" + (" [FORCE]" if force else ""))
    print("=" * 60)

    if not os.getenv("LLM_API_KEY") and not dry_run:
        print("[ERROR] LLM_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    if not trend_only:
        print("\n📥 Fetching hot_links from DB...")
        hot_links = _fetch_hot_links()
        need_hl = hot_links if force else [l for l in hot_links if not l.get("title_zh")]
        print(f"  Total: {len(hot_links)}, need translation: {len(need_hl)}")
    else:
        need_hl = []

    if not hot_only:
        print("\n📥 Fetching trend_signals from DB...")
        trend_signals = _fetch_trend_signals()
        need_ts = trend_signals if force else [s for s in trend_signals if not s.get("title_zh")]
        print(f"  Total: {len(trend_signals)}, need translation: {len(need_ts)}")
    else:
        need_ts = []

    if dry_run:
        print("\n🟡 Dry-run mode: not writing to DB")
        print(f"  Would translate {len(need_hl)} hot_links, {len(need_ts)} trend_signals")
        return

    if not need_hl and not need_ts:
        print("\n✅ All records already have Chinese labels. Nothing to do.")
        return

    total_updated = 0
    if need_hl:
        print(f"\n🌐 Translating {len(need_hl)} hot_links...")
        translate_hot_links(need_hl, force=force)
        updated = _patch_via_db_hot_links(need_hl)
        total_updated += updated
        print(f"  ✅ Updated {updated} hot_links in DB")

    if need_ts:
        print(f"\n🌐 Translating {len(need_ts)} trend_signals...")
        translate_trend_signals(need_ts, force=force)
        updated = _patch_via_db_trend_signals(need_ts)
        total_updated += updated
        print(f"  ✅ Updated {updated} trend_signals in DB")

    print(f"\n{'=' * 60}")
    print(f"✅ Done! Total records updated: {total_updated}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
