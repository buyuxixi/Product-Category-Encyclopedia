from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Category, HotLink, TrendSignal


@dataclass(frozen=True)
class CategorySource:
    code: str
    notes_file: str
    comments_file: str
    comment_format: str
    include: re.Pattern[str]
    exclude: re.Pattern[str] | None = None
    comment_include: re.Pattern[str] | None = None


SOURCES = [
    CategorySource(
        "TENS_THERAPY",
        "19b_xhs_tens_notes_index_cleaned.json",
        "19c_xhs_tens_viral_note_comments_cleaned.json",
        "api",
        re.compile(r"TENS|电刺激|脉冲|理疗仪|电疗", re.I),
        comment_include=re.compile(r"档|电|痛|麻|敏感|强度|效果", re.I),
    ),
    CategorySource(
        "FAR_INFRARED",
        "19d_xhs_ir_notes_index_cleaned.json",
        "19e_xhs_ir_comments_cleaned.json",
        "grouped",
        re.compile(r"红外|理疗灯|烤灯|红光|神灯", re.I),
        comment_include=re.compile(r"怎么选|哪个|区别|效果|疼|痛|热|烫|远红外|近红外|电磁|安全", re.I),
    ),
    CategorySource(
        "NIGHT_LIGHT",
        "19f_xhs_nightlight_notes_index_cleaned.json",
        "19g_xhs_nightlight_comments_cleaned.json",
        "api",
        re.compile(r"夜灯|起夜|感应灯|床头灯|棒灯|星空灯|智能灯|灯带", re.I),
        re.compile(r"监控|皮肤|3D打印", re.I),
    ),
    CategorySource(
        "MEDICATION_MANAGEMENT",
        "19h_xhs_pill_notes_index_cleaned.json",
        "19i_xhs_pill_comments_cleaned.json",
        "api",
        re.compile(r"药盒|切药|分药|吃药|服药|药片|药丸", re.I),
        re.compile(r"耳钉|首饰|收纳|草莓|手办|串珠|文具|创业计划书|Word|PPT|痛盒|中古|便当盒", re.I),
        re.compile(r"抠|保质期|放不了|药|大|小|切|提醒|老人|携带", re.I),
    ),
    CategorySource(
        "SEAT_CUSHION",
        "19j_xhs_cushion_notes_index_cleaned.json",
        "19k_xhs_cushion_comments_cleaned.json",
        "grouped",
        re.compile(r"坐垫|座垫|屁垫|尾骨|护腰垫", re.I),
        comment_include=re.compile(r"塌|软|硬|厚|价格|涨价|腰|坐|滑|透气|清洗", re.I),
    ),
    CategorySource(
        "SHOULDER_NECK_HEAT_THERAPY",
        "20a_xhs_shoulder_notes_cleaned.json",
        "20b_xhs_shoulder_comments_cleaned.json",
        "grouped",
        re.compile(r"肩颈|颈椎|颈肩|脖子|热敷|加热|暖颈|颈贴", re.I),
        re.compile(r"TENS|电刺激|红外灯|理疗灯|烤灯", re.I),
        re.compile(r"热|烫|温度|充电|插电|电压|效果|尺寸|紧|松|味道|材质|不舒服|推荐|好用|没用", re.I),
    ),
]


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


def select_notes(notes: list[dict[str, Any]], source: CategorySource, limit: int) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for note in notes:
        note_id = str(note.get("note_id") or "").strip()
        title = str(note.get("title") or "").strip()
        url = str(note.get("note_url") or "").strip()
        if not note_id or not title or not url.startswith("https://www.xiaohongshu.com/explore/"):
            continue
        if not source.include.search(title):
            continue
        if source.exclude and source.exclude.search(title):
            continue
        if (
            source.code == "MEDICATION_MANAGEMENT"
            and str(note.get("search_keyword") or "").strip() == "药盒"
            and not re.search(r"吃药|服药|切药|分药|药片|老人|便携|智能|提醒|辅助器", title)
        ):
            continue
        previous = unique.get(note_id)
        if previous is None or engagement(note) > engagement(previous):
            unique[note_id] = note
    return sorted(unique.values(), key=lambda item: (engagement(item), number(item.get("liked_count"))), reverse=True)[:limit]


def load_comments(path: Path, comment_format: str) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if comment_format == "api":
        if not isinstance(data, dict):
            return []
        result = data.get("result") or []
        return result[2] if len(result) > 2 and isinstance(result[2], list) else []

    comments: list[dict[str, Any]] = []
    for group in data if isinstance(data, list) else []:
        note_id = group.get("note_id")
        title = group.get("title")
        for comment in group.get("comments") or []:
            comments.append({**comment, "_note_id": note_id, "_note_title": title})
    return comments


def select_comments(
    comments: list[dict[str, Any]],
    notes_by_id: dict[str, dict[str, Any]],
    source: CategorySource,
    limit: int,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen: set[str] = set()
    for comment in comments:
        note_id = str(comment.get("note_id") or comment.get("_note_id") or "").strip()
        note = notes_by_id.get(note_id)
        content = re.sub(r"\s+", " ", str(comment.get("content") or "")).strip()
        likes = number(comment.get("like_count"))
        if note is None or len(content) < 6 or likes <= 0 or content in seen:
            continue
        if source.comment_include and not source.comment_include.search(content):
            continue
        seen.add(content)
        candidates.append((comment, note))
    candidates.sort(
        key=lambda item: (number(item[0].get("like_count")), len(str(item[0].get("content") or ""))),
        reverse=True,
    )
    return candidates[:limit]


def hot_link_from_note(note: dict[str, Any], category_id: int) -> HotLink:
    likes = number(note.get("liked_count"))
    comments = number(note.get("comment_count"))
    collections = number(note.get("collected_count"))
    author = str(note.get("user") or "未知作者").strip()
    keyword = str(note.get("search_keyword") or "").strip()
    title = str(note["title"]).strip()
    description = f"[{author}] | ❤ {likes} | 💬 {comments} | ⭐ {collections} | 搜索词: {keyword}"
    return HotLink(
        category_id=category_id,
        section_key="market",
        link_type="social_post",
        platform="xiaohongshu",
        title=title,
        title_zh=title,
        url=str(note["note_url"]).strip(),
        description=description,
        description_zh=description,
        hotness_score=likes,
        is_hot=likes >= 1000,
    )


def trend_signal_from_comment(
    comment: dict[str, Any],
    note: dict[str, Any],
    category_id: int,
) -> TrendSignal:
    content = re.sub(r"\s+", " ", str(comment.get("content") or "")).strip()
    likes = number(comment.get("like_count"))
    note_title = str(note.get("title") or "").strip()
    note_url = str(note.get("note_url") or "").strip()
    positive_review = bool(re.search(r"好用|推荐|同款|舒服|有效", content))
    pain_signal = bool(re.search(r"疼|痛|烫|过敏|不好|没用|吐槽|难受|太紧|太松", content))
    summary = f"小红书笔记《{note_title}》热评（{likes}赞）：{content}。原文链接: {note_url}"
    return TrendSignal(
        category_id=category_id,
        section_key="market",
        signal_type="review_sentiment" if positive_review and not pain_signal else "user_pain_point",
        platform="xiaohongshu",
        keyword=str(note.get("search_keyword") or "").strip(),
        title=content[:500],
        title_zh=content[:500],
        metric_value=likes,
        metric_unit="likes",
        trend_direction="positive" if positive_review and not pain_signal else ("up" if likes >= 10 else "stable"),
        summary=summary,
        summary_zh=summary,
    )


def run(data_dir: Path, note_limit: int, comment_limit: int, apply: bool) -> None:
    with SessionLocal() as db:
        categories = {
            category.code: category
            for category in db.scalars(
                select(Category).where(Category.code.in_([source.code for source in SOURCES]))
            )
        }
        missing = [source.code for source in SOURCES if source.code not in categories]
        if missing:
            raise RuntimeError(f"数据库缺少品类: {', '.join(missing)}")

        existing_urls = set(db.scalars(select(HotLink.url)).all())
        existing_signal_titles = set(
            db.scalars(
                select(TrendSignal.title).where(TrendSignal.platform == "xiaohongshu")
            ).all()
        )
        existing_signal_summaries = db.scalars(
            select(TrendSignal.summary).where(TrendSignal.platform == "xiaohongshu")
        ).all()
        existing_signal_urls = {
            match.group(0).rstrip("。")
            for summary in existing_signal_summaries
            for match in re.finditer(r"https://www\.xiaohongshu\.com/explore/[0-9a-f]+", summary or "")
        }

        pending_links: list[HotLink] = []
        pending_signals: list[TrendSignal] = []
        for source in SOURCES:
            notes_path = data_dir / source.notes_file
            comments_path = data_dir / source.comments_file
            notes = json.loads(notes_path.read_text(encoding="utf-8"))
            selected = select_notes(notes, source, note_limit)
            notes_by_id = {
                str(note["note_id"]): note
                for note in notes
                if note.get("note_id")
                and str(note.get("note_url") or "").startswith("https://www.xiaohongshu.com/explore/")
            }
            selected_comments = select_comments(
                load_comments(comments_path, source.comment_format),
                notes_by_id,
                source,
                comment_limit,
            )

            new_links = [
                hot_link_from_note(note, categories[source.code].id)
                for note in selected
                if note["note_url"] not in existing_urls
            ]
            new_signals = [
                trend_signal_from_comment(comment, note, categories[source.code].id)
                for comment, note in selected_comments
                if comment.get("content") not in existing_signal_titles
                and note["note_url"] not in existing_signal_urls
            ]
            pending_links.extend(new_links)
            pending_signals.extend(new_signals)

            print(f"\n{source.code}: 选中笔记 {len(selected)}，新增 {len(new_links)}，评论信号新增 {len(new_signals)}")
            for note in selected:
                status = "SKIP 已存在" if note["note_url"] in existing_urls else "ADD"
                print(
                    f"  [{status}] ❤{number(note.get('liked_count')):>6} "
                    f"{str(note['title'])[:42]} | {note['note_url']}"
                )
            for signal in new_signals:
                print(f"  [ADD SIGNAL] ❤{int(signal.metric_value or 0):>4} {signal.title[:60]}")

        print(f"\n汇总：待新增 hot_links={len(pending_links)}，trend_signals={len(pending_signals)}")
        if not apply:
            print("Dry run：未写入数据库。使用 --apply 执行事务导入。")
            return

        db.add_all([*pending_links, *pending_signals])
        db.commit()
        print("导入完成：仅新增记录，未更新或删除已有数据。")


def main() -> None:
    parser = argparse.ArgumentParser(description="增量导入 data/cleaned 中的小红书数据")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--note-limit", type=int, default=10)
    parser.add_argument("--comment-limit", type=int, default=2)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run(args.data_dir, args.note_limit, args.comment_limit, args.apply)


if __name__ == "__main__":
    main()
