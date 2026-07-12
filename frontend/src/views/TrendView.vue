<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { apiRequest, type Identity } from '../api'
import type { CategorySummary, HotLink, TrendSignal } from '../types'

const props = defineProps<{ identity: Identity }>()
const emit = defineEmits<{ select: [code: string] }>()

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
  const labels: Record<string, string> = { google: 'Google', reddit: 'Reddit', youtube: 'YouTube', tiktok: 'TikTok', news: 'News', other: 'Other' }
  return labels[p] || p
}

// 关键词条形图数据 — 按品类分组
const keywordByCategory = computed(() => {
  const result: { category: string; keywords: { keyword: string; value: number }[] }[] = []
  const topCats = categories.value.filter(c => !c.parent_code)
  for (const cat of topCats) {
    const kts = allTrends.value.filter(t => t.category_code === cat.code && t.signal_type === 'keyword_trend' && t.metric_value && t.metric_value > 0)
    const keywords = kts.map(t => ({ keyword: t.keyword, value: t.metric_value })).sort((a, b) => b.value - a.value).slice(0, 5)
    result.push({ category: cat.name, keywords })
  }
  return result.filter(r => r.keywords.length > 0)
})

// 平台分布饼图数据
const platformDist = computed(() => {
  const counts: Record<string, number> = {}
  for (const link of allHotLinks.value) {
    counts[link.platform] = (counts[link.platform] || 0) + 1
  }
  return Object.entries(counts).map(([platform, count]) => ({ name: platformLabel(platform), value: count }))
})

// 关键词排行榜
const keywordRanking = computed(() => {
  const kts = allTrends.value.filter(t => t.signal_type === 'keyword_trend' && t.keyword)
  const seen = new Set<string>()
  const result: { keyword: string; category: string }[] = []
  for (const t of kts) {
    if (t.keyword && !seen.has(t.keyword)) {
      seen.add(t.keyword)
      result.push({ keyword: t.keyword, category: categoryName(t.category_code || '') })
    }
  }
  return result.slice(0, 15)
})

// 品类热点数横向条形图
const categoryHotLinks = computed(() => {
  const topCats = categories.value.filter(c => !c.parent_code)
  return topCats.map(cat => {
    // 统计该品类及其子品类的热点数
    const childCodes = categories.value.filter(c => c.parent_code === cat.code).map(c => c.code)
    const allCodes = [cat.code, ...childCodes]
    const count = allHotLinks.value.filter(l => allCodes.includes(l.category_code || '')).length
    return { name: cat.name, value: count }
  }).sort((a, b) => b.value - a.value)
})

async function loadData() {
  loading.value = true
  try {
    const catResult = await apiRequest<{ items: CategorySummary[] }>('/categories')
    categories.value = catResult.items
    const codes = catResult.items.map(c => c.code)
    const results = await Promise.all(codes.map(async (code) => {
      try {
        const [hl, ts] = await Promise.all([
          apiRequest<{ items: HotLink[] }>(`/categories/${code}/hot-links?days=7`),
          apiRequest<{ items: TrendSignal[] }>(`/categories/${code}/trend-signals?days=7`),
        ])
        return { hotLinks: hl.items, trends: ts.items }
      } catch { return { hotLinks: [] as HotLink[], trends: [] as TrendSignal[] } }
    }))
    allHotLinks.value = results.flatMap(r => r.hotLinks)
    allTrends.value = results.flatMap(r => r.trends)
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  const echarts = (window as any).echarts
  if (!echarts) return

  // 1. 平台分布饼图
  const pieEl = document.getElementById('platform-pie')
  if (pieEl && platformDist.value.length) {
    const chart = echarts.init(pieEl)
    chart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0, textStyle: { fontSize: 12, color: '#666' } },
      series: [{
        type: 'pie', radius: ['45%', '72%'], center: ['50%', '45%'],
        label: { show: false }, labelLine: { show: false },
        data: platformDist.value.map(d => ({ name: d.name, value: d.value })),
        color: ['#2f6f55', '#5b8c7a', '#8cb4a3', '#b5d3c5', '#d9e8de'],
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
      }],
    })
  }

  // 2. 品类热点数横向条形图
  const barEl = document.getElementById('category-bar')
  if (barEl && categoryHotLinks.value.length) {
    const chart = echarts.init(barEl)
    const maxVal = Math.max(...categoryHotLinks.value.map(d => d.value)) || 1
    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 110, right: 40, top: 10, bottom: 10 },
      xAxis: { type: 'value', max: maxVal * 1.3, splitLine: { lineStyle: { color: '#f0f0f0' } }, axisLabel: { color: '#999' } },
      yAxis: { type: 'category', data: categoryHotLinks.value.map(d => d.name), axisLabel: { fontSize: 12, color: '#666' } },
      series: [{
        type: 'bar', barWidth: 14, data: categoryHotLinks.value.map(d => d.value),
        itemStyle: { color: '#2f6f55', borderRadius: [0, 3, 3, 0] },
        label: { show: true, position: 'right', fontSize: 12, color: '#999' },
      }],
    })
  }

  // 3. 关键词搜索量条形图
  const kwBarEl = document.getElementById('keyword-bar')
  if (kwBarEl && keywordByCategory.value.length) {
    const chart = echarts.init(kwBarEl)
    const allKeywords = keywordByCategory.value.flatMap(g => g.keywords.map(k => k.keyword))
    const maxVal = Math.max(...keywordByCategory.value.flatMap(g => g.keywords.map(k => k.value))) || 1
    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { top: 0, textStyle: { fontSize: 11, color: '#666' } },
      grid: { left: 110, right: 50, top: 30, bottom: 10 },
      xAxis: { type: 'value', max: maxVal * 1.3, splitLine: { lineStyle: { color: '#f0f0f0' } }, axisLabel: { color: '#999', formatter: '{value}' } },
      yAxis: { type: 'category', data: allKeywords, axisLabel: { fontSize: 11, color: '#666' } },
      series: keywordByCategory.value.map(g => ({
        name: g.category, type: 'bar', barWidth: 10,
        data: allKeywords.map(kw => g.keywords.find(k => k.keyword === kw)?.value || 0),
        itemStyle: { borderRadius: [0, 2, 2, 0] },
      })),
      color: ['#2f6f55', '#3b7ea1', '#b8860b', '#8b5a8c', '#c0704b'],
    })
  }
}

watch(loading, (isLoading) => {
  if (!isLoading) nextTick(() => setTimeout(renderCharts, 200))
})

onMounted(loadData)
</script>

<template>
  <main v-loading="loading" class="dashboard-page">
    <!-- 图表区域 -->
    <div class="trend-charts-grid">
      <!-- 平台分布饼图 -->
      <div class="trend-chart-card">
        <h3>📊 热点平台分布</h3>
        <div id="platform-pie" class="chart-container"></div>
      </div>

      <!-- 品类热点数条形图 -->
      <div class="trend-chart-card">
        <h3>🔥 各品类热点数量</h3>
        <div id="category-bar" class="chart-container"></div>
      </div>
    </div>

    <!-- 关键词搜索量条形图 -->
    <div class="trend-chart-card" style="margin-bottom: 16px">
      <h3>🔑 Google 关键词搜索量（按品类）</h3>
      <div id="keyword-bar" class="chart-container-wide"></div>
    </div>

    <!-- 关键词排行榜 -->
    <div class="trend-chart-card">
      <h3>📋 关键词排行榜 Top {{ keywordRanking.length }}</h3>
      <div class="kw-ranking-list">
        <div v-for="(kw, i) in keywordRanking" :key="i" class="kw-rank-row" @click="emit('select', categories.find(c => c.name === kw.category)?.code || '')">
          <span class="kw-rank-num" :class="{ 'top-3': i < 3 }">{{ i + 1 }}</span>
          <span class="kw-rank-text">{{ kw.keyword }}</span>
          <span class="kw-rank-cat">{{ kw.category }}</span>
        </div>
      </div>
    </div>
  </main>
</template>
