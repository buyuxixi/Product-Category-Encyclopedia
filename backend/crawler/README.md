# Hot Topic Crawler

舆情热点爬取模块 — 每日自动从 Amazon / Google Trends / Reddit / YouTube / TikTok / Bing News 等数据源爬取市场趋势数据，写入 `hot_links` 和 `trend_signals` 表。

## 目录结构

```
backend/crawler/
├── run_full_crawl.py          # 全量爬取入口 (Bing News + Reddit + YouTube + Google Suggest)
├── crawl_amazon_bsr.py        # Amazon BSR 爬取 (httpx + proxy, 默认不执行)
├── crawl_amazon.py            # Amazon Playwright 爬取 (备用, 需浏览器)
├── crawl_google_news.py       # Bing News RSS 爬取
├── crawl_google_trends.py     # Google Suggest API 关键词趋势
├── crawl_reddit.py            # Reddit 爬取 (OAuth 优先, RSS fallback)
├── crawl_reddit_single.py     # Reddit 单品类爬取 (配合轮转 cron)
├── crawl_youtube.py           # YouTube 搜索页 HTML 解析 (无需 API Key)
├── crawl_youtube_comments.py  # YouTube 评论分析 (痛点提取)
├── crawl_tiktok.py            # TikTok 爬取 (Playwright, 常被反爬)
├── dedup_and_score.py         # 去重 + 热度评分 (多维度 0-100)
├── push_to_encyclopedia.py    # 推送到百科后端 (Batch API)
├── xhs_cleaned_adapter.py     # 小红书 cleaned JSON → 统一结果 / 增量 upsert
├── cron_crawl.sh              # Cron 全量爬取 wrapper
├── cron_reddit_crawl.sh       # Cron Reddit 单品类轮转 wrapper
├── references/                # 各数据源技术细节、URL 质量指南等
└── templates/
    └── crawl_config.yaml       # 爬取配置模板
```

## 数据流

```
爬取脚本 → dedup_and_score (去重+评分) → push_to_encyclopedia (按平台清旧→写新→通知)
                                              ↓
                                    POST /api/v1/hot-links/batch
                                    POST /api/v1/trend-signals/batch
                                              ↓
                                    hot_links 表 / trend_signals 表
                                              ↓
                                    前端: 品类百科 / 总览 / 趋势看板 / 选品Agent

小红书 cleaned JSON → xhs_cleaned_adapter → push_incremental (不清旧→Batch upsert)
```

## 执行方式

### 1. Cron 自动执行 (推荐)

两个 Hermes Cron Job:

| Job | Schedule | 脚本 | 说明 |
|-----|----------|------|------|
| 热点爬取 | `0 8 * * *` (北京16:00) | `cron_crawl.sh` | 全量: Bing News + YouTube + Google Suggest |
| Reddit单品类 | `0 10 * * *` (北京18:00) | `cron_reddit_crawl.sh` | 轮转7个品类, 每天1个 |

Cron Job 配置: `no_agent=True`, `script=backend/crawler/cron_crawl.sh`

### 2. 手动执行

```bash
cd backend

# 全量爬取
CRAWLER_PASSWORD=xxx \
HTTP_PROXY=http://127.0.0.1:7897 \
HTTPS_PROXY=http://127.0.0.1:7897 \
.venv/bin/python crawler/run_full_crawl.py

# 单品类 Reddit
CRAWLER_PASSWORD=xxx \
HTTP_PROXY=http://127.0.0.1:7897 \
HTTPS_PROXY=http://127.0.0.1:7897 \
.venv/bin/python crawler/crawl_reddit_single.py HEAT_THERAPY

# Amazon BSR (默认不执行, 需手动)
HTTP_PROXY=http://127.0.0.1:7897 \
HTTPS_PROXY=http://127.0.0.1:7897 \
.venv/bin/python crawler/crawl_amazon_bsr.py

# 预览小红书 cleaned JSON 的统一 crawler 结果
.venv/bin/python crawler/xhs_cleaned_adapter.py \
  --data-dir ../data/cleaned \
  --output /tmp/xhs-crawl-result.json

# 确认预览后，通过 Batch API 增量 upsert
CRAWLER_PASSWORD=xxx \
.venv/bin/python crawler/xhs_cleaned_adapter.py \
  --data-dir ../data/cleaned \
  --push
```

### 3. API 触发

`POST /api/v1/categories/{code}/crawl` — 后端通过 subprocess 调用 `run_full_crawl.py` + `crawl_reddit_single.py`。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ENCYCLOPEDIA_API_BASE` | `http://localhost:8010/api/v1` | 后端 API 地址 |
| `CRAWLER_USERNAME` | `admin` | 后端登录用户名 |
| `CRAWLER_PASSWORD` | (必填) | 后端登录密码, 或写入 `backend/.crawler_password` |
| `HTTP_PROXY` | — | 本地代理 (httpx 不读系统代理, 必须显式设置) |
| `HTTPS_PROXY` | — | 同上 |
| `FEISHU_WEBHOOK_URL` | — | 飞书通知 Webhook (可选) |
| `MAX_HOTLINKS_PER_CATEGORY` | `10` | 每品类最大 hot_links 数 |
| `REDDIT_CLIENT_ID` | — | Reddit OAuth (可选, 避免限流) |
| `REDDIT_CLIENT_SECRET` | — | Reddit OAuth (可选) |

## 依赖

```bash
cd backend && .venv/bin/pip install feedparser
# TikTok/Amazon Playwright (可选):
.venv/bin/pip install playwright && python -m playwright install chromium
```

## 数据写入的表

- **`hot_links`** — 热点跳转链接 (产品/视频/讨论/新闻)
- **`trend_signals`** — 趋势信号 (搜索量/社媒提及/关键词趋势/新闻量/产品洞察/用户痛点)

全量爬虫仅清除本次成功产出结果的“品类 + 平台”旧数据，再写入新结果；
其它平台和失败数据源的历史记录会保留。小红书适配器使用增量模式，不执行清理：

- `hot_links` 按“品类 + 平台 + URL”upsert。
- `trend_signals` 按“品类 + 平台 + 标题”upsert。
- 默认只转换和预览；仅 `--push` 会调用后端 API。
- cleaned 输入兼容历史 `api` 评论结构和新的 `grouped` 评论结构。

## 展示界面

| 界面 | 展示内容 |
|------|----------|
| 品类百科 (EncyclopediaView) | 第6章「舆情与市场趋势」: 产品/视频/讨论/趋势 Tab 切换 |
| 总览 (DashboardView) | 跨品类热点聚合 + 平台分布统计 |
| 趋势看板 (TrendView) | 全量趋势信号 + YouTube 播放排名 + 关键词标签 |
| 选品Agent (AgentView) | 从 hot_links + trend_signals 读数据喂给 LLM |
