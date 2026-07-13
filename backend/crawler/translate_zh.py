#!/usr/bin/env python3
"""翻译管道 — 调用 LLM 批量为 hot_links / trend_signals 生成中文标签。

设计原则：
  - title_zh 是业务扫读短标签，不是 Listing 卖点堆砌
  - 批量调用（每批最多 10 条），降低 API 成本
  - 失败容错：单批失败不影响整体流程，跳过并继续
  - 不修改原始 title/description，只填充 *_zh 字段

使用方式：
  from crawler.translate_zh import translate_hot_links, translate_trend_signals
  translate_hot_links(hot_links_list)  # 就地修改，回填 title_zh / description_zh
  translate_hot_links(hot_links_list, force=True)  # 覆盖已有中文标签

环境变量（复用后端 LLM 配置）:
  LLM_API_KEY, LLM_BASE_URL, LLM_MODEL (默认 qwen-plus)
"""
from __future__ import annotations

import json
import os
import sys
import time

import httpx

# 复用后端配置
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://llm-4ky3t9l8il29a1dv.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
)
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")

BATCH_SIZE = 10  # 每批最多 10 条
MAX_RETRIES = 2
RETRY_DELAY = 3  # 秒
TITLE_ZH_MAX = 22  # 业务扫读短标签硬上限（字符）


def _call_llm(messages: list[dict], *, temperature: float = 0.2) -> str:
    """调用 LLM，返回 content 文本。"""
    if not LLM_API_KEY:
        print("  [WARN] LLM_API_KEY not set, skipping translation", file=sys.stderr)
        return ""

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"},
    }

    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")

    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=60.0, proxy=proxy) as client:
                resp = client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                # 某些网关不支持 JSON mode，降级
                if resp.status_code in {400, 422}:
                    fallback = {k: v for k, v in payload.items() if k != "response_format"}
                    resp = client.post(
                        f"{LLM_BASE_URL}/chat/completions",
                        headers=headers,
                        json=fallback,
                    )
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                result = resp.json()
                content = result["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError("LLM returned empty content")
                return content
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"  [WARN] LLM call failed (attempt {attempt+1}): {e}", file=sys.stderr)
                time.sleep(RETRY_DELAY)
            else:
                raise

    return ""  # unreachable，但满足类型检查


def _clip_title_zh(text: str) -> str:
    """截断过长标签；尽量在分隔符处切断。"""
    text = (text or "").strip().replace("——", "·").replace("—", "·")
    if len(text) <= TITLE_ZH_MAX:
        return text
    for sep in (" · ", "·", "，", ",", "（", "("):
        idx = text.rfind(sep, 0, TITLE_ZH_MAX + 1)
        if idx >= 8:
            return text[:idx].rstrip(" ·，,")
    return text[:TITLE_ZH_MAX].rstrip(" ·，,")


def translate_hot_links(hot_links: list[dict], *, force: bool = False) -> int:
    """批量翻译 hot_links，就地为每条回填 title_zh 和 description_zh。

    Returns: 成功翻译的条数
    """
    if not hot_links:
        return 0

    need_translate = hot_links if force else [l for l in hot_links if not l.get("title_zh")]
    if not need_translate:
        print("  [translate] All hot_links already have title_zh, skipping")
        return 0

    print(f"  [translate] Translating {len(need_translate)} hot_links in batches of {BATCH_SIZE}...")
    success = 0

    for i in range(0, len(need_translate), BATCH_SIZE):
        batch = need_translate[i:i + BATCH_SIZE]
        try:
            results = _translate_hot_links_batch(batch)
            for item, zh in zip(batch, results):
                if zh.get("title_zh"):
                    item["title_zh"] = _clip_title_zh(zh["title_zh"])[:200]
                if "description_zh" in zh:
                    item["description_zh"] = (zh.get("description_zh") or "").strip()
                success += 1
        except Exception as e:
            print(f"  [WARN] Batch {i//BATCH_SIZE} translation failed: {e}", file=sys.stderr)
        time.sleep(0.5)

    print(f"  [translate] Done: {success}/{len(need_translate)} hot_links translated")
    return success


def _translate_hot_links_batch(batch: list[dict]) -> list[dict]:
    """单批翻译 hot_links，返回 [{title_zh, description_zh}] 列表。"""
    items_text = []
    for idx, link in enumerate(batch):
        title = link.get("title", "")[:200]
        desc = link.get("description", "")[:300]
        platform = link.get("platform", "")
        link_type = link.get("link_type", "")
        items_text.append(
            f"[{idx}] platform={platform} type={link_type}\n  title: {title}\n  desc: {desc}"
        )

    prompt = f"""你是跨境电商内部工具的「中文短标签」助手。读者是选品/运营同事，要快速扫读，不是写商品详情页。

为以下 {len(batch)} 条数据各生成 title_zh（必填）和 description_zh（可空）。

【title_zh 规则 — 最重要】
1. 最多 {TITLE_ZH_MAX} 个汉字/字符（含标点），宁可短，不要堆卖点
2. 固定结构：品牌(若有) + 品类核心词 + 最多1个差异点；件数可用「·2装」
3. 禁止：破折号——、SKU/型号数字、重复品类词、SEO关键词串、广告口吻
4. 品牌名保留英文（GE、AUVON、MAZ-TEK）
5. 术语统一：
   - Dusk to Dawn / auto sensor → 光控
   - Color Changing / RGB → 变色
   - Plug-in / Plug into Wall → 插电
   - Dimmable → 调光
   - Motion Sensor → 人体感应
   - Warm White / Amber → 暖光
   - Pack / 2 Pack → 2装

【description_zh 规则】
- Amazon/product：不要复述价格、评分、评论数、BSR（卡片上已有）；无独特信息则返回空字符串 ""
- 视频/讨论：用 ≤20 字点出核心话题即可

【好坏对照】
原文: Night Lights Plug into Wall [2 Pack], Color Changing...
❌ 插墙式变色夜灯（2只装）——8色RGB儿童房夜灯，带光感自动启停功能
✅ 变色插电夜灯·2装

原文: GE Color Changing LED Night Light for Kids, Dusk to Dawn...
❌ GE彩色渐变LED儿童夜灯，光感自动启停，卧室氛围照明
✅ GE·儿童变色夜灯

原文: MAZ-TEK Plug in Dimmable Led Night Light with Auto Dusk to Dawn...
❌ MAZ-TEK插电式智能光感夜灯（4件装），暖白光可调光
✅ MAZ-TEK·调光插电夜灯·4装

数据：
{chr(10).join(items_text)}

返回 JSON: {{"results": [{{"title_zh": "...", "description_zh": "..."}}, ...]}}
results 长度必须 = {len(batch)}。"""

    content = _call_llm([
        {
            "role": "system",
            "content": (
                "你为内部选品看板生成极短中文标签。"
                f"title_zh 严格 ≤{TITLE_ZH_MAX} 字，像导航标签不像商品文案。"
            ),
        },
        {"role": "user", "content": prompt},
    ])

    data = json.loads(content)
    results = data.get("results", [])
    while len(results) < len(batch):
        results.append({"title_zh": "", "description_zh": ""})
    return results[:len(batch)]


def translate_trend_signals(trend_signals: list[dict], *, force: bool = False) -> int:
    """批量翻译 trend_signals，就地为每条回填 title_zh 和 summary_zh。

    Returns: 成功翻译的条数
    """
    if not trend_signals:
        return 0

    need_translate = trend_signals if force else [s for s in trend_signals if not s.get("title_zh")]
    if not need_translate:
        print("  [translate] All trend_signals already have title_zh, skipping")
        return 0

    print(f"  [translate] Translating {len(need_translate)} trend_signals in batches of {BATCH_SIZE}...")
    success = 0

    for i in range(0, len(need_translate), BATCH_SIZE):
        batch = need_translate[i:i + BATCH_SIZE]
        try:
            results = _translate_trend_signals_batch(batch)
            for item, zh in zip(batch, results):
                if zh.get("title_zh"):
                    item["title_zh"] = _clip_title_zh(zh["title_zh"])[:200]
                if zh.get("summary_zh"):
                    item["summary_zh"] = zh["summary_zh"]
                success += 1
        except Exception as e:
            print(f"  [WARN] Batch {i//BATCH_SIZE} translation failed: {e}", file=sys.stderr)
        time.sleep(0.5)

    print(f"  [translate] Done: {success}/{len(need_translate)} trend_signals translated")
    return success


def _translate_trend_signals_batch(batch: list[dict]) -> list[dict]:
    """单批翻译 trend_signals。"""
    items_text = []
    for idx, sig in enumerate(batch):
        title = sig.get("title", "")[:200]
        summary = sig.get("summary", "")[:300]
        keyword = sig.get("keyword", "")
        signal_type = sig.get("signal_type", "")
        items_text.append(
            f"[{idx}] type={signal_type} keyword={keyword}\n  title: {title}\n  summary: {summary}"
        )

    prompt = f"""你是市场趋势分析助手。为 {len(batch)} 条趋势信号生成中文短标签，供内部运营扫读。

规则：
1. title_zh: ≤{TITLE_ZH_MAX}字，直译核心意思，保留数字；禁止破折号堆砌
2. summary_zh: ≤40字，保留关键数字/涨跌；不要空话
3. 品牌与专有名词可保留英文

数据：
{chr(10).join(items_text)}

返回 JSON: {{"results": [{{"title_zh": "...", "summary_zh": "..."}}, ...]}}
results 长度必须 = {len(batch)}。"""

    content = _call_llm([
        {"role": "system", "content": "你输出极短中文趋势标签，供内部看板扫读。"},
        {"role": "user", "content": prompt},
    ])

    data = json.loads(content)
    results = data.get("results", [])
    while len(results) < len(batch):
        results.append({"title_zh": "", "summary_zh": ""})
    return results[:len(batch)]


def translate_crawl_result(crawl_result: dict, *, force: bool = False) -> dict:
    """翻译整个爬取结果（hot_links + trend_signals），就地修改。"""
    hl = crawl_result.get("hot_links", [])
    ts = crawl_result.get("trend_signals", [])

    if hl:
        translate_hot_links(hl, force=force)
    if ts:
        translate_trend_signals(ts, force=force)

    return crawl_result


if __name__ == "__main__":
    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        data = json.loads(stdin_data)
        translate_crawl_result(data)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("Usage: echo '{\"hot_links\":[...]}' | python translate_zh.py")
