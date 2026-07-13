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
  const labels: Record<string, string> = { google: 'Google', reddit: 'Reddit', youtube: 'YouTube', tiktok: 'TikTok', xiaohongshu: '小红书', news: 'News', other: 'Other' }
  return labels[p] || p
}

// YouTube 播放量排行
const topVideos = computed(() => {
  return allHotLinks.value
    .filter(l => l.platform === 'youtube' && l.hotness_score && l.hotness_score > 0)
    .sort((a, b) => (b.hotness_score || 0) - (a.hotness_score || 0))
    .slice(0, 8)
})

// 用户搜索行为词 — 按品类分组
const keywordGroups = computed(() => {
  const topCats = categories.value.filter(c => !c.parent_code)
  return topCats.map(cat => {
    const childCodes = categories.value.filter(c => c.parent_code === cat.code).map(c => c.code)
    const allCodes = [cat.code, ...childCodes]
    const kts = allTrends.value.filter(t => allCodes.includes(t.category_code || '') && t.signal_type === 'keyword_trend' && t.keyword)
    const seen = new Set<string>()
    const keywords = kts
      .filter(t => {
        if (seen.has(t.keyword!)) return false
        seen.add(t.keyword!)
        return true
      })
      .map(t => ({ keyword: t.keyword!, isNew: t.trend_direction === 'new' }))
    return { category: cat.name, code: cat.code, keywords }
  }).filter(g => g.keywords.length > 0)
})

// 平台分布饼图数据
const platformDist = computed(() => {
  const counts: Record<string, number> = {}
  for (const link of allHotLinks.value) {
    counts[link.platform] = (counts[link.platform] || 0) + 1
  }
  return Object.entries(counts).map(([platform, count]) => ({ name: platformLabel(platform), value: count }))
})

// 品类热点数横向条形图
const categoryHotLinks = computed(() => {
  const topCats = categories.value.filter(c => !c.parent_code)
  return topCats.map(cat => {
    const childCodes = categories.value.filter(c => c.parent_code === cat.code).map(c => c.code)
    const allCodes = [cat.code, ...childCodes]
    const links = allHotLinks.value.filter(l => allCodes.includes(l.category_code || ''))
    // 按平台分组统计
    const byPlatform: Record<string, number> = {}
    for (const l of links) {
      byPlatform[l.platform] = (byPlatform[l.platform] || 0) + 1
    }
    return { name: cat.name, value: links.length, byPlatform }
  }).sort((a, b) => b.value - a.value)
})

// 平台×品类交叉统计 — 用于堆叠条形图
const stackedByPlatform = computed(() => {
  const topCats = categories.value.filter(c => !c.parent_code)
  const platforms = ['amazon', 'youtube', 'reddit', 'news']
  return {
    categories: topCats.map(c => c.name),
    series: platforms.map(p => ({
      name: platformLabel(p),
      type: 'bar',
      stack: 'total',
      data: topCats.map(cat => {
        const childCodes = categories.value.filter(c => c.parent_code === cat.code).map(c => c.code)
        const allCodes = [cat.code, ...childCodes]
        return allHotLinks.value.filter(l => allCodes.includes(l.category_code || '') && l.platform === p).length
      }),
    })),
  }
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
        color: ['#d4a017', '#5b8c7a', '#6b9bc4', '#9b8ab8'],  // Amazon=琥珀, YouTube=薄荷绿, Reddit=淡蓝, News=淡紫
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
      }],
    })
  }

  // 2. 品类×平台堆叠条形图
  const barEl = document.getElementById('category-bar')
  if (barEl && stackedByPlatform.value.categories.length) {
    const chart = echarts.init(barEl)
    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { top: 0, textStyle: { fontSize: 11, color: '#666' } },
      grid: { left: 110, right: 30, top: 30, bottom: 10 },
      xAxis: { type: 'value', splitLine: { lineStyle: { color: '#f0f0f0' } }, axisLabel: { color: '#999' } },
      yAxis: { type: 'category', data: stackedByPlatform.value.categories, axisLabel: { fontSize: 12, color: '#666' } },
      series: stackedByPlatform.value.series.map((s, i) => ({
        ...s,
        barWidth: 14,
        itemStyle: { borderRadius: [0, 2, 2, 0] },
      })),
      color: ['#d4a017', '#5b8c7a', '#6b9bc4', '#9b8ab8'],  // Amazon=琥珀, YouTube=薄荷绿, Reddit=淡蓝, News=淡紫
    })
  }

  // 3. 删除——关键词条形图无实际数据差异，改为列表展示
}

watch(loading, (isLoading) => {
  if (!isLoading) nextTick(() => setTimeout(renderCharts, 200))
})

onMounted(loadData)
</script>

<template>
  <main v-loading="loading" class="dashboard-page">
    <!-- 数据概览条 -->
    <div class="trend-overview-bar">
      <span class="trend-overview-item">📊 总热点: <strong>{{ allHotLinks.length }}</strong></span>
      <span class="trend-overview-item">📈 总趋势: <strong>{{ allTrends.length }}</strong></span>
      <span class="trend-overview-item">🏷️ 品类: <strong>{{ categories.filter(c => !c.parent_code).length }}</strong></span>
      <span class="trend-overview-item">📡 数据源: <strong>{{ platformDist.length }}</strong> 个平台</span>
    </div>

    <!-- 图表区域 -->
    <div class="trend-charts-grid">
      <!-- 平台分布饼图 -->
      <div class="trend-chart-card">
        <h3>📊 热点来源平台分布</h3>
        <div id="platform-pie" class="chart-container"></div>
      </div>

      <!-- 品类热点数条形图 -->
      <div class="trend-chart-card">
        <h3>🔥 各品类数据来源分布</h3>
        <div id="category-bar" class="chart-container"></div>
      </div>
    </div>

    <!-- YouTube 播放量排行 -->
    <div class="trend-chart-card" style="margin-bottom: 16px">
      <h3>📺 YouTube 视频热度 Top {{ topVideos.length }}</h3>
      <div class="video-rank-list">
        <a v-for="(v, i) in topVideos" :key="v.id" :href="v.url" target="_blank" rel="noreferrer" class="video-rank-row">
          <span class="video-rank-num" :class="{ 'top-3': i < 3 }">{{ i + 1 }}</span>
          <span class="video-rank-title">{{ v.title_zh?.trim() || v.title }}</span>
          <span class="video-rank-cat">{{ categoryName(v.category_code || '') }}</span>
          <span class="video-rank-views">👀 {{ v.hotness_score }}</span>
        </a>
      </div>
    </div>

    <!-- 用户搜索行为词 — 按品类分组 -->
    <div class="trend-chart-card">
      <h3>🔑 用户搜索行为词 <small style="font-weight: 400; color: var(--text-quaternary)">Google 真实用户搜索词，★ 标记为新词</small></h3>
      <div class="kw-grouped-list">
        <div v-for="group in keywordGroups" :key="group.category" class="kw-group">
          <div class="kw-group-header" @click="emit('select', group.code)">
            <span class="kw-group-name">{{ group.category }}</span>
            <span class="kw-group-count">{{ group.keywords.length }} 词</span>
          </div>
          <div class="kw-group-tags">
            <span v-for="kw in group.keywords" :key="kw.keyword" class="kw-tag" :class="{ 'is-new': kw.isNew }">
              {{ kw.keyword }}<span v-if="kw.isNew" class="kw-new-badge">★</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>
