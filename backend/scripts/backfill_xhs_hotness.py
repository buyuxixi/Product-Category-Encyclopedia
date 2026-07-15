#!/usr/bin/env python3
"""回刷小红书 hot_links 热度到 0–100 归一化分。

公式: min(赞/100,40) + min(藏/80,30) + min(评/10,20)，is_hot ≥ 50。
从 description 解析 ❤ / 💬 / ⭐ 后重写 hotness_score / is_hot。

使用方式：
    cd backend
    DATABASE_URL=mysql+pymysql://encyclopedia:encyclopedia_dev@127.0.0.1:3308/category_encyclopedia?charset=utf8mb4 \\
      python scripts/backfill_xhs_hotness.py           # dry-run
    ... python scripts/backfill_xhs_hotness.py --apply # 写入
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from scripts.import_cleaned_xhs import (  # noqa: E402
    hotness_from_metrics,
    parse_metrics_from_description,
)


def fetch_xhs_links() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, title, description, hotness_score, is_hot
                FROM hot_links
                WHERE platform = 'xiaohongshu'
                ORDER BY id
                """
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def plan_updates(rows: list[dict]) -> list[dict]:
    planned: list[dict] = []
    for row in rows:
        metrics = parse_metrics_from_description(row.get("description"))
        if metrics is None:
            continue
        likes, comments, collections = metrics
        new_score, new_is_hot = hotness_from_metrics(likes, comments, collections)
        old_score = float(row["hotness_score"] or 0)
        old_is_hot = bool(row["is_hot"])
        if old_score == new_score and old_is_hot == new_is_hot:
            continue
        planned.append(
            {
                "id": row["id"],
                "title": row["title"],
                "old_score": old_score,
                "new_score": new_score,
                "old_is_hot": old_is_hot,
                "new_is_hot": new_is_hot,
                "likes": likes,
                "comments": comments,
                "collections": collections,
            }
        )
    return planned


def apply_updates(planned: list[dict]) -> int:
    if not planned:
        return 0
    with engine.begin() as conn:
        for item in planned:
            conn.execute(
                text(
                    """
                    UPDATE hot_links
                    SET hotness_score = :score, is_hot = :is_hot
                    WHERE id = :id AND platform = 'xiaohongshu'
                    """
                ),
                {
                    "score": item["new_score"],
                    "is_hot": 1 if item["new_is_hot"] else 0,
                    "id": item["id"],
                },
            )
    return len(planned)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="回刷小红书 hotness_score = 0-100 分段封顶"
    )
    parser.add_argument("--apply", action="store_true", help="写入数据库；默认 dry-run")
    args = parser.parse_args()

    rows = fetch_xhs_links()
    planned = plan_updates(rows)
    parsed_ok = sum(
        1 for row in rows if parse_metrics_from_description(row.get("description"))
    )
    unparsable = len(rows) - parsed_ok

    print(
        f"小红书 hot_links 共 {len(rows)} 条，可解析 {parsed_ok}，"
        f"待更新 {len(planned)}，无法解析 {unparsable}"
    )
    for item in planned[:15]:
        print(
            f"  [{item['id']}] {item['old_score']:.1f} → {item['new_score']:.1f} "
            f"(❤{item['likes']}/100 + ⭐{item['collections']}/80 + 💬{item['comments']}/10) "
            f"is_hot {item['old_is_hot']}→{item['new_is_hot']} | {str(item['title'])[:40]}"
        )
    if len(planned) > 15:
        print(f"  ... 另有 {len(planned) - 15} 条")

    if not args.apply:
        print("Dry run：未写入。使用 --apply 执行更新。")
        return

    updated = apply_updates(planned)
    print(f"已更新 {updated} 条。")


if __name__ == "__main__":
    main()
