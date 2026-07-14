#!/usr/bin/env python3
"""将小红书 cleaned JSON 转换并增量推送到统一 crawler Batch API。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from crawler.push_to_encyclopedia import push_incremental
from scripts.import_cleaned_xhs import build_crawl_result


def main() -> None:
    parser = argparse.ArgumentParser(description="转换并推送小红书 cleaned JSON")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--note-limit", type=int, default=10)
    parser.add_argument("--comment-limit", type=int, default=2)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--push", action="store_true", help="通过 Batch API 增量 upsert")
    args = parser.parse_args()

    result = build_crawl_result(
        args.data_dir,
        note_limit=args.note_limit,
        comment_limit=args.comment_limit,
    )
    print(
        f"转换完成：hot_links={len(result['hot_links'])}, "
        f"trend_signals={len(result['trend_signals'])}"
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"已保存：{args.output}")

    if not args.push:
        print("Dry run：未写入数据库。使用 --push 执行增量 upsert。")
        return

    summary = push_incremental(result)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
