# Data Source API Quirks (Tested 2026-07)

Real-world behavior observed during implementation. Update when APIs change.

## Reddit (IP-blocked without OAuth — confirmed 2026-07)

- **All non-OAuth endpoints blocked at IP level**: `www.reddit.com/r/{sub}/search.json` returns 403 Blocked. `old.reddit.com` JSON returns 403. RSS `search.rss` returns 429 (rate-limited) or 403. Even the browser tool gets "You've been blocked by network security." This is NOT a User-Agent or TLS fingerprint issue — it's an IP-level block.
- **RSS search returns irrelevant content when it does work**: `search.rss` returns the subreddit's HOT posts, not keyword-filtered search results. Searching for "TENS" in r/ChronicPain returns random posts about debt, college, dementia. Completely useless.
- **Solution: Reddit OAuth API via PRAW**: `pip install praw`. Register a "script" app at `reddit.com/prefs/apps`. Set `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` env vars. The OAuth API works from any IP because it uses Reddit's official auth flow. Returns real `ups`, `num_comments`, `score`, and `permalink` fields.
- **Graceful fallback**: If OAuth is not configured, the crawler logs a warning and skips Reddit entirely. No partial/broken data is pushed.
- **section_key**: Reddit `hot_links` use `section_key="users"` so discussions appear alongside user persona content, not buried in the market section.

## Bing News RSS (primary news source, implemented)

- **Source URL**: `https://www.bing.com/news/search?q={keyword}&format=rss`
- **No auth needed**, no rate limit observed.
- **RSS format**: Standard RSS 2.0, parseable with `feedparser`.
- **URL extraction**: Bing News RSS returns redirect URLs like `http://www.bing.com/news/apiclick.aspx?ref=FexRss&aid=&tid=...&url=https%3a%2f%2fwww.realsite.com%2farticle`. Extract the `url=` query parameter using `urllib.parse.parse_qs(urlparse(bing_url).query).get('url', [''])[0]` and `unquote()` it to get the real article URL.
- **Result**: Direct links to articles on publisher sites (CNN, NYT, HuffPost, Nature, Yahoo, PopSci, Chicago Tribune, etc.)
- **Publisher extraction**: Article title from Bing News includes publisher name as suffix (e.g., "Article Title - CNN"). Split on ` - ` to extract publisher name. Domain extracted from real URL via `urllib.parse.urlparse`.
- **Freshness window**: 30 days. Niche B2B keywords don't generate daily news. Articles older than 30 days are skipped.
- **SSL errors**: Occasional `UNEXPECTED_EOF_WHILE_READING` — transient, retry works.
- **Result count**: Typically 2-15 entries per keyword. Niche keywords may return 0 fresh articles (within 30 days).
- **Scoring**: Freshness (7d=+20, 30d=+12, 90d=+6) + publisher authority (+15 for ~33 major domains, +5 for others). `is_hot` = score >= 30. Range: 11-35.

## Google News RSS (DEPRECATED — replaced by Bing News)

- **ARTICLE URLs ARE BROKEN (2026-07):** The RSS feed returns URLs in the format `news.google.com/rss/articles/CBMi...` which return HTTP 400 — completely unusable.
- **Publisher data IS available:** `entry.source.href` (domain) and `entry.source.title` (name).
- **Old workaround (also bad):** Constructing Google search URLs (`google.com/search?q=site:domain "title"`) — this produces SEARCH PAGES, not article links. Users click and see search results, not the article.
- **Replaced by:** Bing News RSS which provides real article URLs directly.
- **If Bing News is unavailable:** Fall back to Google News RSS but extract publisher domain for the description. The Google News URL itself is unusable.

## Google Trends (BROKEN — replaced by Google Suggest API)

- **pytrends is BROKEN (2026-07):** The `pytrends` library depends on `pandas`→`numpy`, and the numpy C-extension has a Python version mismatch (compiled for cpython-3.11, runtime is 3.13). `import numpy` raises `ModuleNotFoundError: No module named 'numpy._core._multiarray_umath'`. Even if numpy is fixed, the Google Trends Explore API (`trends.google.com/trends/api/explore`) consistently returns HTTP 500 or 429, even with cookies and proper browser headers.
- **Replacement: Google Suggest API** (`suggestqueries.google.com/complete/search?client=firefox&q={keyword}`). Always available, no auth, no rate limit. Returns real user search queries (e.g., searching "TENS unit" returns "tens unit pads", "tens unit for back pain", "tens unit for labor"). Intermittent SSL errors (`UNEXPECTED_EOF_WHILE_READING`) — wrap in a 3-retry loop with 2s backoff.
- **Output:** `keyword_trend` signals (NOT `search_volume`). Each keyword produces ~8 signals: 1 main (with suggestion count as metric_value) + 3 related keywords (metric_value=null, but summary carries the search query text).
- **No hot_links:** Neither Google Trends nor Google Suggest produce hot_links — Google Trends URLs are search pages, not content.
- **If Google Trends API recovers:** The `get_google_trends_interest()` function is preserved in `crawl_google_trends.py` but disabled. To re-enable: fix numpy version, uncomment the explore API call, and it will produce `search_volume` signals with interest values 0-100.

## YouTube (search page HTML parsing — no API key)

- **No API key needed**: The crawler parses `ytInitialData` JSON embedded in YouTube search results pages.
- **Search URL**: `youtube.com/results?search_query={keyword}&sp=EgIIBA&hl=en` (filter: this year, English locale). Do NOT use `sp=CAMSAhAB` (sort by view count) — that returns 8-15 year old videos useless for trend tracking.
- **JSON extraction**: `re.search(r"ytInitialData\s*=\s*(\{.+?})\s*;?\s*</script>", resp.text, re.DOTALL)`
- **JSON navigation**: `data.contents.twoColumnSearchResultsRenderer.primaryContents.sectionListRenderer.contents[].itemSectionRenderer.contents[].videoRenderer`
- **Data extracted**: videoId, title, viewCount (simpleText), channel (ownerText.runs[0].text), publishedTimeText
- **URL format**: `youtube.com/watch?v={videoId}`
- **No quota limits**: No API key means no daily quota. Can search unlimited keywords.
- **Scoring (freshness-dominant)**: Freshness (<7d=+25, <30d=+20, <60d=+12, <90d=+6) + Views (>100K=+15, >10K=+10, >1K=+5, <1K=+1) + Channel authority (known channels=+10, others=+3). `is_hot` = score >= 15. Hard 3-month cutoff: videos older than 90 days are excluded entirely, not just scored lower. 0-view videos are hard-filtered with `if views == 0: continue`.
- **Title relevance filter**: `_is_relevant(title, keyword)` checks that the title contains at least one keyword stem (len > 2, after removing "review"/"best" filler). Filters out anime/manhwa/gaming results from loose YouTube search.
- **SSL errors**: Occasional `UNEXPECTED_EOF_WHILE_READING` — transient, retry works.
- **Result count**: 5-10 videos per keyword. Sorted by view count so highest-views videos come first.

## Amazon (Playwright)

- **Anti-scraping:** Amazon blocks headless browsers aggressively. Use random User-Agent from a pool, 2-4s page load delays, 3-5s between keywords.
- **Selectors:** `[data-component-type="s-search-result"]` for result cards, `data-asin` attribute for ASIN, `.a-price-whole` + `.a-price-fraction` for price, `span.a-size-base.s-underline-text` for rating count.
- **Headless mode:** `headless=True` works but is more likely to be blocked. If blocked, try `headless=False` or use a proxy.
- **Fallback:** If Playwright is blocked entirely, consider third-party APIs (Rainforest API, Keepa API) as alternatives.

## TikTok (Playwright — needs stealth/proxy)

- **Anti-bot detection:** TikTok detects headless Playwright and serves a "verify you're human" page instead of search results. The `wait_for_selector("div[data-e2e='search_video-item']")` times out at 10s.
- **Script is correct:** `crawl_tiktok.py` properly navigates to `tiktok.com/search?q={keyword}`, waits for video cards, and extracts video URL, author, play count, like count.
- **Fix needed:** One of: (a) `pip install playwright-stealth` and apply stealth to the browser context; (b) use residential proxies via Browserbase; (c) use the unofficial `TikTokApi` Python library (github: `davidteather/TikTok-Api`, 6,483 stars) which handles anti-bot internally.
- **URL format when working:** `tiktok.com/@{author}/video/{videoId}` — direct video page link.
- **Data extraction selectors:** `div[data-e2e='search_video-item']` for video cards, `a[href*='/video/']` for video URL, `a[href*='/@']` for author, `span[data-e2e='video-views']` for play count, `span[data-e2e='like-count']` for like count.
- **Count parsing:** TikTok displays counts as "1.2M", "15.3K" — parse with `parse_count()` function that multiplies by 1M or 1K.

## Encyclopedia Backend API

- **Batch endpoint:** `POST /api/v1/hot-links/batch` and `POST /api/v1/trend-signals/batch`. Max 500 items per batch.
- **Auth:** Session cookie-based. The push script (`push_to_encyclopedia.py`) auto-logs in via `POST /api/v1/auth/local/login` with admin credentials and passes the returned session cookie to all batch requests. The `login()` function is called automatically by `push_all()` when no cookies are provided.
- **Dedup at DB level:** No unique constraint on URL+date — the `dedup_and_score.py` script handles dedup before pushing.
- **Frontend layout (EncyclopediaView.vue):** The "06 舆情与市场趋势" section renders in priority order: (1) 🔥 今日热点 (hot_links) at top, with empty state when 0 items; (2) 📊 趋势信号 (trend_signals); (3) 📝 分析内容 (section content); (4) 📎 证据来源 (evidence). Top stats bar shows hot_links count (red highlight) and trend_signals count first. Frontend requests `days=7` (not 365).
- **Category existence:** Items with `category_code` not in the DB are silently skipped (returned in `skipped` array). Always verify categories exist before crawling — e.g., `PILL_ORGANIZER` may not exist if the category was never created via `import_amazon_directories`.
- **Port discovery:** The backend may not be on port 8000. Check `docker-compose.yml` for the host port mapping (e.g., `"8010:8000"` means the backend is reachable on localhost:8010). Set `ENCYCLOPEDIA_API_BASE` env var to match.
