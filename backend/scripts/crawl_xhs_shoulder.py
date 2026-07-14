from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


SEARCHES = {
    "general": ["肩颈热敷", "颈椎热敷", "肩颈热敷仪", "肩颈加热垫"],
    "usage": ["肩颈热敷使用", "办公室肩颈热敷", "睡前颈椎热敷", "热敷颈枕怎么用"],
    "recommendation": ["肩颈热敷推荐", "颈椎热敷推荐", "肩颈热敷测评", "热敷颈枕测评"],
    "complaint": ["肩颈热敷智商税", "肩颈热敷不好用", "热敷垫烫伤", "肩颈热敷避坑"],
}

INCLUDE = re.compile(r"肩颈|颈椎|颈肩|脖子|热敷|加热|低头族|肩膀|肩部", re.I)
SHOULDER_TERMS = re.compile(r"肩颈|颈椎|颈肩|脖子|低头族|肩膀|肩部", re.I)
EXCLUDE = re.compile(r"TENS|电刺激|红外灯|理疗灯|烤灯", re.I)
MOVEMENT_ONLY = re.compile(r"瑜伽|八段锦|按摩手法|穴位|训练动作|颈椎操|拉伸", re.I)
HEAT_TERMS = re.compile(r"热敷|加热|发热|暖颈|热疗", re.I)
COMPLAINT_TERMS = re.compile(r"离谱|越敷越疼|烫|智商税|骗|受不了|慎用|警告|副作用|不好用|注意", re.I)


def number(value: Any) -> int:
    try:
        return int(str(value or "0").replace(",", ""))
    except ValueError:
        return 0


def engagement(note: dict[str, Any]) -> int:
    return (
        number(note.get("liked_count"))
        + number(note.get("collected_count"))
        + number(note.get("comment_count")) * 2
    )


def call_api(
    python: str,
    tool: str,
    method: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="xhs-shoulder-") as temp_dir:
        params_file = Path(temp_dir) / "params.json"
        output_file = Path(temp_dir) / "output.json"
        params_file.write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")
        subprocess.run(
            [
                python,
                tool,
                "call",
                "pc",
                method,
                "--params-file",
                str(params_file),
                "--out",
                str(output_file),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            timeout=60,
        )
        return json.loads(output_file.read_text(encoding="utf-8"))


def payload(response: dict[str, Any]) -> Any:
    result = response.get("result") or []
    if len(result) < 3 or result[0] is not True:
        message = result[1] if len(result) > 1 else "未知错误"
        raise RuntimeError(f"小红书 API 请求失败: {message}")
    return result[2]


def parse_search_items(
    response: dict[str, Any],
    keyword: str,
    intent: str,
) -> list[dict[str, Any]]:
    result = payload(response)
    items = result.get("data", {}).get("items", []) if isinstance(result, dict) else []
    notes: list[dict[str, Any]] = []
    for item in items:
        note_id = str(item.get("id") or "").strip()
        card = item.get("note_card") or {}
        title = str(card.get("display_title") or "").strip()
        if not note_id or not title:
            continue
        interaction = card.get("interact_info") or {}
        user = card.get("user") or {}
        notes.append(
            {
                "note_id": note_id,
                "xsec_token": item.get("xsec_token") or "",
                "title": title,
                "type": card.get("type") or "",
                "user": user.get("nick_name") or "",
                "user_id": user.get("user_id") or "",
                "liked_count": interaction.get("liked_count") or "0",
                "comment_count": interaction.get("comment_count") or "0",
                "collected_count": interaction.get("collected_count") or "0",
                "category": "肩颈热敷",
                "search_keyword": keyword,
                "intent": intent,
                "note_url": f"https://www.xiaohongshu.com/explore/{note_id}",
            }
        )
    return notes


def merge_notes(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for note in results:
        note_id = note["note_id"]
        current = merged.get(note_id)
        if current is None:
            note["search_keywords"] = [note["search_keyword"]]
            note["intents"] = [note["intent"]]
            merged[note_id] = note
            continue
        if note["search_keyword"] not in current["search_keywords"]:
            current["search_keywords"].append(note["search_keyword"])
        if note["intent"] not in current["intents"]:
            current["intents"].append(note["intent"])
        if engagement(note) > engagement(current):
            current.update(
                {
                    key: value
                    for key, value in note.items()
                    if key not in {"search_keyword", "intent"}
                }
            )
    return list(merged.values())


def relevant(note: dict[str, Any]) -> bool:
    title = note["title"]
    if not INCLUDE.search(title) or EXCLUDE.search(title):
        return False
    if not SHOULDER_TERMS.search(title) and not any(
        SHOULDER_TERMS.search(keyword)
        for keyword in note.get("search_keywords", [])
    ):
        return False
    if MOVEMENT_ONLY.search(title) and not HEAT_TERMS.search(title):
        return False
    if HEAT_TERMS.search(title):
        return True
    product_hint = re.search(r"好物|神器|暖|发热|颈枕|颈贴|肩颈带", title, re.I)
    return bool(product_hint and len(note.get("search_keywords", [])) >= 2)


def select_balanced(notes: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ranked = sorted((note for note in notes if relevant(note)), key=engagement, reverse=True)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    per_intent = max(1, limit // len(SEARCHES))
    for intent in SEARCHES:
        candidates = [note for note in ranked if intent in note.get("intents", [])]
        if intent == "complaint":
            candidates.sort(
                key=lambda note: (bool(COMPLAINT_TERMS.search(note["title"])), engagement(note)),
                reverse=True,
            )
        added = 0
        for note in candidates:
            if note["note_id"] not in selected_ids:
                selected.append(note)
                selected_ids.add(note["note_id"])
                added += 1
            if added >= per_intent:
                break
    for note in ranked:
        if len(selected) >= limit:
            break
        if note["note_id"] not in selected_ids:
            selected.append(note)
            selected_ids.add(note["note_id"])
    return selected[:limit]


def comment_list(response: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload(response)
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        data = result.get("data") or {}
        return data.get("comments") or result.get("comments") or []
    return []


def run(args: argparse.Namespace) -> None:
    a1 = os.environ.get("XHS_A1", "").strip()
    session = os.environ.get("XHS_SESSION", "").strip()
    if not a1 or not session:
        raise RuntimeError("请通过 XHS_A1 和 XHS_SESSION 环境变量提供本次临时会话")
    cookies = f"a1={a1}; web_session={session}"

    all_results: list[dict[str, Any]] = []
    raw_searches: list[dict[str, Any]] = []
    for intent, keywords in SEARCHES.items():
        for keyword in keywords:
            response = call_api(
                args.python,
                args.tool,
                "search_note",
                {
                    "query": keyword,
                    "cookies_str": cookies,
                    "page": 1,
                    "sort_type_choice": 2,
                },
            )
            notes = parse_search_items(response, keyword, intent)
            all_results.extend(notes)
            raw_searches.append({"keyword": keyword, "intent": intent, "response": response})
            print(f"{intent:14} {keyword}: {len(notes)}")
            time.sleep(args.delay)

    merged = merge_notes(all_results)
    selected = select_balanced(merged, args.note_limit)
    if len(selected) < args.note_limit:
        raise RuntimeError(f"相关笔记不足：仅筛出 {len(selected)} 条")

    comment_targets: list[dict[str, Any]] = []
    used_intents: set[str] = set()
    for note in selected:
        intent = next((value for value in note.get("intents", []) if value not in used_intents), None)
        if intent and note.get("xsec_token"):
            comment_targets.append(note)
            used_intents.add(intent)
        if len(comment_targets) >= args.comment_notes:
            break

    raw_comments: list[dict[str, Any]] = []
    cleaned_comments: list[dict[str, Any]] = []
    for note in comment_targets:
        query = urlencode({"xsec_token": note["xsec_token"], "xsec_source": "pc_search"})
        response = call_api(
            args.python,
            args.tool,
            "get_note_all_comment",
            {"url": f"{note['note_url']}?{query}", "cookies_str": cookies},
        )
        comments = comment_list(response)
        raw_comments.append(
            {
                "note_id": note["note_id"],
                "title": note["title"],
                "note_url": note["note_url"],
                "response": response,
            }
        )
        cleaned_comments.append(
            {
                "note_id": note["note_id"],
                "title": note["title"],
                "note_url": note["note_url"],
                "comments": comments,
            }
        )
        print(f"comments       {note['title'][:30]}: {len(comments)}")
        time.sleep(args.delay)

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.cleaned_dir.mkdir(parents=True, exist_ok=True)
    (args.raw_dir / "20a_xhs_shoulder_searches.json").write_text(
        json.dumps(raw_searches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.raw_dir / "20b_xhs_shoulder_comments.json").write_text(
        json.dumps(raw_comments, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.cleaned_dir / "20a_xhs_shoulder_notes_cleaned.json").write_text(
        json.dumps(selected, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.cleaned_dir / "20b_xhs_shoulder_comments_cleaned.json").write_text(
        json.dumps(cleaned_comments, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"完成：搜索去重 {len(merged)} 条，精选 {len(selected)} 条，评论来源 {len(cleaned_comments)} 篇")


def main() -> None:
    parser = argparse.ArgumentParser(description="采集小红书肩颈热敷搜索与评论")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--cleaned-dir", type=Path, default=Path("data/cleaned"))
    parser.add_argument("--note-limit", type=int, default=10)
    parser.add_argument("--comment-notes", type=int, default=4)
    parser.add_argument("--delay", type=float, default=2.5)
    parser.add_argument(
        "--python",
        default=os.environ.get("XHS_API_PYTHON", sys.executable),
    )
    parser.add_argument(
        "--tool",
        default=os.environ.get("XHS_API_TOOL", "xhs_api_tool.py"),
    )
    run(parser.parse_args())


if __name__ == "__main__":
    main()
