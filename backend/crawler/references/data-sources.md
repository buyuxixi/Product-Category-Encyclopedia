# Data Sources Reference

Detailed per-source documentation for the hot-topic-crawler. Last updated 2026-07-11.

## Google Trends + Suggest (keyword trend signals)

- **Script**: `scripts/crawl_google_trends.py`
- **Channel 1 — Google Suggest API (primary, always works)**:
  - Endpoint: `https://suggestqueries.google.com/complete/search?client=firefox&q={keyword}`
  - Returns JSON array: `["query", ["suggestion1", "suggestion2", ...]]`
  - No auth needed, no rate limit, but intermittent SSL `UNEXPECTED_EOF_WHILE_READING` errors — wrap in 3-retry loop with 2s backoff.
  - Produces `keyword_trend` signals: 1 main signal per keyword (with suggestion count as metric_value) + 3 related-keyword signals (metric_value=null, but kept in frontend because summary has the related search terms).
  - Output: ~8 signals per category × 7 categories = 56 total.
- **Channel 2 — Google Trends Explore API (disabled)**:
  - Endpoints: `trends.google.com/trends/api/explore` (POST) → `trends.google.com/trends/api/widgetdata/multiline` (GET)
  - Status: ❌ Returns HTTP 500 or 429 consistently as of 2026-07-11. Even with cookies + proper headers, the explore endpoint returns 500.
  - `pytrends` library unusable: depends on `pandas`→`numpy`, and numpy C-extension has Python version mismatch (compiled for 3.11, runtime is 3.13).
  - Code preserved in script but not called. If Google lifts the rate limit in the future, re-enable by uncommenting the `get_google_trends_interest()` call.
- **No hot_links produced** — Google Trends/Suggest URLs are search pages, not specific content.

## YouTube (Primary video source)

- **Script**: `scripts/crawl_youtube.py`
- **Method**: Parse `ytInitialData` JSON from YouTube search results page HTML. No API key needed.
- **Search URL**: `youtube.com/results?search_query={keyword}&sp=EgIIBA&hl=en` (filter: this year, English locale)
- **Freshness**: Hard 3-month cutoff (90 days). Videos older than 90 days are **excluded entirely**, not scored lower. `_parse_age_days()` returns `None` for "year" in published text or age > 90 days.
- **Title relevance filter**: `_is_relevant(title, keyword)` checks at least one keyword stem (len > 2, "review"/"best" stripped) appears in title. Filters anime/manhwa/gaming false positives.
- **Scoring (freshness-dominant)**:
  - Freshness: <7d=+25, <30d=+20, <60d=+12, <90d=+6 (max 25 pts — heaviest dimension)
  - Views: >100K=+15, >10K=+10, >1K=+5, <1K=+1 (max 15 pts)
  - Channel authority: known tech/review channels=+10, other=+3 (max 10 pts)
  - `is_hot` = score >= 15
- **Cross-section distribution** (added 2026-07-11): Top 5 videos per keyword are distributed across sections:
  - Video #1 → `section_key="technology"` (技术、材料与设计原则)
  - Video #2 → `section_key="users"` (用户画像与使用场景)
  - Video #3 → `section_key="needs"` (用户需求与品类痛点)
  - Video #4-5 → `section_key="market"` (舆情与市场趋势)
  - This ensures each section has relevant video content, not all piled in market.
- **Known issue**: Some requests get SSL `UNEXPECTED_EOF_WHILE_READING` — transient, logged and skipped.

## Bing News RSS (Primary news source)

- **Script**: `scripts/crawl_google_news.py` (filename kept for backward compat, actually uses Bing)
- **Endpoint**: `https://www.bing.com/news/search?q={keyword}&format=rss`
- **URL extraction**: Bing returns redirect URLs (`bing.com/news/apiclick.aspx?...&url=https://realsite.com/article`). Extract the `url=` query param to get the real article URL.
- **Freshness window**: 30 days. Articles older than 30 days are silently skipped.
- **Publisher authority**: ~33 major domains in `PUBLISHER_AUTHORITY` set (cnn.com, nytimes.com, nature.com, etc.) get +15 score. Others get +5.
- **Score range**: 11-35 (freshness 6-20 + authority 5-15). `is_hot` = score >= 30.
- **Cross-section distribution** (added 2026-07-11): News articles distributed across sections:
  - Article #1 → `section_key="trends"` (新兴趋势)
  - Article #2 → `section_key="needs"` (用户需求与品类痛点)
  - Article #3+ → `section_key="market"` (舆情与市场趋势)
- **Known issue**: Some keywords return SSL `UNEXPECTED_EOF_WHILE_READING` errors intermittently. These are transient — the crawler logs a warning and continues.

## Reddit (Rate-limited without OAuth, works with single-category rotation)

- **Scripts**: `scripts/crawl_reddit.py` (full pipeline) + `scripts/crawl_reddit_single.py` (single-category)
- **Architecture**: Dual-channel — OAuth API (preferred) + RSS fallback (works with single-category rotation).
- **Channel 1 — Reddit OAuth API via PRAW (preferred)**:
  - Requires: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` env vars + `praw` pip package.
  - Returns: real upvotes, comment counts, post permalinks. Not affected by IP blocks.
  - Setup: `reddit.com/prefs/apps` → create "script" app → set env vars.
  - When configured: auto-detected, uses OAuth for all requests.
  - Rate limiting: 2s between subreddit+keyword combos (OAuth allows higher rate).
- **Channel 2 — RSS search feed (fallback, works with single-category rotation)**:
  - Endpoint: `www.reddit.com/r/{sub}/search.rss?q={keyword}&sort=relevance&limit=5&t=year&restrict_sr=on`
  - **`restrict_sr=on` is CRITICAL**: Without it, Reddit returns generic subreddit hot posts (anime, wigs, college) instead of keyword-matched results. Always include this parameter.
  - **Keyword relevance filter**: After fetching RSS entries, filter by checking that at least one keyword stem (len > 2) appears in the title or description. This catches the occasional irrelevant post that slips through.
  - RSS provides NO upvote/comment counts — all engagement metrics are 0. Posts are scored on freshness + platform authority only.
  - Retry: 2 retries with 30s/60s backoff on 429. 429 is the main failure mode — Reddit's rate limiting is aggressive (2 requests in quick succession triggers it).
  - Rate limit behavior: Single requests with **40s+** gaps succeed reliably. Continuous requests with 6s gaps trigger 429 immediately. Once 429'd, need 60-180s cooldown before next success.
- **Single-category rotation pattern (when OAuth is not available)**:
  - `scripts/crawl_reddit_single.py <CATEGORY_CODE>` — crawls ONE category (2 subreddit requests, 40s apart), then logs in and pushes directly. Only clears Reddit-platform hot_links for that category (preserves YouTube/News data).
  - `scripts/cron_reddit_crawl.sh` — Cron wrapper using `date +%j % 7` to pick today's category. Schedule: `0 10 * * *` (2 hours after main crawl at 08:00).
  - 7-day cycle covers all 7 categories. Each day only 2 requests are made, staying within Reddit's rate limit.
  - Proxy env vars (`HTTP_PROXY`/`HTTPS_PROXY`) MUST be set in the cron wrapper — httpx does not read macOS system proxy.
- **Proxy requirement**: If the machine has a local proxy (Clash/V2Ray), httpx will NOT use it automatically. Without `HTTP_PROXY`/`HTTPS_PROXY` env vars set, all Reddit HTTPS requests fail with `[SSL: UNEXPECTED_EOF_WHILE_READING]`. Check `scutil --proxy` to find the proxy port (typically `127.0.0.1:7897`).
- **section_key**: Reddit `hot_links` use `section_key="users"` so discussions appear in user personas section.
- **Hermes network gateway factor**: User clarified that Hermes's HTTP requests go through a company gateway (different exit IP) while browser/curl may go direct. The local proxy (Clash/V2Ray) handles the routing — setting `HTTP_PROXY`/`HTTPS_PROXY` ensures httpx uses the same proxy path as the browser.

## TikTok (Blocked by anti-bot)

- **Script**: `scripts/crawl_tiktok.py` (ready but non-functional)
- **Method**: Playwright headless browser loads `tiktok.com/search?q={keyword}`, waits for `div[data-e2e='search_video-item']`.
- **Status**: ❌ Blocked. TikTok detects headless Playwright and only serves a skeleton loader.
- **To make it work**: (a) Install `playwright-stealth`, (b) Use residential proxies, (c) Use `TikTokApi` Python library (GitHub: `davidteather/TikTok-Api`, 6483 stars).

## Amazon (Optional, disabled by default)

- **Script**: `scripts/crawl_amazon.py`
- **Method**: Playwright browser automation. Often blocked by anti-scraping.
- **Status**: Disabled by default. Enable in `crawl_config.yaml` if needed.
