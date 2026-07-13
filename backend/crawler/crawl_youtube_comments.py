#!/usr/bin/env python3
"""YouTube 评论分析爬取器 — 从热门视频爬取评论，提取用户痛点和需求。

策略:
- 读取已入库的 hot_links 中 platform=youtube 的视频
- 用 YouTube oEmbed + ytInitialData 提取评论
- 分析评论中的高频词和情感倾向
- 生成 trend_signals (user_pain_points 类型)

数据推送到百科后端:
- trend_signals: 用户痛点关键词 + 频次

Usage:
    python crawl_youtube_comments.py              # 全品类
    python crawl_youtube_comments.py TENS_THERAPY  # 单品类
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, UTC
from urllib.parse import parse_qs, urlparse

import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# 用户痛点/需求关键词 — 用于从评论中提取有价值的信号
PAIN_POINT_KEYWORDS = [
    "pain", "hurt", "ache", "sore", "uncomfortable", "disappoint", "waste",
    "cheap", "broke", "broken", "defective", "return", "refund", "awful",
    "terrible", "worst", "flimsy", "falls apart", "doesn't work", "didn't work",
    "too hard", "too soft", "too small", "too big", "too expensive",
    "love", "amazing", "perfect", "great", "best", "recommend", "worth",
    "helped", "relief", "comfortable", "durable", "quality",
]

REQUEST_INTERVAL = 5  # 视频间隔


def extract_video_id(url: str) -> str | None:
    """从 YouTube URL 提取视频 ID"""
    m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def fetch_comments(video_id: str, client: httpx.Client) -> list[str]:
    """从 YouTube 视频页面提取评论 — 通过 continuation API"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        resp = client.get(url, headers=HEADERS)
        if resp.status_code != 200:
            return []

        html = resp.text

        # 提取 INNERTUBE_API_KEY
        api_key_match = re.search(r'"INNERTUBE_API_KEY":\s*"([^"]+)"', html)
        if not api_key_match:
            return []
        api_key = api_key_match.group(1)

        # 提取 continuation token (评论数据入口)
        # 找包含 "comment" 上下文的 token
        tokens_with_ctx = []
        for m in re.finditer(r'"token":\s*"([^"]+)"', html):
            ctx_before = html[max(0, m.start()-300):m.start()].lower()
            ctx_after = html[m.end():m.end()+300].lower()
            if 'comment' in ctx_before or 'comment' in ctx_after:
                tokens_with_ctx.append(m.group(1))

        if tokens_with_ctx:
            continuation_token = tokens_with_ctx[-1]  # 最后一个评论 token
        else:
            # 备用: 直接用第二个 token
            all_tokens = re.findall(r'"token":\s*"([^"]+)"', html)
            if len(all_tokens) >= 2:
                continuation_token = all_tokens[1]
            else:
                return []

        # 调用 YouTube innertube API 获取评论
        api_url = f"https://www.youtube.com/youtubei/v1/next?key={api_key}"
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240101.00.00",
                },
            },
            "continuation": continuation_token,
        }

        time.sleep(2)  # 礼貌延迟
        api_resp = client.post(api_url, json=payload, headers=HEADERS)
        if api_resp.status_code != 200:
            return []

        data = api_resp.json()
        comments = []

        # 递归提取评论文本
        def extract_text(obj):
            if isinstance(obj, dict):
                # 评论 content 在 "content" 字段中 (YouTube API 格式)
                if "content" in obj and isinstance(obj["content"], str):
                    text = obj["content"].strip()
                    if len(text) > 10:  # 过滤短文本
                        comments.append(text)
                # 也检查 runs 数组中的 text
                if "content" in obj and isinstance(obj["content"], dict):
                    runs = obj["content"].get("runs", [])
                    text = "".join(r.get("text", "") for r in runs)
                    if text.strip() and len(text.strip()) > 10:
                        comments.append(text.strip())
                for v in obj.values():
                    extract_text(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract_text(item)

        extract_text(data)
        return comments[:50]

    except Exception as e:
        print(f"    -> Error fetching comments: {e}")
        return []


def analyze_comments(comments: list[str]) -> dict:
    """分析评论，提取痛点关键词和情感倾向"""
    all_text = " ".join(comments).lower()

    # 统计痛点关键词
    found_pain_points = []
    for kw in PAIN_POINT_KEYWORDS:
        count = all_text.count(kw)
        if count > 0:
            found_pain_points.append({"keyword": kw, "count": count})

    found_pain_points.sort(key=lambda x: x["count"], reverse=True)

    # 情感分类
    positive_words = ["love", "amazing", "perfect", "great", "best", "recommend", "worth", "helped", "comfortable", "durable", "quality"]
    negative_words = ["pain", "hurt", "disappoint", "waste", "cheap", "broke", "broken", "defective", "return", "refund", "awful", "terrible", "worst", "flimsy"]

    pos_count = sum(all_text.count(w) for w in positive_words)
    neg_count = sum(all_text.count(w) for w in negative_words)

    if pos_count > neg_count * 2:
        sentiment = "positive"
    elif neg_count > pos_count * 2:
        sentiment = "negative"
    else:
        sentiment = "mixed"

    # 提取高频词（去除停用词）
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                  "have", "has", "had", "do", "does", "did", "will", "would", "could",
                  "should", "may", "might", "must", "shall", "can", "need", "ought",
                  "i", "me", "my", "we", "us", "our", "you", "your", "he", "she", "it",
                  "they", "them", "their", "this", "that", "these", "those", "and", "or",
                  "but", "not", "no", "so", "if", "then", "than", "too", "very", "just",
                  "for", "with", "about", "as", "in", "on", "at", "to", "of", "from", "by",
                  "it's", "its", "im", "dont", "cant", "wont", "didnt", "ive", "wasnt"}

    words = re.findall(r'\b[a-z]{3,}\b', all_text)
    filtered = [w for w in words if w not in stop_words]
    word_freq = Counter(filtered).most_common(20)

    return {
        "total_comments": len(comments),
        "sentiment": sentiment,
        "positive_count": pos_count,
        "negative_count": neg_count,
        "pain_points": found_pain_points[:10],
        "top_words": word_freq,
    }


def crawl_category_comments(category_code: str, hot_links: list[dict]) -> list[dict]:
    """爬取某个品类的 YouTube 视频评论"""
    results = []
    client = httpx.Client(timeout=30, follow_redirects=True, verify=False, proxy='http://127.0.0.1:7897')

    # 过滤该品类的 YouTube 视频
    yt_links = [l for l in hot_links if l.get("platform") == "youtube" and l.get("category_code") == category_code]
    print(f"  Found {len(yt_links)} YouTube videos for {category_code}")

    for i, link in enumerate(yt_links[:5]):  # 每品类最多爬 5 个视频
        video_id = extract_video_id(link["url"])
        if not video_id:
            continue

        print(f"  [{i+1}/{min(len(yt_links), 5)}] {link['title'][:50]}...")
        comments = fetch_comments(video_id, client)

        if comments:
            analysis = analyze_comments(comments)
            print(f"    -> {analysis['total_comments']} comments, sentiment: {analysis['sentiment']}")
            print(f"    -> Pain points: {[p['keyword'] for p in analysis['pain_points'][:5]]}")

            # 生成 trend_signal
            pain_summary = ", ".join([f"{p['keyword']}({p['count']})" for p in analysis['pain_points'][:5]])
            results.append({
                "category_code": category_code,
                "section_key": "users",
                "signal_type": "user_pain_point",
                "platform": "youtube",
                "keyword": link["title"][:50],
                "title": f"YouTube 评论分析: {link['title'][:50]}",
                "metric_value": analysis["total_comments"],
                "metric_unit": "comments",
                "trend_direction": analysis["sentiment"],
                "summary": f"情感:{analysis['sentiment']} | 痛点: {pain_summary} | 高频词: {[w[0] for w in analysis['top_words'][:5]]}",
                "collected_at": datetime.now(UTC).isoformat(),
            })
        else:
            print(f"    -> No comments found")

        time.sleep(REQUEST_INTERVAL)

    client.close()
    return results


def crawl_all(hot_links: list[dict]) -> list[dict]:
    """爬取所有品类的 YouTube 评论"""
    all_signals = []
    codes = list(set(l.get("category_code", "") for l in hot_links if l.get("platform") == "youtube"))

    for code in codes:
        if not code:
            continue
        print(f"=== {code} ===")
        signals = crawl_category_comments(code, hot_links)
        all_signals.extend(signals)
        time.sleep(3)

    return all_signals


if __name__ == "__main__":
    # 测试模式：直接用视频 URL 测试
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    vid = extract_video_id(test_url)
    if vid:
        client = httpx.Client(timeout=30, follow_redirects=True, verify=False)
        comments = fetch_comments(vid, client)
        print(f"Found {len(comments)} comments")
        if comments:
            analysis = analyze_comments(comments)
            print(json.dumps(analysis, indent=2, ensure_ascii=False))
        client.close()
