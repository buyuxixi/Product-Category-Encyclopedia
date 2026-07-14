#!/usr/bin/env python3
"""Reddit 爬取器 — 双通道：OAuth API（优先） + RSS fallback。

策略:
  Channel 1: Reddit OAuth API (via PRAW, needs REDDIT_CLIENT_ID/SECRET)
    - 能获取真实点赞/评论数
    - 不受 IP 封锁影响
  Channel 2: RSS search feed (fallback, no auth needed)
    - 可能被 429/403 限流
    - 指标有限

  如果 OAuth 未配置或失败，自动降级到 RSS。
  如果 RSS 也被限流，跳过并记录。

Usage:
    # 设置 OAuth (只需一次)
    export REDDIT_CLIENT_ID=your_client_id
    export REDDIT_CLIENT_SECRET=your_client_secret
    export REDDIT_USER_AGENT=encyclopedia_crawler/1.0

    python crawl_reddit.py           # 爬取全品类
    python crawl_reddit.py --json    # 输出 JSON
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus

import httpx

# 品类 → Subreddit + 关键词
REDDIT_SOURCES: dict[str, list[dict]] = {
    "TENS_THERAPY": [
        {"subreddit": "ChronicPain", "keyword": "TENS"},
        {"subreddit": "Fibromyalgia", "keyword": "TENS"},
        {"subreddit": "physicaltherapy", "keyword": "TENS unit"},
    ],
    "HEAT_THERAPY": [
        {"subreddit": "ChronicPain", "keyword": "heating pad"},
        {"subreddit": "ChronicPain", "keyword": "heat therapy"},
    ],
    "SHOULDER_NECK_HEAT_THERAPY": [
        {"subreddit": "ChronicPain", "keyword": "neck pain"},
        {"subreddit": "neckpain", "keyword": "heating pad"},
    ],
    "FAR_INFRARED": [
        {"subreddit": "ChronicPain", "keyword": "infrared"},
        {"subreddit": "PainManagement", "keyword": "infrared therapy"},
    ],
    "NIGHT_LIGHT": [
        {"subreddit": "sleep", "keyword": "night light"},
        {"subreddit": "NewParents", "keyword": "night light"},
    ],
    "MEDICATION_MANAGEMENT": [
        {"subreddit": "ChronicPain", "keyword": "pill organizer"},
        {"subreddit": "Health", "keyword": "pill box"},
    ],
    "SEAT_CUSHION": [
        {"subreddit": "Ergonomics", "keyword": "seat cushion"},
        {"subreddit": "backpain", "keyword": "cushion"},
    ],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/rss+xml,application/xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# 本地代理（系统配的 Clash/V2Ray），httpx 默认不走系统代理所以需要显式设置
LOCAL_PROXY = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or "http://127.0.0.1:7897"

BACKOFF_BASE = 3.0
MAX_RETRIES = 2
MAX_AGE_DAYS = 90

# 请求间隔：Reddit 限流严格，至少 40 秒
REQUEST_INTERVAL = 40

# OAuth credentials from env
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "python:encyclopedia_crawler:1.0 (by /u/encyclopedia_dev)")


def _try_oauth_api(sub: str, kw: str) -> list[dict] | None:
    """使用 Reddit OAuth API 搜索帖文。需要 PRAW 和 OAuth credentials。
    
    Returns:
        list[dict]: 帖文列表 (成功)
        None: 未配置或失败 (降级到 RSS)
    """
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return None  # OAuth 未配置

    try:
        import praw
    except ImportError:
        return None  # PRAW 未安装

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
        reddit.read_only = True

        subreddit = reddit.subreddit(sub)
        posts = []
        for submission in subreddit.search(kw, sort="new", time_filter="month", limit=5):
            days_ago = (datetime.now(timezone.utc) - datetime.fromtimestamp(
                submission.created_utc, tz=timezone.utc
            )).days
            if days_ago > MAX_AGE_DAYS:
                continue

            posts.append({
                "title": submission.title,
                "permalink": f"https://www.reddit.com{submission.permalink}",
                "num_comments": submission.num_comments,
                "ups": submission.ups,
                "score": submission.score,
                "desc": submission.selftext[:300] if submission.selftext else "",
                "days_ago": days_ago,
            })
        return posts
    except Exception as e:
        print(f"  [WARN] Reddit OAuth r/{sub}?q={kw} failed: {e}", file=sys.stderr)
        return None


def _try_rss_search(sub: str, kw: str, retry: int = 0) -> list[dict]:
    """通过 RSS search feed 获取搜索结果。restrict_sr=on 限定在 subreddit 内搜索。

    使用 subprocess 调用 curl 获取 RSS 内容，绕过 httpx TLS 指纹被 Reddit 识别的问题。
    """
    # restrict_sr=on: 限制搜索范围在当前 subreddit 内（否则返回全站随机热帖）
    # sort=relevance: 按相关性排序（比 new 更能匹配关键词）
    # t=year: 搜索过去一年的帖文（扩大范围，评分阶段再过滤 90 天）
    rss_url = f"https://old.reddit.com/r/{sub}/search.rss?q={quote_plus(kw)}&sort=relevance&limit=5&t=year&restrict_sr=on"

    try:
        # 用 curl 代替 httpx — Reddit 对 httpx 的 TLS 指纹返回 403，但 curl 能通过
        import subprocess as sp
        result = sp.run(
            [
                "curl", "-s", "-L", "-m", "15", "--proxy", LOCAL_PROXY,
                "-H", f"User-Agent: {HEADERS['User-Agent']}",
                "-H", f"Accept: {HEADERS['Accept']}",
                "-H", f"Accept-Language: {HEADERS['Accept-Language']}",
                "-w", "\n%{http_code}",  # 最后输出 HTTP 状态码
                rss_url,
            ],
            capture_output=True, text=True, timeout=20,
        )
        # 最后一行是 HTTP 状态码
        lines = result.stdout.rsplit("\n", 1)
        if len(lines) == 2:
            body, status_str = lines
        else:
            body, status_str = result.stdout, "0"
        try:
            status_code = int(status_str.strip())
        except ValueError:
            status_code = 0

        if status_code == 429:
            if retry < MAX_RETRIES:
                # 429 限流：等 30 秒再重试（Reddit 限流恢复较慢）
                wait = 30 if retry == 0 else 60
                print(f"  [429] Reddit r/{sub}?q={kw} rate-limited, waiting {wait}s (retry {retry+1}/{MAX_RETRIES})", file=sys.stderr)
                time.sleep(wait)
                return _try_rss_search(sub, kw, retry + 1)
            print(f"  [SKIP] Reddit r/{sub}?q={kw} rate-limited after {MAX_RETRIES} retries", file=sys.stderr)
            return []
        if status_code == 403:
            print(f"  [SKIP] Reddit r/{sub}?q={kw} blocked (403)", file=sys.stderr)
            return []
        if status_code == 404:
            return []
        if status_code != 200:
            print(f"  [SKIP] Reddit r/{sub}?q={kw} HTTP {status_code}", file=sys.stderr)
            return []

        import feedparser
        feed = feedparser.parse(body)
        entries = []
        for entry in feed.entries[:5]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            desc_raw = entry.get("summary", "") or entry.get("description", "")
            desc = re.sub(r'<[^>]+>', '', desc_raw).strip()[:300]

            # 关键词相关性检查：标题或描述中必须包含关键词词根
            kw_words = [w.lower() for w in kw.split() if len(w) > 2]
            title_lower = title.lower()
            desc_lower = desc.lower()
            if not any(w in title_lower or w in desc_lower for w in kw_words):
                continue  # 跳过不相关的帖文

            published = entry.get("published_parsed") or entry.get("updated_parsed")
            days_ago = None
            if published:
                try:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    days_ago = (datetime.now(timezone.utc) - pub_dt).days
                except Exception:
                    pass

            if title and link:
                entries.append({
                    "title": title,
                    "permalink": link,
                    "num_comments": 0,  # RSS doesn't provide comment count
                    "ups": 0,
                    "score": 0,
                    "desc": desc,
                    "days_ago": days_ago,
                })
        return entries
    except Exception as e:
        if retry < MAX_RETRIES:
            time.sleep(30)
            return _try_rss_search(sub, kw, retry + 1)
        print(f"  [SKIP] Reddit r/{sub}?q={kw} failed: {e}", file=sys.stderr)
        return []


def _score_post(comments: int, ups: int, days_ago: int | None) -> tuple[float, bool]:
    """计算帖文热度分。"""
    score = 0.0
    # 社交互动
    score += min(comments * 2, 15)
    score += min(ups / 10, 15)
    # 新鲜度
    if days_ago is None:
        score += 5
    elif days_ago <= 7:
        score += 20
    elif days_ago <= 30:
        score += 12
    elif days_ago <= 90:
        score += 6
    else:
        return -1, False  # 超过 90 天跳过
    # Reddit 平台权威性
    score += 7
    return round(score, 2), score >= 20


def crawl_reddit(category_code: str, sources: list[dict]) -> dict:
    """爬取 Reddit 搜索结果，返回 hot_links 和 trend_signals。"""
    hot_links: list[dict] = []
    trend_signals: list[dict] = []

    use_oauth = bool(REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET)
    if use_oauth:
        print(f"  Using Reddit OAuth API (client_id configured)", file=sys.stderr)
    else:
        print(f"  Reddit OAuth not configured, using RSS fallback (may be rate-limited)", file=sys.stderr)

    for source in sources:
        sub = source["subreddit"]
        kw = source["keyword"]

        posts = None
        if use_oauth:
            posts = _try_oauth_api(sub, kw)

        if posts is None:
            posts = _try_rss_search(sub, kw)

        if not posts:
            time.sleep(BACKOFF_BASE)
            continue

        total_comments = 0
        total_ups = 0
        valid_posts = 0

        for post in posts:
            comments = post.get("num_comments", 0)
            ups = post.get("ups", 0)
            permalink = post.get("permalink", "")
            post_title = post.get("title", "")
            post_desc = post.get("desc", "")
            days_ago = post.get("days_ago")

            score, is_hot = _score_post(comments, ups, days_ago)
            if score < 0:
                continue

            total_comments += comments
            total_ups += ups
            valid_posts += 1

            hot_links.append({
                "category_code": category_code,
                "section_key": "users",  # Reddit 讨论帖关联到用户画像章节
                "link_type": "discussion",
                "platform": "reddit",
                "title": post_title[:500],
                "url": permalink,
                "description": f"r/{sub} · {post_desc[:200]}" if post_desc else f"r/{sub} · {comments} comments · {ups} upvotes",
                "hotness_score": score,
                "is_hot": is_hot,
            })

        if valid_posts > 0:
            trend_signals.append({
                "category_code": category_code,
                "section_key": "market",
                "signal_type": "social_mention",
                "platform": "reddit",
                "keyword": kw,
                "title": f"Reddit r/{sub}: {kw}",
                "metric_value": float(total_comments + total_ups),
                "metric_unit": "interactions",
                "trend_direction": "up" if (total_comments + total_ups) > 30 else "stable",
                "summary": f"r/{sub} 过去月内: {valid_posts} 帖, 总互动 {total_comments + total_ups}",
            })

        # RSS 模式：6 秒间隔避免 429；OAuth 模式：2 秒
        time.sleep(2 if use_oauth else 6)

    return {"hot_links": hot_links, "trend_signals": trend_signals}


def crawl_all() -> dict:
    """Crawl all categories, return merged result."""
    all_hot_links: list[dict] = []
    all_trend_signals: list[dict] = []
    for cat, sources in REDDIT_SOURCES.items():
        result = crawl_reddit(cat, sources)
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
