# URL Quality Guide — What Makes a Good Hot Link

> Created 2026-07 after user feedback that crawled data quality was poor.
> Core principle: **every hot_link URL must point to a specific, viewable piece of content.**
> Updated 2026-07-11: Bing News replaces Google News. YouTube uses HTML parsing (no API key). TikTok crawler added.

## Quality Spectrum

### ✅ Good URLs (specific content pages)

| Source | URL Pattern | Why Good |
|--------|------------|----------|
| Bing News | `nbcnews.com/health/shoulder-heat-therapy-rcna12345` | Real article URL extracted from Bing redirect |
| Reddit | `reddit.com/r/ChronicPain/comments/abc123/title` | Specific post with discussion |
| YouTube | `youtube.com/watch?v=dQw4w9WgXcQ` | Specific video with view/like counts |
| Amazon | `amazon.com/dp/B0CXYZ123` | Specific product with reviews |
| TikTok | `tiktok.com/@username/video/1234567890` | Specific video with play/like counts |

### ❌ Bad URLs (search pages, dashboards, redirects, broken)

| Source | URL Pattern | Why Bad |
|--------|------------|---------|
| Google Trends | `trends.google.com/trends/explore?q=heating+pad` | Search page, not content |
| Google News RSS | `news.google.com/rss/articles/CBMi...` | Broken redirect (HTTP 400) |
| Google Search | `google.com/search?q=site:nbcnews.com "title"` | Search page, not article (old workaround, replaced by Bing News) |
| Amazon Search | `amazon.com/s?k=heating+pad` | Search results page, not a product |

## Rules

1. **Search pages are not content.** If a URL shows a list of results rather than a single article/video/post, it's a search page — don't store it as a hot_link.
2. **Redirect URLs that don't resolve are worse than no URL.** If a URL returns an error page when clicked, it damages user trust. Either resolve it to the real URL or don't push it.
3. **When a source only provides search-page URLs, use trend_signals instead.** Google Trends interest values are useful data — store them as `trend_signal` with `signal_type="search_volume"`, but don't create `hot_link` entries for the Trends explore page.
4. **Always verify URLs after code changes.** Run the full crawl, then check the DB: `curl -s -b cookies "http://localhost:8010/api/v1/categories/{CODE}/hot-links?days=7" | python3 -c "import sys,json; [print(i['url']) for i in json.load(sys.stdin)['items']]"`. Eyeball each URL — if any is a search page or returns 400, fix the crawler. Do NOT report "done" without this verification.

## Source-Specific URL Strategies

### Bing News RSS (primary news source, implemented)
- **Source URL**: `https://www.bing.com/news/search?q={keyword}&format=rss`
- **URL extraction**: Bing News RSS returns redirect URLs like `http://www.bing.com/news/apiclick.aspx?...&url=https%3a%2f%2fwww.realsite.com%2farticle`. Extract the `url=` query parameter using `urllib.parse.parse_qs` and `unquote` it to get the real article URL.
- **Result**: Direct links to articles on publisher sites (CNN, NYT, HuffPost, Nature, Yahoo, PopSci, etc.)
- **Publisher extraction**: The article title from Bing News includes the publisher name as a suffix (e.g., "Article Title - CNN"). Split on ` - ` to extract publisher name. Domain extracted from the real URL via `urllib.parse.urlparse`.
- **Freshness**: 30-day window. Niche B2B keywords don't generate daily news.
- **Scoring**: Freshness (7d=+20, 30d=+12, 90d=+6) + publisher authority (+15 for major, +5 for niche). `is_hot` threshold = 30 within Bing News scorer.

### Google News RSS (DEPRECATED — do not use)
- **Problem**: `news.google.com/rss/articles/CBMi...` → HTTP 400, completely broken
- **Old workaround**: Extract publisher domain, construct Google search URL — but this produces a SEARCH PAGE, not the article itself. User clicks and sees search results, not the article.
- **Replaced by**: Bing News RSS which provides real article URLs directly.

### Google Trends
- **Problem**: `trends.google.com/trends/explore?q=...` is a search dashboard
- **Solution**: Don't create hot_links. Only create trend_signals with `signal_type="search_volume"`.

### Reddit
- **Good URL format**: `reddit.com/r/{sub}/comments/{id}/title` — specific posts ✓
- **Problem**: RSS returns 0 upvote/comment counts AND returns random hot posts (not keyword-filtered)
- **Solution**: Use `old.reddit.com/r/{sub}/search.json` which returns real engagement metrics and correct search results. If JSON API returns 403, **skip entirely** — do NOT fall back to RSS.
- **Future**: Use Reddit OAuth (PRAW) for reliable access.

### YouTube (no API key needed)
- **Method**: Parse `ytInitialData` JSON from search results page HTML
- **URL format**: `youtube.com/watch?v={videoId}` — specific videos ✓
- **Data extracted**: videoId, title, view count, channel name, published date
- **Search URL**: `youtube.com/results?search_query={keyword}&sp=CAMSAhAB` (sort by view count)
- **JSON extraction**: `re.search(r"ytInitialData\s*=\s*(\{.+?})\s*;?\s*</script>", resp.text, re.DOTALL)`
- **Scoring**: 10K views = 10 pts, 100K = 20 pts, 500K+ = 30 pts. Known tech/review channels get +10 bonus.
- **No quota limits** — no API key needed at all.

### TikTok (script ready, needs stealth/proxy infrastructure)
- **Method**: Playwright headless browser loads search page, waits for video card selectors
- **URL format**: `tiktok.com/@{author}/video/{videoId}` — specific videos ✓
- **Problem**: TikTok anti-bot detects headless Playwright, `wait_for_selector` times out
- **Fix needed**: Install `playwright-stealth` or use residential proxies (e.g., Browserbase)
- **Alternative**: Use `TikTokApi` Python library (github: `davidteather/TikTok-Api`, 6,483 stars)

### Amazon
- **Good**: Playwright scraper returns `amazon.com/dp/{ASIN}` — specific products ✓
- **Problem**: Often blocked by anti-scraping
- **Disabled by default** in `crawl_config.yaml`
