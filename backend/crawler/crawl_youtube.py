#!/usr/bin/env python3
"""YouTube 爬取器 — 无需 API Key，只爬最近 3 个月的视频。

策略：
- 只搜索"YouTube 本年度"结果（sp=EgIIBA&hl=en）
- 硬过滤：超过 3 个月的视频直接跳过
- 评分：新鲜度(50%) + 播放量(30%) + 频道权威(20%)

业务逻辑：跨境电商需要捕捉最新热点和新兴趋势，
老教程视频对业务没有参考价值，直接剔除。

Usage:
    python crawl_youtube.py           # 爬取全品类
    python crawl_youtube.py --json    # 输出 JSON
"""
from __future__ import annotations

import json
import re
import sys
import time
from urllib.parse import quote_plus

import httpx

# 品类 → 搜索关键词
YOUTUBE_KEYWORDS: dict[str, list[str]] = {
    "TENS_THERAPY": ["TENS unit review", "TENS unit placement guide"],
    "HEAT_THERAPY": ["heating pad review", "infrared heating pad"],
    "SHOULDER_NECK_HEAT_THERAPY": ["neck heating pad review", "shoulder heating pad"],
    "FAR_INFRARED": ["far infrared heating pad review", "infrared sauna blanket"],
    "NIGHT_LIGHT": ["best night light review", "motion sensor night light"],
    "MEDICATION_MANAGEMENT": ["pill organizer review", "smart pill dispenser"],
    "SEAT_CUSHION": ["best seat cushion review", "tailbone cushion"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# 硬过滤：超过此天数的视频直接跳过
MAX_AGE_DAYS = 90  # 3 个月

# 知名频道关键词
AUTHORITY_CHANNELS = [
    "linus", "cnet", "wirecutter", "consumer", "tech", "review",
    "vsauce", "mark rober", "doctor", "physio", "medical", "health",
    "bob & brad", "askdoctorjo", "squat university", "gearpatrol",
    "popular mechanics", "popular science", "rtings", "dr todd",
]


def _parse_views(view_text: str) -> int:
    """解析播放量文本，如 '2,651,618 次观看' → 2651618"""
    return int(re.sub(r"[^0-9]", "", view_text) or 0)


def _parse_age_days(published_text: str) -> int | None:
    """解析发布时间文本，返回天数。超过 3 个月返回 None（跳过）。"""
    if not published_text:
        return None

    text = published_text.lower()
    try:
        num = int(re.search(r"(\d+)", text).group(1))
    except Exception:
        return None

    if "hour" in text:
        days = 0
    elif "day" in text:
        days = num
    elif "week" in text:
        days = num * 7
    elif "month" in text:
        days = num * 30
    elif "year" in text:
        return None  # 超过 3 个月，跳过
    else:
        return None

    if days > MAX_AGE_DAYS:
        return None
    return days


def _score_video(views: int, days_ago: int, channel: str) -> tuple[float, bool]:
    """评分：新鲜度(50%) + 播放量(30%) + 频道权威(20%)。

    新鲜度最高 25 分（3个月内有效）：
      < 7天 = 25, < 30天 = 20, < 60天 = 12, < 90天 = 6

    播放量最高 15 分：
      > 100K = 15, > 10K = 10, > 1K = 5, < 1K = 1

    频道权威最高 10 分：
      知名测评频道 = 10, 其他 = 3
    """
    # 新鲜度
    if days_ago <= 7:
        freshness = 25
    elif days_ago <= 30:
        freshness = 20
    elif days_ago <= 60:
        freshness = 12
    else:
        freshness = 6

    # 播放量
    if views >= 100_000:
        view_score = 15
    elif views >= 10_000:
        view_score = 10
    elif views >= 1_000:
        view_score = 5
    else:
        view_score = 1

    # 频道权威
    channel_lower = channel.lower()
    if any(name in channel_lower for name in AUTHORITY_CHANNELS):
        authority = 10
    else:
        authority = 3

    score = freshness + view_score + authority
    return round(float(score), 2), score >= 15


def _is_relevant(title: str, keyword: str) -> bool:
    """检查视频标题是否与搜索关键词相关，过滤无关内容（如动漫、游戏视频）。
    标题中必须包含关键词的核心词根。
    """
    title_lower = title.lower()
    keyword_lower = keyword.lower()
    # 将关键词拆分成词根
    words = [w for w in keyword_lower.replace("review", "").replace("best", "").split() if len(w) > 2]
    # 标题中至少包含 1 个关键词词根
    return any(w in title_lower for w in words)


def _search_youtube_recent(keyword: str, max_results: int = 10) -> list[dict]:
    """搜索 YouTube 本年度视频。sp=EgIIBA 过滤为本年度。"""
    # sp=EgIIBA = This year filter, hl=en 强制英文
    url = f"https://www.youtube.com/results?search_query={quote_plus(keyword)}&sp=EgIIBA&hl=en"

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [WARN] YouTube search '{keyword}' failed: {e}", file=sys.stderr)
        return []

    match = re.search(r"ytInitialData\s*=\s*(\{.+?})\s*;?\s*</script>", resp.text, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    videos = []
    contents = (
        data.get("contents", {})
        .get("twoColumnSearchResultsRenderer", {})
        .get("primaryContents", {})
        .get("sectionListRenderer", {})
        .get("contents", [])
    )

    for section in contents:
        items = section.get("itemSectionRenderer", {}).get("contents", [])
        for item in items:
            video = item.get("videoRenderer", {})
            if not video:
                continue

            video_id = video.get("videoId", "")
            title = video.get("title", {}).get("runs", [{}])[0].get("text", "")
            if not video_id or not title:
                continue

            # 标题相关性过滤：跳过无关内容（如动漫、游戏）
            if not _is_relevant(title, keyword):
                continue

            published = video.get("publishedTimeText", {}).get("simpleText", "")

            # 硬过滤：超过 3 个月的跳过
            days_ago = _parse_age_days(published)
            if days_ago is None:
                continue

            view_text = (
                video.get("viewCountText", {}).get("simpleText", "")
                or video.get("viewCountText", {}).get("runs", [{}])[0].get("text", "0")
            )
            views = _parse_views(view_text)

            # 硬过滤：播放量为 0 的视频跳过（无业务参考价值）
            if views == 0:
                continue

            channel = (
                video.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                or video.get("channelName", "")
            )

            desc = ""
            snippets = video.get("detailedMetadataSnippets", [])
            if snippets:
                desc = snippets[0].get("snippetText", {}).get("runs", [{}])[0].get("text", "")

            videos.append({
                "video_id": video_id,
                "title": title[:500],
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "views": views,
                "channel": channel,
                "published": published,
                "days_ago": days_ago,
                "description": desc[:300],
            })

            if len(videos) >= max_results:
                return videos

    return videos


def crawl_youtube(category_code: str, keywords: list[str]) -> dict:
    """爬取 YouTube 最近视频，硬过滤超过 3 个月的内容。"""
    hot_links: list[dict] = []
    trend_signals: list[dict] = []

    for keyword in keywords:
        videos = _search_youtube_recent(keyword, max_results=10)
        time.sleep(1)

        # 评分并排序
        scored = []
        for v in videos:
            score, is_hot = _score_video(v["views"], v["days_ago"], v["channel"])
            scored.append({**v, "score": score, "is_hot": is_hot})

        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[:5]  # 每个关键词取 top 5

        for idx, v in enumerate(top):
            # 跨章节分布: 第1个视频→technology, 第2个→users, 第3个→needs, 其余→market
            section_map = ["technology", "users", "needs", "market", "market"]
            section = section_map[idx] if idx < len(section_map) else "market"
            hot_links.append({
                "category_code": category_code,
                "section_key": section,
                "link_type": "video",
                "platform": "youtube",
                "title": v["title"],
                "url": v["url"],
                "description": f"[{v['channel']}] 👀 {v['views']:,} 次观看 · {v['published']}",
                "hotness_score": v["score"],
                "is_hot": v["is_hot"],
            })

        total_views = sum(v["views"] for v in top)
        trend_signals.append({
            "category_code": category_code,
            "section_key": "market",
            "signal_type": "social_mention",
            "platform": "youtube",
            "keyword": keyword,
            "title": f"YouTube: {keyword}",
            "metric_value": float(total_views),
            "metric_unit": "views",
            "trend_direction": "up" if total_views > 10000 else "stable",
            "summary": f"YouTube '{keyword}' (近3月): {len(top)} 个视频, 总播放 {total_views:,}",
        })

    return {"hot_links": hot_links, "trend_signals": trend_signals}


def crawl_all() -> dict:
    """Crawl all categories, return merged result."""
    all_hot_links: list[dict] = []
    all_trend_signals: list[dict] = []
    for cat, kws in YOUTUBE_KEYWORDS.items():
        result = crawl_youtube(cat, kws)
        all_hot_links.extend(result["hot_links"])
        all_trend_signals.extend(result["trend_signals"])
        hot_count = sum(1 for l in result["hot_links"] if l["is_hot"])
        print(f"  {cat}: {len(result['hot_links'])} hot_links ({hot_count} hot), {len(result['trend_signals'])} trend_signals")
    return {"hot_links": all_hot_links, "trend_signals": all_trend_signals}


if __name__ == "__main__":
    result = crawl_all()
    total_hl = len(result["hot_links"])
    total_ts = len(result["trend_signals"])
    print(f"\nTotal: {total_hl} hot_links, {total_ts} trend_signals")
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2, ensure_ascii=False))
