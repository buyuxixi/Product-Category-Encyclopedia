<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { apiRequest, type Identity } from '../api'
import type { CategorySummary, HotLink, TrendSignal } from '../types'

const props = defineProps<{ identity: Identity }>()
const emit = defineEmits<{ select: [code: string] }>()

const loading = ref(false)
const categories = ref<CategorySummary[]>([])
const allHotLinks = ref<HotLink[]>([])
const allTrends = ref<TrendSignal[]>([])
const perCategoryStats = ref<Record<string, { hotLinks: number; trends: number; sources: number; sections: number; filled: number; updated: string | null }>>({})

interface CategoryRow {
  code: string
  name: string
  hotLinks: number
  trends: number
  sources: number
  filled: number
  total: number
  updated: string | null
  health: 'good' | 'fair' | 'poor'
}

const categoryRows = computed<CategoryRow[]>(() => {
  return categories.value
    .filter(c => !c.parent_code)
    .map(c => {
      const stats = perCategoryStats.value[c.code] || { hotLinks: 0, trends: 0, sources: 0, sections: 0, filled: 0, updated: null }
      const children = categories.value.filter(ch => ch.parent_code === c.code)
      const childStats = children.map(ch => perCategoryStats.value[ch.code] || { hotLinks: 0, trends: 0, sources: 0, sections: 0, filled: 0, updated: null })
      const totalHot = stats.hotLinks + childStats.reduce((s, v) => s + v.hotLinks, 0)
      const totalTrends = stats.trends + childStats.reduce((s, v) => s + v.trends, 0)
      const totalSources = stats.sources + childStats.reduce((s, v) => s + v.sources, 0)
      const totalFilled = stats.filled + childStats.reduce((s, v) => s + v.filled, 0)
      const totalSections = stats.sections + childStats.reduce((s, v) => s + v.sections, 0)
      const latestUpdate = [stats.updated, ...childStats.map(v => v.updated)].filter(Boolean).sort().pop() || null
      const health: 'good' | 'fair' | 'poor' = totalHot >= 5 && totalFilled >= 6 ? 'good' : totalHot > 0 ? 'fair' : 'poor'
      return { code: c.code, name: c.name, hotLinks: totalHot, trends: totalTrends, sources: totalSources, filled: totalFilled, total: totalSections, updated: latestUpdate, health }
    })
})

const topHotLinks = computed(() =>
  [...allHotLinks.value]
    .sort((a, b) => (b.hotness_score || 0) - (a.hotness_score || 0))
    .slice(0, 10)
)

// Reddit 讨论精选 — 只显示 Reddit 平台
const topRedditPosts = computed(() =>
  allHotLinks.value
    .filter(l => l.platform === 'reddit')
    .sort((a, b) => (b.hotness_score || 0) - (a.hotness_score || 0))
    .slice(0, 10)
)

// Amazon 选品榜单 — 只显示 Amazon 产品
const topAmazonProducts = computed(() =>
  allHotLinks.value
    .filter(l => l.platform === 'amazon')
    .slice(0, 10)
)

// 数据更新日志 — 按更新时间排序
const updateLog = computed(() => {
  return categoryRows.value
    .filter(r => r.updated)
    .sort((a, b) => new Date(b.updated!).getTime() - new Date(a.updated!).getTime())
    .map(r => ({ code: r.code, name: r.name, updated: r.updated }))
    .slice(0, 5)
})

const categoryNameMap = computed(() => {
  const map: Record<string, string> = {}
  for (const c of categories.value) map[c.code] = c.name
  return map
})

function categoryName(code: string): string { return categoryNameMap.value[code] || code }

const topKeywords = computed(() => {
  const kts = allTrends.value.filter(t => t.signal_type === 'keyword_trend' && t.keyword)
  const seen = new Set<string>()
  const result: { keyword: string; category: string }[] = []
  for (const t of kts) {
    if (t.keyword && !seen.has(t.keyword)) {
      seen.add(t.keyword)
      result.push({ keyword: t.keyword, category: categoryName(t.category_code || '') })
    }
  }
  return result.slice(0, 20)
})

function healthLabel(h: string) { return h === 'good' ? '健康' : h === 'fair' ? '一般' : '待更新' }
function healthType(h: string) { return h === 'good' ? 'success' : h === 'fair' ? 'warning' : 'info' }

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return '—'
  const hours = (Date.now() - new Date(dateStr).getTime()) / 3600000
  if (hours < 1) return `${Math.floor(hours * 60)}分钟前`
  if (hours < 24) return `${Math.floor(hours)}小时前`
  return `${Math.floor(hours / 24)}天前`
}

function platformLabel(p: string): string {
  const labels: Record<string, string> = { google: 'Google', reddit: 'Reddit', youtube: 'YouTube', tiktok: 'TikTok', news: 'News', other: 'Other' }
  return labels[p] || p
}

function selectCategory(code: string) { emit('select', code) }

async function loadDashboard() {
  loading.value = true
  try {
    const catResult = await apiRequest<{ items: CategorySummary[] }>('/categories')
    categories.value = catResult.items
    const codes = catResult.items.map(c => c.code)
    const results = await Promise.all(codes.map(async (code) => {
      try {
        const [cat, hl, ts] = await Promise.all([
          apiRequest<{ sections: Array<{ content: string }> } & { source_count: number }>(`/categories/${code}`),
          apiRequest<{ items: HotLink[] }>(`/categories/${code}/hot-links?days=7`),
          apiRequest<{ items: TrendSignal[] }>(`/categories/${code}/trend-signals?days=7`),
        ])
        const sections = cat.sections || []
        const filled = sections.filter((s: { content: string }) => s.content?.trim()).length
        const latestHl = hl.items.length ? hl.items[0].collected_at : null
        const latestTs = ts.items.length ? ts.items[0].collected_at : null
        const latest = [latestHl, latestTs].filter(Boolean).sort().pop() || null
        return { code, stats: { hotLinks: hl.items.length, trends: ts.items.length, sources: cat.source_count || 0, sections: sections.length, filled, updated: latest }, hotLinks: hl.items, trends: ts.items }
      } catch {
        return { code, stats: { hotLinks: 0, trends: 0, sources: 0, sections: 0, filled: 0, updated: null }, hotLinks: [] as HotLink[], trends: [] as TrendSignal[] }
      }
    }))
    for (const r of results) {
      perCategoryStats.value[r.code] = r.stats
      allHotLinks.value.push(...r.hotLinks)
      allTrends.value.push(...r.trends)
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)

// 渲染迷你环形图
function renderMiniCharts() {
  for (const row of categoryRows.value) {
    const el = document.getElementById(`chart-${row.code}`)
    if (!el || !(window as any).echarts) continue
    const chart = (window as any).echarts.init(el)
    const total = row.hotLinks + row.trends + row.sources
    if (total === 0) {
      chart.setOption({ graphic: { type: 'text', style: { text: '无数据', fontSize: 12, fill: '#ccc' }, left: 'center', top: 'center' } })
      continue
    }
    chart.setOption({
      series: [{
        type: 'pie',
        radius: ['55%', '80%'],
        center: ['50%', '50%'],
        silent: true,
        label: { show: false },
        labelLine: { show: false },
        data: [
          { value: row.hotLinks, name: '热点', itemStyle: { color: '#8cb4a3' } },
          { value: row.trends, name: '趋势', itemStyle: { color: '#b5d3c5' } },
          { value: row.sources, name: '来源', itemStyle: { color: '#d9e8de' } },
        ],
      }],
    })
  }
}

// 数据加载完后渲染图表
watch([loading, categoryRows], ([isLoading]) => {
  if (!isLoading) {
    setTimeout(renderMiniCharts, 100)
  }
}, { onTrigger: () => {} })
</script>

<template>
  <main v-loading="loading" class="dashboard-page">
    <!-- 品类卡片墙 — 每个品类一张紧凑卡片，含迷你环形图 -->
    <section class="cat-grid">
      <div
        v-for="row in categoryRows"
        :key="row.code"
        class="cat-card"
        :class="`health-${row.health}`"
        @click="selectCategory(row.code)"
      >
        <div class="cat-card-header">
          <span class="cat-card-name">{{ row.name }}</span>
          <el-tag :type="healthType(row.health)" size="small" effect="plain">{{ healthLabel(row.health) }}</el-tag>
        </div>
        <div class="cat-card-body">
          <div :id="`chart-${row.code}`" class="cat-mini-chart"></div>
          <div class="cat-card-stats">
            <div class="cat-stat"><span class="cat-stat-num">{{ row.hotLinks }}</span><span class="cat-stat-label">🔥 热点</span></div>
            <div class="cat-stat"><span class="cat-stat-num">{{ row.trends }}</span><span class="cat-stat-label">📊 趋势</span></div>
            <div class="cat-stat"><span class="cat-stat-num">{{ row.sources }}</span><span class="cat-stat-label">📎 来源</span></div>
          </div>
        </div>
        <div class="cat-card-footer">
          <span>{{ formatRelativeTime(row.updated) }}</span>
          <span class="cat-card-arrow">→</span>
        </div>
      </div>
    </section>

    <!-- 数据更新日志 — 紧凑时间条 -->
    <section v-if="updateLog.length" class="update-log">
      <span class="update-log-label">🔄 最近更新</span>
      <span v-for="item in updateLog" :key="item.code" class="update-log-item" @click="selectCategory(item.code)">
        {{ item.name }} <small>{{ formatRelativeTime(item.updated) }}</small>
      </span>
    </section>

    <!-- Reddit 讨论 + Amazon 选品 并排 -->
    <section class="bottom-split">
      <!-- 左：Reddit 讨论精选 -->
      <div class="hot-panel">
        <div class="panel-header">
          <h2>💬 社区讨论精选</h2>
          <span class="panel-hint">Reddit 真实用户讨论</span>
        </div>
        <div v-if="topRedditPosts.length" class="hot-list">
          <a
            v-for="link in topRedditPosts"
            :key="link.id"
            :href="link.url"
            target="_blank"
            rel="noreferrer noopener"
            class="hot-row"
            :class="{ 'is-hot': link.is_hot }"
          >
            <div class="hot-row-main">
              <div class="hot-row-title">{{ link.title.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'") }}</div>
              <div class="hot-row-meta">
                <el-tag size="small" effect="plain">{{ platformLabel(link.platform) }}</el-tag>
                <span class="hot-row-cat" v-if="categoryName(link.category_code)">{{ categoryName(link.category_code) }}</span>
                <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
              </div>
            </div>
            <span class="hot-row-time">{{ formatRelativeTime(link.collected_at) }}</span>
          </a>
        </div>
        <el-empty v-else description="暂无 Reddit 讨论数据" :image-size="60" />
      </div>

      <!-- 右：Amazon 选品榜单 -->
      <div class="kw-panel">
        <div class="panel-header">
          <h2>🛒 Amazon 选品榜单</h2>
          <span class="panel-hint">搜索排名 Top 产品</span>
        </div>
        <div v-if="topAmazonProducts.length" class="hot-list">
          <a
            v-for="link in topAmazonProducts"
            :key="link.id"
            :href="link.url"
            target="_blank"
            rel="noreferrer noopener"
            class="hot-row"
          >
            <div class="hot-row-main">
              <div class="hot-row-title">{{ link.title.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'") }}</div>
              <div class="hot-row-meta">
                <el-tag size="small" effect="plain" type="success">Amazon</el-tag>
                <span class="hot-row-cat" v-if="categoryName(link.category_code)">{{ categoryName(link.category_code) }}</span>
              </div>
            </div>
          </a>
        </div>
        <el-empty v-else description="暂无 Amazon 产品数据" :image-size="60" />
      </div>
    </section>
  </main>
</template>
