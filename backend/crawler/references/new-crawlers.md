# New Crawler Scripts (2026-07-12)

## crawl_amazon_bsr.py — Amazon Best Sellers Rank

Crawls Amazon search results pages (sorted by sales rank) to extract product data.

### What it extracts
- ASIN (10-char product ID)
- Product title
- Price, rating, review_count (often NOT available from search page HTML — Amazon loads these via JS)
- BSR rank (search result position)
- Product URL: `https://www.amazon.com/dp/{ASIN}`

### How it works
1. For each category, searches 2 keywords on `amazon.com/s?k={keyword}&s=salesrank`
2. Method 1: Extracts JSON from `<script type="application/json">` blocks
3. Method 2 (fallback): Regex `data-asin="([A-Z0-9]{10})"` + nearby HTML for title/price/rating
4. Skips sponsored products
5. 15-second interval between categories

### Data output
- **hot_links**: `link_type=product`, `platform=amazon`, `section_key=market`
- **trend_signals**: `signal_type=product_insight`, aggregating avg price / avg rating / total reviews per keyword

### Key success — prices/ratings/reviews ARE in server HTML (verified 2026-07-12)
Amazon's search results page DOES include prices, ratings, and review counts in server-rendered HTML — they're just located up to **12000 characters away** from the `data-asin` attribute. A 5000-char block misses them; a 12000-char block finds them.

**Extraction patterns (all verified working):**
- **Price:** `<span class="a-offscreen">JPY\xa03,230</span>` or `$29.99` → `re.search(r'class="a-offscreen"[^>]*>([^<]+)<', block)`
- **Rating:** `<span class="a-icon-alt">4.1 out of 5 stars</span>` → `re.search(r'class="a-icon-alt"[^>]*>(\d+\.?\d*)\s*out of\s*5', block, re.I)`
- **Review count:** `aria-label="12,720 ratings"` → `re.search(r'aria-label="([\d,]+)\s*(?:ratings?|reviews?)"', block, re.I)`
- **Sponsored filter:** Check `block[:1000]` for "Sponsored" — skip sponsored products

**JPY price conversion:** When proxy exits through Japanese IP (common with Clash/V2Ray in Asia), Amazon returns JPY format. Parse JPY and convert to USD at ~150 JPY/USD:
```python
text = text.replace('\xa0', ' ').strip()
m = re.search(r"JPY\s*([\d,]+)", text)
if m: return round(float(m.group(1).replace(",", "")) / 150, 2)
```

**Not all products have price/rating data** — some ASINs are bare cards (out-of-stock/restricted). Skip them silently. Filter in frontend: `l.description && !l.description.includes('$?') && !l.description.includes('0 reviews')` and limit to Top 20 to avoid overwhelming the user.

### Proxy configuration
Uses `httpx.Client(proxy='http://127.0.0.1:7897', verify=False)` — the `proxy=` parameter is more reliable than `HTTP_PROXY` env var on Python 3.13 (see Pitfall 57).

---

## crawl_youtube_comments.py — YouTube Comment Analysis

Fetches comments from YouTube videos via the innertube API and analyzes them for user pain points.

### What it does
1. Takes a list of YouTube hot_links (video URLs with video IDs)
2. For each video, fetches the watch page HTML to extract:
   - `INNERTUBE_API_KEY` (from embedded JSON)
   - Continuation tokens (from `token` fields with `comment` in surrounding context)
3. POSTs to `https://www.youtube.com/youtubei/v1/next?key={api_key}` with the continuation token
4. Recursively extracts comment text from the API response (in `content` string fields or `content.runs[].text`)
5. Analyzes comments:
   - **Sentiment**: positive/negative/mixed based on keyword counts
   - **Pain points**: matches against 40+ pain-point keywords (pain, hurt, disappointing, waste, cheap, love, amazing, etc.)
   - **Top words**: high-frequency words (excluding stop words)

### Token extraction — debugging methodology

YouTube watch pages contain 4-6 `token` fields. Only ONE is the comment continuation token. The debugging process:

1. Extract ALL tokens with context: `for m in re.finditer(r'"token":\s*"([^"]+)"', html)` — for each match, capture 300 chars before and after.
2. Filter by context: check if `comment` appears in the surrounding text (case-insensitive).
3. Tokens with `commentsHeaderRenderer` in context BEFORE the token = comment section header token.
4. Tokens with `comment-item-section` or `engagement-panel-comments-section` in context AFTER the token = comment section body token.
5. Use the LAST matching token (it's tied to `comment-item-section`).
6. If no comment-context tokens found, fall back to `all_tokens[1]` (second token — the first is usually a video recommendation token starting with `CBQ`).

**Failed approaches (don't retry):**
- `continuationItemRenderer.*token` regex — finds wrong tokens (video recommendations, not comments).
- `itemSectionContinuation.*continuation` regex — pattern doesn't match current YouTube HTML structure.
- First `token` field value — this is a video navigation token, returns 0 comments.

### Comment text extraction — debugging methodology

The API response (`/youtubei/v1/next`) is deeply nested (~140KB JSON). Comment text appears in two field patterns:

1. `"content": "actual comment text"` (string) — most common, found in `commentEntityPayload.content`
2. `"content": {"runs": [{"text": "part1"}, {"text": "part2"}]}` (dict) — for formatted text

The recursive extractor must check `isinstance(obj["content"], str)` vs `isinstance(obj["content"], dict)` separately. Filter to `len(text) > 10` to skip UI labels like "Show more replies" and short emoji-only replies.

**Failed approaches (don't retry):**
- `commentText` field key — does NOT exist in the current YouTube API response.
- `"text": "..."` field key — too broad, matches video descriptions, channel names, UI labels.
- `"content": "..."` only as string — misses dict-format content with `runs` arrays.

### Data output
- **trend_signals**: `signal_type=user_pain_point`, `section_key=users`, `platform=youtube`
  - `metric_value` = comment count
  - `trend_direction` = sentiment (positive/negative/mixed)
  - `summary` = "情感:{sentiment} | 痛点: {keywords} | 高频词: {top_words}"

### Proxy configuration
Uses `httpx.Client(proxy='http://127.0.0.1:7897', verify=False)` — same as Amazon BSR.

### Rate limiting
- 5-second interval between videos
- 2-second delay before API POST (politeness)
- Max 5 videos per category, max 50 comments per video
