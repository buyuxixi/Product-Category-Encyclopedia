# Cross-Section Distribution — REVISED 2026-07-11

## Final Design (user-confirmed)

Hot links and trend signals are **ONLY displayed in the market section** (06 舆情与市场趋势).
Sections 01-05 do NOT show any hot links or trend signals — no fallback, no empty state.

## Frontend Logic

```javascript
// EncyclopediaView.vue
const sectionHotLinks = computed(() =>
  activeSectionKey.value === 'market' ? hotLinks.value : []
)

const sectionTrendSignals = computed(() =>
  activeSectionKey.value === 'market'
    ? trendSignals.value.filter(s => {
        if (s.signal_type === 'keyword_trend') return true
        return s.metric_value !== null && s.metric_value !== undefined && s.metric_value > 0
      })
    : []
)
```

Summary stat cards (热点链接, 趋势信号) also only render on market section:
```html
<section v-if="activeSectionKey === 'market'" class="summary-strip">
```

## Crawler section_key Values

Even though only `market` section displays in the frontend, crawler scripts still assign `section_key` values for data organization:

| Source | section_key | Reason |
|--------|-------------|--------|
| YouTube | technology, users, needs, market | Rotating distribution for data diversity |
| Bing News | trends, needs, market | Rotating distribution |
| Reddit | users | Discussions are user-persona content |
| Google Suggest | market | Keyword trends belong in market |

The `section_key` in the DB is for future use (if the user decides to show section-specific hot links later). Currently, the frontend ignores `section_key` for display purposes — it shows ALL hot_links in the market section regardless of their `section_key` value.

## Market Timestamp Placement

The "数据采集时间" tag must appear at the TOP of the market section, above the hot links — not embedded in the markdown content body. The push script writes it as a blockquote in the section content, but the frontend extracts it and renders it as a separate styled bar:

```javascript
// Extract timestamp from content for top-of-section display
const marketTimestamp = computed(() => {
  if (activeSectionKey.value !== 'market') return null
  const match = activeSection.value.content.match(/数据采集时间[：:]\s*([\d\-/]+)/)
  return match ? match[1] : null
})

// Remove timestamp blockquote from rendered content to avoid duplication
const renderedContentWithoutTimestamp = computed(() => {
  if (!activeSection.value) return ''
  return activeSection.value.content
    .split('\n')
    .filter(line => !line.trim().startsWith('>') || !line.includes('数据采集时间'))
    .join('\n')
})
```

Template:
```html
<!-- Timestamp bar at top of market section -->
<div v-if="activeSectionKey === 'market' && marketTimestamp" class="market-timestamp">
  <span>⏰ 数据采集时间: {{ marketTimestamp }}</span>
</div>
```

CSS:
```css
.market-timestamp {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; margin-bottom: 12px;
  border-left: 3px solid var(--brand-green, #1e6650);
  background: var(--bg-subtle, #f5f7f5);
  border-radius: 0 6px 6px 0;
  font-size: 12px; color: var(--text-secondary);
}
```

The user explicitly said: "这个更新的标签是不是放到6的顶置会合理一些？" — the timestamp must be the FIRST thing visible in the market section, before hot links and trend signals.

## Top Stats Bar Must Match Displayed Count

The summary-strip stat cards must show the FILTERED count (what the user actually sees), not the raw API total. The user caught a mismatch: "如图热点链接我没看到有16个，下面我只看到有4个" — top said 16, only 4 visible.

```javascript
// CORRECT: use filteredHotLinks.length (after section + platform filtering)
<div class="stat-hot"><strong>{{ filteredHotLinks.length }}</strong><span>🔥 热点链接</span></div>
<div><strong>{{ sectionTrendSignals.length }}</strong><span>📊 趋势信号</span></div>

// WRONG: raw API total (causes mismatch)
// <strong>{{ hotLinks.length }}</strong>  ← shows 16 when only 4 are displayed
```

## History

- **v1 (initial)**: All hot_links had `section_key="market"` — only market section showed them
- **v2 (cross-section)**: Distributed hot_links across technology/users/needs/market — each section showed its own subset. User rejected: "为什么在其他模块也会出现热点链接？"
- **v3 (current)**: All hot_links shown in market section only. Other sections have no hot-links area. Stat cards only render on market section. Timestamp rendered as top-of-section bar. Top stats use filtered counts. This is the user-confirmed design.
