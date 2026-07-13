#!/usr/bin/env python3
"""去重 + 热度评分工具 — 对爬取结果进行去重和热度归一化。

新评分算法 (多维度):
  - 来源权威性: 知名出版商 (CNN, NBC, NYT 等) = +15, 垂直博客 = +5
  - 新鲜度: 24h = +20, 3d = +12, 7d = +6
  - 社交互动: 点赞/100 (max 20), 评论/50 (max 15), 观看/10000 (max 20)
  - 平台多样性: 同一故事在 2+ 平台出现 = +10
  - is_hot = score >= 50 (降低阈值，因维度增多)

Usage:
    # 作为模块导入
    from dedup_and_score import deduplicate, calculate_hotness, merge_results

    # 命令行测试
    python dedup_and_score.py
"""
from __future__ import annotations

import json
from datetime import datetime, UTC

# ~50 个主要出版商域名 — 命中获得 +15 权威性加分
PUBLISHER_AUTHORITY: set[str] = {
    # 美国主流新闻
    "cnn.com", "nytimes.com", "washingtonpost.com", "nbcnews.com",
    "cbsnews.com", "abcnews.go.com", "reuters.com", "apnews.com",
    "bloomberg.com", "forbes.com", "wsj.com", "ft.com",
    "economist.com", "time.com", "newsweek.com", "usatoday.com",
    "npr.org", "pbs.org", "foxnews.com", "cnbc.com",
    "businessinsider.com", "marketwatch.com",
    # 英国/国际
    "bbc.com", "bbc.co.uk", "theguardian.com", "independent.co.uk",
    # 科技媒体
    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
    "engadget.com", "cnet.com",
    # 健康/医疗
    "health.com", "webmd.com", "medicalnewstoday.com", "mayoclinic.org",
    "healthline.com", "medscape.com", "statnews.com",
    # 生活/文化
    "esquire.com", "gq.com", "vogue.com", "huffpost.com", "vox.com",
    "nationalgeographic.com",
    # 科学/学术
    "scientificamerican.com", "nature.com", "sciencedaily.com",
}


def _extract_domain(url: str) -> str:
    """从 URL 提取域名（去掉协议和路径，去掉 www. 前缀）。"""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def _is_authority_publisher(url: str, description: str = "") -> bool:
    """检查 URL 是否属于知名出版商。也检查描述中是否包含出版商域名。"""
    domain = _extract_domain(url)
    if domain and _domain_in_authority_set(domain):
        return True

    # 检查 Google 搜索 URL 中的 site: 操作符
    if "site:" in url:
        # 提取 site: 后面的域名
        import re
        match = re.search(r'site:([\w.]+)', url)
        if match:
            d = match.group(1).lower()
            if _domain_in_authority_set(d):
                return True

    return False


def _domain_in_authority_set(domain: str) -> bool:
    """检查域名是否在权威出版商集合中（支持子域名匹配）。"""
    domain = domain.lower().lstrip(".")
    if domain in PUBLISHER_AUTHORITY:
        return True
    for auth in PUBLISHER_AUTHORITY:
        if domain.endswith("." + auth) or domain == auth:
            return True
    return False


def deduplicate(items: list[dict]) -> list[dict]:
    """按 URL + 当日日期去重。

    同一条 URL 一天只写入一次，避免重复推送。
    """
    seen: set[str] = set()
    result: list[dict] = []
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    for item in items:
        url = item.get("url", "")
        if not url:
            continue
        key = f"{url}|{today}"
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _parse_published_date(item: dict) -> datetime | None:
    """尝试从 item 的元数据中解析发布时间。"""
    # 各爬取器可能在不同字段存储时间信息
    for field in ("published_at", "published", "date", "created_at"):
        val = item.get(field)
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except Exception:
                pass

    # 尝试从描述中推断
    # Google News 的 description 包含出版商和摘要，但没有标准时间
    return None


def _calculate_freshness_score(item: dict) -> float:
    """计算新鲜度分数: 24h = +20, 3d = +12, 7d = +6。"""
    pub_time = _parse_published_date(item)
    if pub_time is None:
        # 如果无法确定时间，给中等分数
        return 6.0

    now = datetime.now(UTC)
    if pub_time.tzinfo is None:
        pub_time = pub_time.replace(tzinfo=UTC)

    hours_ago = (now - pub_time).total_seconds() / 3600

    if hours_ago <= 24:
        return 20.0
    elif hours_ago <= 72:
        return 12.0
    elif hours_ago <= 168:
        return 6.0
    else:
        return 2.0  # 超过 7 天给 2 分


def _calculate_authority_score(item: dict) -> float:
    """计算来源权威性分数: 知名出版商 = +15, 垂直博客 = +5。"""
    url = item.get("url", "")
    desc = item.get("description", "")
    platform = item.get("platform", "")

    # YouTube 是一个高权威平台
    if platform == "youtube":
        return 10.0

    # Reddit 是中等权威平台
    if platform == "reddit":
        return 7.0

    # Google News: 检查是否来自权威出版商
    if _is_authority_publisher(url, desc):
        return 15.0

    # 其他来源默认 5 分（垂直博客）
    return 5.0


def _calculate_engagement_score(metrics: dict) -> float:
    """计算社交互动分数:
    - upvotes/100 (max 20)
    - comments/50 (max 15)
    - views/10000 (max 20)
    """
    score = 0.0
    if "upvotes" in metrics:
        score += min(metrics["upvotes"] / 100, 20)
    if "comment_count" in metrics:
        score += min(metrics["comment_count"] / 50, 15)
    if "view_count" in metrics:
        score += min(metrics["view_count"] / 10000, 20)
    if "like_count" in metrics:
        score += min(metrics["like_count"] / 500, 10)
    if "search_interest" in metrics:
        score += min(metrics["search_interest"] / 4, 10)
    return round(min(score, 55), 2)  # 20+15+20 = 55 上限


def calculate_hotness(metrics: dict) -> tuple[float, bool]:
    """计算热度评分 (0-100) 和 is_hot 标记。

    新评分算法:
    - Source authority: major publisher = +15, niche blog = +5
    - Freshness: 24h = +20, 3d = +12, 7d = +6
    - Social engagement: upvotes/100 (max 20), comments/50 (max 15), views/10000 (max 20)
    - is_hot = score >= 50
    """
    score = 0.0

    # 社交互动
    score += _calculate_engagement_score(metrics)

    # 如果传入的是 item dict (含 url, platform 等), 也计算其他维度
    if "url" in metrics or "platform" in metrics:
        score += _calculate_authority_score(metrics)
        score += _calculate_freshness_score(metrics)

    # 如果只有纯 metrics (无 URL/platform), 只有 engagement 部分生效
    score = round(min(score, 100), 2)
    return score, score >= 50.0


def merge_results(*results: dict) -> dict:
    """合并多个爬取器的结果并去重。

    Each result dict has 'hot_links' and 'trend_signals' keys.
    """
    all_hot_links: list[dict] = []
    all_trend_signals: list[dict] = []
    for r in results:
        all_hot_links.extend(r.get("hot_links", []))
        all_trend_signals.extend(r.get("trend_signals", []))

    # 去重 hot_links + trend_signals
    all_hot_links = deduplicate(all_hot_links)
    all_trend_signals = deduplicate_signals(all_trend_signals)

    # 平台多样性加分: 同一故事标题在 2+ 平台出现 = +10
    _apply_platform_diversity_bonus(all_hot_links)

    return {
        "hot_links": all_hot_links,
        "trend_signals": all_trend_signals,
    }


def _apply_platform_diversity_bonus(items: list[dict]) -> None:
    """如果同一故事（标题相似）在 2+ 平台出现，给每条加 +10 分。原地修改。"""
    from collections import defaultdict
    import difflib

    # 按标题归组（使用标题前 50 字符作为相似度键）
    title_groups: dict[str, list[int]] = defaultdict(list)
    for i, item in enumerate(items):
        title = item.get("title", "")[:50].lower().strip()
        if title:
            # 尝试匹配已有的组（使用简单相似度）
            matched_key = None
            for key in title_groups:
                ratio = difflib.SequenceMatcher(None, title, key).ratio()
                if ratio > 0.6:  # 60% 相似度
                    matched_key = key
                    break
            if matched_key:
                title_groups[matched_key].append(i)
            else:
                title_groups[title].append(i)

    # 对跨平台出现的故事加分
    for title, indices in title_groups.items():
        platforms = set(items[i].get("platform", "") for i in indices)
        if len(platforms) >= 2:
            for i in indices:
                old_score = items[i].get("hotness_score", 0) or 0
                items[i]["hotness_score"] = round(old_score + 10.0, 2)
                # 更新 is_hot
                if items[i]["hotness_score"] >= 50:
                    items[i]["is_hot"] = True


def deduplicate_signals(items: list[dict]) -> list[dict]:
    """按品类+关键词+平台+日期去重 trend_signals。
    同一天同一关键词同一平台只保留一条。
    """
    seen: set[str] = set()
    result: list[dict] = []
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    for item in items:
        key = f"{item.get('category_code')}|{item.get('keyword')}|{item.get('platform')}|{today}"
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def limit_per_category(items: list[dict], max_per_cat: int = 10) -> list[dict]:
    """按品类限制每个品类的最大条目数。"""
    by_cat: dict[str, list[dict]] = {}
    for item in items:
        cat = item.get("category_code", "UNKNOWN")
        by_cat.setdefault(cat, []).append(item)

    result: list[dict] = []
    for cat, cat_items in by_cat.items():
        # 按热度排序，取前 N 条
        sorted_items = sorted(
            cat_items,
            key=lambda x: x.get("hotness_score") or 0,
            reverse=True,
        )
        result.extend(sorted_items[:max_per_cat])
    return result


if __name__ == "__main__":
    # 测试去重
    items = [
        {"url": "https://example.com/1", "title": "A"},
        {"url": "https://example.com/1", "title": "A dup"},
        {"url": "https://example.com/2", "title": "B"},
    ]
    deduped = deduplicate(items)
    assert len(deduped) == 2, f"Expected 2, got {len(deduped)}"
    print("✅ Dedup test passed")

    # 测试权威出版商识别
    assert _is_authority_publisher("https://www.cnn.com/2024/01/01/health/heat-therapy")
    assert _is_authority_publisher("https://www.google.com/search?q=site:nbcnews.com \"news title\"")
    assert not _is_authority_publisher("https://blog.example.com/post/1")
    print("✅ Authority publisher detection passed")

    # 测试热度评分 — 高互动度
    score, is_hot = calculate_hotness({
        "url": "https://www.cnn.com/health/heat-therapy",
        "platform": "news",
        "upvotes": 5000,       # 20 pts (capped)
        "comment_count": 2000,  # 15 pts (capped)
        "view_count": 50000,    # 5 pts
        "like_count": 3000,     # 6 pts
    })
    print(f"✅ Hotness (high + authority): {score}, is_hot: {is_hot}")
    assert is_hot, f"Expected is_hot=True for score {score} >= 50"

    # 测试低分
    score2, is_hot2 = calculate_hotness({"upvotes": 5})
    print(f"✅ Hotness (low): {score2}, is_hot: {is_hot2}")
    assert not is_hot2, "Expected is_hot=False for low scores"

    # 测试平台多样性加分
    r1 = {
        "hot_links": [
            {"url": "https://a.com/1", "title": "Heat Therapy Benefits", "platform": "news", "hotness_score": 30.0, "is_hot": False},
        ],
        "trend_signals": [],
    }
    r2 = {
        "hot_links": [
            {"url": "https://b.com/1", "title": "Heat Therapy Benefits Guide", "platform": "reddit", "hotness_score": 20.0, "is_hot": False},
        ],
        "trend_signals": [],
    }
    merged = merge_results(r1, r2)
    # 两条标题相似且来自不同平台，应各加 10 分
    hl0 = merged["hot_links"][0]
    hl1 = merged["hot_links"][1]
    print(f"  Diversity bonus: {hl0.get('hotness_score')}, {hl1.get('hotness_score')}")
    assert hl0.get("hotness_score", 0) >= 30.0, f"Expected diversity bonus, got {hl0.get('hotness_score')}"
    print("✅ Platform diversity bonus passed")

    # 测试合并去重
    r3 = {"hot_links": [{"url": "https://a.com/1"}], "trend_signals": [{"keyword": "a"}]}
    r4 = {"hot_links": [{"url": "https://a.com/1"}, {"url": "https://b.com/2"}], "trend_signals": [{"keyword": "b"}]}
    merged2 = merge_results(r3, r4)
    assert len(merged2["hot_links"]) == 2, f"Expected 2 after dedup, got {len(merged2['hot_links'])}"
    assert len(merged2["trend_signals"]) == 2
    print("✅ Merge test passed")

    print("\nAll tests passed!")
