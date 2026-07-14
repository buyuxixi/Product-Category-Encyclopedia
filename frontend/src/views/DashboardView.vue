<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { apiRequest, type Identity } from '../api'
import type { CategorySummary, HotLink, TrendSignal } from '../types'

const props = defineProps<{ identity: Identity }>()
const emit = defineEmits<{ select: [code: string]; browse: [] }>()

/** 总览首屏最多展示的品类数；超过后显示「查看全部」 */
const CAT_PREVIEW_LIMIT = 12

const loading = ref(false)
const categories = ref<CategorySummary[]>([])
const allHotLinks = ref<HotLink[]>([])
const allTrends = ref<TrendSignal[]>([])

const categoryNameMap = computed(() => {
  const map: Record<string, string> = {}
  for (const c of categories.value) map[c.code] = c.name
  return map
})

function categoryName(code: string): string { return categoryNameMap.value[code] || code }

function platformLabel(p: string): string {
  const labels: Record<string, string> = { google: 'Google', reddit: 'Reddit', youtube: 'YouTube', tiktok: 'TikTok', xiaohongshu: '小红书', news: 'News', amazon: 'Amazon', other: 'Other' }
  return labels[p] || p
}

function cleanTitle(title: string): string {
  return (title || '').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
}

function hotLinkTitle(link: HotLink): string {
  return cleanTitle(link.title_zh?.trim() || link.title)
}

// 品类数据行
interface CategoryRow {
  code: string; name: string; health: string;
  hotLinks: number; trends: number; sources: number; filled: number; total: number;
  updated: string | null;
  parentCode: string | null;
  parentName: string | null;
}
const categoryRows = ref<CategoryRow[]>([])

function healthLabel(h: string) { return h === 'good' ? '健康' : h === 'fair' ? '一般' : '待更新' }
function healthType(h: string) { return h === 'good' ? 'success' : h === 'fair' ? 'warning' : 'info' }
function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return '—'
  const hours = (Date.now() - new Date(dateStr).getTime()) / 3600000
  if (hours < 1) return `${Math.floor(hours * 60)}分钟前`
  if (hours < 24) return `${Math.floor(hours)}小时前`
  return `${Math.floor(hours / 24)}天前`
}

function selectCategory(code: string) { emit('select', code) }
function browseAllCategories() { emit('browse') }

function activityScore(row: CategoryRow) {
  return row.hotLinks * 2 + row.trends + row.sources
}

/** 一级按活跃度排序，其子品类紧跟在父品类后 */
const sortedCategoryRows = computed(() => {
  const tops = categoryRows.value.filter(r => !r.parentCode).sort((a, b) => activityScore(b) - activityScore(a))
  const result: CategoryRow[] = []
  for (const top of tops) {
    result.push(top)
    const children = categoryRows.value
      .filter(r => r.parentCode === top.code)
      .sort((a, b) => activityScore(b) - activityScore(a))
    result.push(...children)
  }
  return result
})
const visibleCategoryRows = computed(() => sortedCategoryRows.value.slice(0, CAT_PREVIEW_LIMIT))
const hasMoreCategories = computed(() => categoryRows.value.length > CAT_PREVIEW_LIMIT)
const hiddenCategoryCount = computed(() => Math.max(0, categoryRows.value.length - CAT_PREVIEW_LIMIT))
const topCategoryCount = computed(() => categoryRows.value.filter(r => !r.parentCode).length)
const childCategoryCount = computed(() => categoryRows.value.filter(r => r.parentCode).length)

// 最新视频 Top 3
const latestVideos = computed(() =>
  allHotLinks.value
    .filter(l => l.platform === 'youtube' && l.hotness_score && l.hotness_score > 0)
    .sort((a, b) => (b.hotness_score || 0) - (a.hotness_score || 0))
    .slice(0, 3)
)

// 最新社区讨论 Top 3（Reddit + 小红书）
const latestReddit = computed(() =>
  allHotLinks.value
    .filter(l => l.platform === 'reddit' || l.platform === 'xiaohongshu' || l.link_type === 'social_post')
    .sort((a, b) => (b.hotness_score || 0) - (a.hotness_score || 0))
    .slice(0, 3)
)

// Top 搜索词
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
  return result.slice(0, 12)
})

// 平台分布
const platformDist = computed(() => {
  const counts: Record<string, number> = {}
  for (const link of allHotLinks.value) {
    counts[link.platform] = (counts[link.platform] || 0) + 1
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([platform, count]) => ({ name: platformLabel(platform), value: count }))
})

async function loadDashboard() {
  loading.value = true
  categoryRows.value = []
  allHotLinks.value = []
  allTrends.value = []
  try {
    const catResult = await apiRequest<{ items: CategorySummary[] }>('/categories')
    const topCats = catResult.items.filter(c => !c.parent_code)
    categories.value = catResult.items
    const codes = topCats.map(c => c.code)
    // 也请求子品类数据用于聚合
    const childCodes = catResult.items.filter(c => c.parent_code).map(c => c.code)
    const allCodes = [...codes, ...childCodes]
    const results = await Promise.all(allCodes.map(async (code) => {
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
      // 跳过子品类：父品类卡片做聚合，子品类单独追加
      const meta = catResult.items.find(c => c.code === r.code)
      if (!meta || meta.parent_code) continue
      const cat = topCats.find(c => c.code === r.code)
      const childMetas = catResult.items.filter(c => c.parent_code === r.code)
      // 聚合子品类数据到一级品类
      for (const childMeta of childMetas) {
        const childResult = results.find(res => res.code === childMeta.code)
        if (childResult) {
          r.stats.hotLinks += childResult.stats.hotLinks
          r.stats.trends += childResult.stats.trends
          r.stats.sources += childResult.stats.sources
          if (childResult.stats.updated && (!r.stats.updated || childResult.stats.updated > r.stats.updated)) {
            r.stats.updated = childResult.stats.updated
          }
          r.hotLinks.push(...childResult.hotLinks)
          r.trends.push(...childResult.trends)
        }
      }
      const health = r.stats.updated ? (Date.now() - new Date(r.stats.updated).getTime() < 86400000 ? 'good' : 'fair') : 'poor'
      categoryRows.value.push({
        code: r.code, name: cat?.name || r.code, health,
        hotLinks: r.stats.hotLinks, trends: r.stats.trends, sources: r.stats.sources,
        filled: r.stats.filled, total: r.stats.sections,
        updated: r.stats.updated,
        parentCode: null, parentName: null,
      })
      // 给 hot_links 加上 category_code（聚合列表用父 code，便于下方动态区归类）
      for (const hl of r.hotLinks) { (hl as any).category_code = r.code }
      allHotLinks.value.push(...r.hotLinks)
      allTrends.value.push(...r.trends)

      // 子品类独立卡片（用自身统计，不二次聚合）
      for (const childMeta of childMetas) {
        const childResult = results.find(res => res.code === childMeta.code)
        if (!childResult) continue
        const childHealth = childResult.stats.updated
          ? (Date.now() - new Date(childResult.stats.updated).getTime() < 86400000 ? 'good' : 'fair')
          : 'poor'
        categoryRows.value.push({
          code: childMeta.code,
          name: childMeta.name,
          health: childHealth,
          hotLinks: childResult.stats.hotLinks,
          trends: childResult.stats.trends,
          sources: childResult.stats.sources,
          filled: childResult.stats.filled,
          total: childResult.stats.sections,
          updated: childResult.stats.updated,
          parentCode: r.code,
          parentName: cat?.name || r.code,
        })
      }
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

function renderMiniCharts() {
  const echarts = (window as any).echarts
  if (!echarts) return
  for (const row of visibleCategoryRows.value) {
    const el = document.getElementById(`chart-${row.code}`)
    if (!el || !(window as any).echarts) continue
    const chart = echarts.init(el)
    const total = row.hotLinks + row.trends + row.sources
    if (total === 0) {
      chart.setOption({ graphic: { type: 'text', style: { text: '无数据', fontSize: 12, fill: '#ccc' }, left: 'center', top: 'center' } })
      continue
    }
    chart.setOption({
      series: [{
        type: 'pie', radius: ['55%', '80%'], center: ['50%', '50%'],
        silent: true, label: { show: false }, labelLine: { show: false },
        data: [
          { value: row.hotLinks, name: '热点', itemStyle: { color: '#2f6f55' } },
          { value: row.trends, name: '趋势', itemStyle: { color: '#8cb4a3' } },
          { value: row.sources, name: '来源', itemStyle: { color: '#d9e8de' } },
        ],
      }],
    })
  }
}

watch(loading, (isLoading) => {
  if (!isLoading) nextTick(() => setTimeout(renderMiniCharts, 100))
})

onMounted(loadDashboard)
</script>

<template>
  <main v-loading="loading" class="dashboard-page">
    <!-- 品类卡片墙：一级 + 子品类；子卡紧跟父卡 -->
    <section class="cat-section">
      <div class="panel-header">
        <h2>品类概览</h2>
        <span class="panel-hint">
          {{ topCategoryCount }} 个一级
          <template v-if="childCategoryCount"> · {{ childCategoryCount }} 个子品类</template>
        </span>
      </div>
      <div class="cat-grid">
        <div
          v-for="row in visibleCategoryRows"
          :key="row.code"
          class="cat-card"
          :class="[`health-${row.health}`, { 'is-child': !!row.parentCode }]"
          @click="selectCategory(row.code)"
        >
          <div class="cat-card-header">
            <div class="cat-card-title">
              <span v-if="row.parentName" class="cat-card-parent">{{ row.parentName }}</span>
              <span class="cat-card-name">{{ row.name }}</span>
            </div>
            <el-tag :type="healthType(row.health)" size="small" effect="plain">{{ healthLabel(row.health) }}</el-tag>
          </div>
          <div class="cat-card-body">
            <div :id="`chart-${row.code}`" class="cat-mini-chart"></div>
            <div class="cat-card-stats">
              <div class="cat-stat"><span class="cat-stat-num">{{ row.hotLinks }}</span><span class="cat-stat-label">热点</span></div>
              <div class="cat-stat"><span class="cat-stat-num">{{ row.trends }}</span><span class="cat-stat-label">趋势</span></div>
              <div class="cat-stat"><span class="cat-stat-num">{{ row.sources }}</span><span class="cat-stat-label">来源</span></div>
            </div>
          </div>
          <div class="cat-card-footer">
            <span>{{ formatRelativeTime(row.updated) }}</span>
            <span class="cat-card-arrow">→</span>
          </div>
        </div>
      </div>
      <button v-if="hasMoreCategories" type="button" class="cat-view-all" @click="browseAllCategories">
        查看全部 {{ categoryRows.length }} 个品类（还有 {{ hiddenCategoryCount }} 个）→
      </button>
    </section>

    <!-- 三列最新动态 — 精选，不重复06章节的完整列表 -->
    <section class="latest-grid">
      <!-- 最新视频 -->
      <div class="latest-panel">
        <div class="panel-header">
          <h2>📺 最新视频</h2>
          <span class="panel-hint">热度 Top 3</span>
        </div>
        <div v-if="latestVideos.length" class="hot-list">
          <a v-for="link in latestVideos" :key="link.id" :href="link.url" target="_blank" rel="noreferrer noopener" class="hot-row">
            <div class="hot-row-main">
              <div class="hot-row-title">{{ hotLinkTitle(link) }}</div>
              <div class="hot-row-meta">
                <el-tag size="small" effect="plain">YouTube</el-tag>
                <span class="hot-row-cat" v-if="categoryName(link.category_code || '')">{{ categoryName(link.category_code || '') }}</span>
                <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
              </div>
            </div>
          </a>
        </div>
        <el-empty v-else description="暂无视频" :image-size="50" />
      </div>

      <!-- 最新讨论 -->
      <div class="latest-panel">
        <div class="panel-header">
          <h2>💬 热门讨论</h2>
          <span class="panel-hint">社区 Top 3</span>
        </div>
        <div v-if="latestReddit.length" class="hot-list">
          <a v-for="link in latestReddit" :key="link.id" :href="link.url" target="_blank" rel="noreferrer noopener" class="hot-row">
            <div class="hot-row-main">
              <div class="hot-row-title">{{ hotLinkTitle(link) }}</div>
              <div class="hot-row-meta">
                <el-tag size="small" effect="plain">{{ platformLabel(link.platform) }}</el-tag>
                <span class="hot-row-cat" v-if="categoryName(link.category_code || '')">{{ categoryName(link.category_code || '') }}</span>
                <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
              </div>
            </div>
          </a>
        </div>
        <el-empty v-else description="暂无讨论" :image-size="50" />
      </div>

      <!-- 搜索趋势词 -->
      <div class="latest-panel">
        <div class="panel-header">
          <h2>🔑 搜索趋势词</h2>
          <span class="panel-hint">Google Top 12</span>
        </div>
        <div v-if="topKeywords.length" class="kw-tag-list">
          <span v-for="(kw, i) in topKeywords" :key="i" class="kw-tag" @click="selectCategory(categories.find(c => c.name === kw.category)?.code || '')">
            {{ kw.keyword }}<small>{{ kw.category }}</small>
          </span>
        </div>
        <el-empty v-else description="暂无关键词" :image-size="50" />
      </div>
    </section>

    <!-- 平台分布概览 -->
    <section class="platform-overview">
      <div class="panel-header">
        <h2>📡 数据来源分布</h2>
        <span class="panel-hint">{{ allHotLinks.length }} 条总数据</span>
      </div>
      <div class="platform-bars">
        <div v-for="p in platformDist" :key="p.name" class="platform-bar">
          <span class="platform-name">{{ p.name }}</span>
          <div class="platform-bar-track">
            <div class="platform-bar-fill" :style="{ width: `${(p.value / Math.max(...platformDist.map(d => d.value)) * 100)}%` }"></div>
          </div>
          <span class="platform-count">{{ p.value }}</span>
        </div>
      </div>
    </section>
  </main>
</template>
