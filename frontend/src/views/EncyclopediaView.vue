<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen, Refresh, View, CopyDocument, Download } from '@element-plus/icons-vue'
import { apiRequest, type Identity } from '../api'
import type {
  CategoryDetail,
  CategorySummary,
  EncyclopediaSection,
  HotLink,
  SourceMaterial,
  TrendSignal,
} from '../types'

const props = defineProps<{ categoryCode: string; identity: Identity; focusSection?: string | null }>()
const emit = defineEmits<{ changed: []; navigate: [code: string]; addNote: [code: string] }>()

const loading = ref(false)
const category = ref<CategoryDetail | null>(null)
const sources = ref<SourceMaterial[]>([])
const hotLinks = ref<HotLink[]>([])
const trendSignals = ref<TrendSignal[]>([])
const activeSectionKey = ref('definition')

const activeSection = computed(() =>
  category.value?.sections.find((s) => s.section_key === activeSectionKey.value) ?? category.value?.sections[0] ?? null,
)

const filterPlatform = ref('')

const sectionHotLinks = computed(() =>
  // 热点链接只在 market 章节显示（舆情与市场趋势）
  activeSectionKey.value === 'market' ? hotLinks.value : []
)

const hotLinkPlatforms = computed(() => {
  const set = new Set(sectionHotLinks.value.map((l) => l.platform))
  return Array.from(set)
})

const filteredHotLinks = computed(() => {
  if (!filterPlatform.value) return sectionHotLinks.value
  return sectionHotLinks.value.filter((l) => l.platform === filterPlatform.value)
})

const groupedHotLinks = computed(() => {
  const groups: Record<string, HotLink[]> = {}
  for (const link of filteredHotLinks.value) {
    const type = link.link_type
    if (!groups[type]) groups[type] = []
    // 清理 description 中的 HTML 实体
    const cleaned = {
      ...link,
      description: link.description ? cleanHtmlEntities(link.description) : link.description,
      description_zh: link.description_zh ? cleanHtmlEntities(link.description_zh) : link.description_zh,
    }
    groups[type].push(cleaned)
  }
  // 产品按热度降序排序
  if (groups['product']) {
    groups['product'].sort((a, b) => (b.hotness_score || 0) - (a.hotness_score || 0))
  }
  // 视频按热度降序排序
  if (groups['video']) {
    groups['video'].sort((a, b) => (b.hotness_score || 0) - (a.hotness_score || 0))
  }
  // 讨论按热度降序排序
  if (groups['discussion']) {
    groups['discussion'].sort((a, b) => (b.hotness_score || 0) - (a.hotness_score || 0))
  }
  return groups
})

function cleanHtmlEntities(text: string): string {
  return text.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
}

function hotLinkTitle(link: HotLink): string {
  return link.title_zh?.trim() || link.title
}

function hotLinkDescription(link: HotLink): string {
  return link.description_zh?.trim() || link.description
}

function trendSignalTitle(signal: TrendSignal): string {
  return signal.title_zh?.trim() || signal.title
}

function trendSignalSummary(signal: TrendSignal): string {
  return signal.summary_zh?.trim() || signal.summary
}

function linkify(text: string, iconOnly = false): string {
  if (!text) return ''
  const escaped = escapeHtml(text)
  const label = iconOnly ? '🔗' : '$1'
  // Match URLs but stop at CJK punctuation (。：，；！？、）」』) and whitespace
  return escaped.replace(
    /(https?:\/\/[^\s<。：，；！？、）」』]+)/g,
    `<a href="$1" target="_blank" rel="noreferrer noopener" class="inline-link" title="$1" aria-label="打开链接">${label}</a>`,
  )
}

const linkTypeOrder = ['product', 'video', 'social_post', 'discussion', 'trend', 'news', 'keyword']
const linkTypeLabels: Record<string, string> = {
  product: '🔥 爆品监控',
  video: '📺 视频测评',
  social_post: '📕 小红书笔记',
  discussion: '💬 社区讨论',
  trend: '📈 搜索趋势',
  news: '📰 新闻动态',
  keyword: '🔑 关键词',
}

const lastHotLinkUpdate = computed(() => {
  if (!hotLinks.value.length) return null
  const dates = hotLinks.value.map((l) => new Date(l.collected_at).getTime()).filter(Boolean)
  return dates.length ? new Date(Math.max(...dates)) : null
})

function formatRelativeTime(date: Date | null): string {
  if (!date) return '—'
  const hours = (Date.now() - date.getTime()) / 3600000
  if (hours < 1) return `${Math.floor(hours * 60)} 分钟前`
  if (hours < 24) return `${Math.floor(hours)} 小时前`
  return `${Math.floor(hours / 24)} 天前`
}

const crawlLoading = ref(false)

// 06 章节分块 tab
const marketTab = ref<'products' | 'videos' | 'discussions' | 'trends' | 'analysis'>('products')

const marketTimestamp = computed(() => {
  if (!activeSection.value || activeSectionKey.value !== 'market') return null
  const match = activeSection.value.content.match(/数据采集时间[：:]\s*([\d\-/]+)/)
  return match ? match[1] : null
})

const renderedContentWithoutTimestamp = computed(() => {
  if (!activeSection.value) return ''
  // 移除时间戳 blockquote 行，避免重复显示
  return activeSection.value.content
    .split('\n')
    .filter(line => !line.trim().startsWith('>') || !line.includes('数据采集时间'))
    .join('\n')
})
async function triggerCrawl() {
  if (!category.value) return
  try {
    await ElMessageBox.confirm('将手动触发一次热点爬取，预计需要 1-2 分钟。', '手动爬取', {
      confirmButtonText: '开始爬取',
      cancelButtonText: '取消',
    })
    crawlLoading.value = true
    await apiRequest(`/categories/${category.value.code}/crawl`, { method: 'POST' })
    ElMessage.success('爬取已触发，正在刷新数据...')
    await loadCategory()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error((error as Error).message)
  } finally {
    crawlLoading.value = false
  }
}

const sectionTrendSignals = computed(() =>
  // 趋势信号只在 market 章节显示（舆情与市场趋势）
  activeSectionKey.value === 'market'
    ? trendSignals.value
        .filter((s) => {
          // keyword_trend 信号即使 metric_value=null 也保留（有相关搜索词 summary）
          if (s.signal_type === 'keyword_trend') return true
          // 其他类型过滤掉 0/null 噪音
          return s.metric_value !== null && s.metric_value !== undefined && s.metric_value > 0
        })
    : []
)

function signalTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    search_volume: '搜索量',
    best_seller_rank: 'BSR 排名',
    social_mention: '社媒提及',
    keyword_trend: '关键词趋势',
    news_volume: '新闻量',
    review_sentiment: '评论情感',
    product_insight: '产品洞察',
    user_pain_point: '用户痛点',
  }
  return labels[type] || type
}

function metricUnitLabel(unit: string | null): string {
  if (!unit) return ''
  const labels: Record<string, string> = {
    avg_price_usd: '美元均价',
    products: '款产品',
    views: '次播放',
    articles: '篇新闻',
    comments: '条评论',
    likes: '点赞',
    '5yr avg': '5年均值',
    related_keywords: '个相关词',
    search_volume: '次搜索',
  }
  return labels[unit] || unit
}

function trendDirectionLabel(dir: string | null): string {
  if (!dir) return ''
  const labels: Record<string, string> = { up: '↑ 上升', down: '↓ 下降', stable: '→ 平稳', new: '★ 新增' }
  return labels[dir] || dir
}

function platformLabel(p: string): string {
  const labels: Record<string, string> = {
    google: 'Google', amazon: 'Amazon', reddit: 'Reddit',
    youtube: 'YouTube', tiktok: 'TikTok', xiaohongshu: '小红书',
    x: 'X', facebook: 'Facebook', news: 'News', other: 'Other',
  }
  return labels[p] || p
}

// ── 领域关键词提取 ──
// 英文标题/描述/关键词 → 中文标签，帮助用户快速抓住要点
const keywordDict: Array<{ pattern: RegExp; zh: string }> = [
  // 产品类型
  { pattern: /\btens\b/i, zh: 'TENS电刺激' },
  { pattern: /\bems\b/i, zh: 'EMS电脉冲' },
  { pattern: /\bheating pad/i, zh: '加热贴' },
  { pattern: /\bheat therapy/i, zh: '热敷理疗' },
  { pattern: /\bfar infrared\b|\bfir\b/i, zh: '远红外' },
  { pattern: /\binfrared/i, zh: '红外理疗' },
  { pattern: /\bnight light/i, zh: '夜灯' },
  { pattern: /\bmotion sensor/i, zh: '人体感应' },
  { pattern: /\bseat cushion/i, zh: '坐垫' },
  { pattern: /\b(coccyx|tailbone)\b/i, zh: '尾骨保护' },
  { pattern: /\bergonomic/i, zh: '人体工学' },
  { pattern: /\bpill organizer/i, zh: '智能药盒' },
  { pattern: /\bpill splitter/i, zh: '药片分割器' },
  { pattern: /\bheat lamp/i, zh: '理疗灯' },
  { pattern: /\b(photon|pemf)\b/i, zh: '光波脉冲理疗' },
  { pattern: /\bscarf\b/i, zh: '围巾式' },
  { pattern: /\bweighted\b/i, zh: '加重设计' },
  // 身体部位 / 适应症
  { pattern: /\bsciatica\b/i, zh: '坐骨神经痛' },
  { pattern: /\b(back pain|lower back)\b/i, zh: '腰背疼痛' },
  { pattern: /\b(neck pain|cervical)\b/i, zh: '颈椎疼痛' },
  { pattern: /\bshoulder\b/i, zh: '肩部疼痛' },
  { pattern: /\b(cramp|menstrual)\b/i, zh: '痉挛缓解' },
  { pattern: /\b(labour|labor)\b/i, zh: '分娩助产' },
  { pattern: /\bflat feet\b/i, zh: '扁平足' },
  { pattern: /\b(muscle pain|doms)\b/i, zh: '肌肉酸痛' },
  { pattern: /\bposture\b/i, zh: '姿势矫正' },
  { pattern: /\b(sleep|insomnia|awake)\b/i, zh: '睡眠改善' },
  { pattern: /\bdetox\b/i, zh: '排毒养颜' },
  { pattern: /\blaminectomy|discectomy|fusion\b/i, zh: '脊柱术后' },
  { pattern: /\bburn\b/i, zh: '低温烫伤' },
  // 产品特性
  { pattern: /\bwireless\b/i, zh: '无线便携' },
  { pattern: /\brechargeable\b/i, zh: '可充电' },
  { pattern: /\bsmart\b/i, zh: '智能联动' },
  { pattern: /\bwaterproof\b/i, zh: '防水' },
  { pattern: /\bportable\b/i, zh: '便携' },
  { pattern: /\belectrode\b/i, zh: '电极贴片' },
  // 动作/场景
  { pattern: /\b(review|best|top \d+)\b/i, zh: '产品测评' },
  { pattern: /\b(purchase|buy|worth)\b/i, zh: '购买决策' },
  { pattern: /\b(post[- ]?surgery|recovery)\b/i, zh: '术后康复' },
  { pattern: /\bprolonged sitting\b/i, zh: '久坐人群' },
  { pattern: /\b(office chair|workspace)\b/i, zh: '办公场景' },
  { pattern: /\b(restaurant|travel|car)\b/i, zh: '出行场景' },
  { pattern: /\bplacement\b/i, zh: '使用指导' },
  // 中文内容
  { pattern: /肩颈热敷|颈肩热敷|颈椎热敷|肩颈加热|暖颈/, zh: '肩颈热敷' },
  { pattern: /加热披肩|热敷披肩|肩颈披肩/, zh: '披肩式' },
  { pattern: /热敷|加热垫|加热贴/, zh: '热敷理疗' },
  { pattern: /理疗灯|烤灯/, zh: '理疗灯' },
  { pattern: /红外|红光/, zh: '红外理疗' },
  { pattern: /夜灯|小夜灯/, zh: '夜灯' },
  { pattern: /人体感应|感应灯/, zh: '人体感应' },
  { pattern: /药盒|分药盒/, zh: '智能药盒' },
  { pattern: /切药|分药器/, zh: '药片分割器' },
  { pattern: /坐垫|座垫|屁垫/, zh: '坐垫' },
  { pattern: /可充电|充电|续航/, zh: '可充电' },
  { pattern: /温度|档位|恒温|过热/, zh: '温度控制' },
  { pattern: /烫伤|低温烫伤/, zh: '低温烫伤' },
  { pattern: /尺寸|太紧|太松|贴合/, zh: '尺寸贴合' },
  { pattern: /办公|久坐|低头族/, zh: '办公久坐' },
  { pattern: /使用|教程|怎么用/, zh: '使用指导' },
  { pattern: /推荐|测评|哪个好|对比|好物/, zh: '产品测评' },
  { pattern: /吐槽|智商税|避坑|不好用|没效果|鸡肋|被坑/, zh: '吐槽避坑' },
]

function extractKeywords(text: string, fallbacks: string[] = []): string[] {
  const lowerText = text.toLowerCase()
  const found = new Set<string>()
  for (const entry of keywordDict) {
    if (entry.pattern.test(lowerText)) {
      found.add(entry.zh)
      if (found.size >= 3) break
    }
  }
  for (const fallback of fallbacks) {
    const keyword = fallback.trim().replace(/^["']|["']$/g, '')
    if (keyword && keyword.length <= 16) found.add(keyword)
    if (found.size >= 3) break
  }
  return Array.from(found)
}

function linkKeywords(link: HotLink): string[] {
  const title = hotLinkTitle(link)
  const description = hotLinkDescription(link)
  const searchKeyword = description.match(/搜索词:\s*([^|。\n]+)/)?.[1]?.trim()
  const fallbackLabels: Record<string, string> = {
    product: '产品信息',
    video: '视频测评',
    discussion: '用户讨论',
    social_post: '用户分享',
    news: '行业动态',
    trend: '趋势观察',
    keyword: '搜索趋势',
  }
  return extractKeywords(`${title} ${description}`, [
    searchKeyword || '',
    fallbackLabels[link.link_type] || '相关信息',
  ])
}

function signalKeywords(signal: TrendSignal): string[] {
  const fallbackLabels: Record<string, string> = {
    user_pain_point: '用户痛点',
    product_insight: '产品洞察',
    social_mention: '社媒热度',
    keyword_trend: '搜索趋势',
    review_sentiment: '评论情感',
  }
  return extractKeywords(
    `${signal.keyword || ''} ${trendSignalTitle(signal)} ${trendSignalSummary(signal)}`,
    [signal.keyword || '', fallbackLabels[signal.signal_type] || '趋势信号'],
  )
}
const editVisible = ref(false)
const editSection = ref<EncyclopediaSection | null>(null)
const editContent = ref('')
const selectedSourceIds = ref<number[]>([])
const sourceVisible = ref(false)
const sourceForm = ref({ source_type: 'manual', title: '', url: '', content: '' })
const boundaryVisible = ref(false)
const boundaryForm = ref({ description: '', aliases: '', included_items: '', excluded_items: '' })

/* ── Lightweight Markdown renderer ──
   Parses a subset of Markdown into HTML for v-html display.
   Supports: headings (###), tables, bold, links, blockquotes,
   unordered/ordered lists, and paragraphs. */
function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function renderMarkdown(md: string): string {
  if (!md) return ''
  const lines = md.replace(/\r\n/g, '\n').split('\n')
  const html: string[] = []
  let i = 0
  let inList: 'ul' | 'ol' | null = null
  let tableBuffer: string[] = []

  function flushList() {
    if (inList) {
      html.push(`</${inList}>`)
      inList = null
    }
  }
  function flushTable() {
    if (tableBuffer.length >= 2) {
      // Find separator line index
      const sepIdx = tableBuffer.findIndex((l) => l.trim().startsWith('|') && /[-:]/.test(l) && !l.includes('---'))
      const realSepIdx = sepIdx >= 0 ? sepIdx : (tableBuffer.length > 1 && /[-:]/.test(tableBuffer[1]) ? 1 : -1)

      if (realSepIdx > 0) {
        const headerCells = splitTableRow(tableBuffer[0])
        const bodyRows = tableBuffer.slice(realSepIdx + 1)
        let t = '<table class="md-table"><thead><tr>'
        for (const cell of headerCells) t += `<th>${inlineFormat(cell)}</th>`
        t += '</tr></thead><tbody>'
        for (const row of bodyRows) {
          if (!row.trim()) continue
          const cells = splitTableRow(row)
          t += '<tr>'
          for (const cell of cells) t += `<td>${inlineFormat(cell)}</td>`
          t += '</tr>'
        }
        t += '</tbody></table>'
        html.push(t)
      } else {
        // No separator — render as text
        for (const l of tableBuffer) html.push(`<p>${inlineFormat(l)}</p>`)
      }
    } else if (tableBuffer.length === 1) {
      html.push(`<p>${inlineFormat(tableBuffer[0])}</p>`)
    }
    tableBuffer = []
  }

  function splitTableRow(line: string): string[] {
    const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '')
    return trimmed.split('|').map((c) => c.trim())
  }

  function inlineFormat(text: string): string {
    text = escapeHtml(text)
    // Bold labels like **药盒类型**: → render as section label (before table/list)
    // This is handled in the main loop, not here
    // Links [text](url) — only allow http(s) protocols to prevent XSS
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label: string, url: string) => {
      const trimmed = url.trim()
      if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
        return `<a href="${trimmed}" target="_blank" rel="noreferrer noopener">${label}</a>`
      }
      return match
    })
    // Bold **text** or __text__
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>')
    // Inline code `text`
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>')
    // Italic *text*
    text = text.replace(/(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
    return text
  }

  let inCard = false

  function closeCard() {
    if (inCard) {
      html.push('</div>')
      inCard = false
    }
  }

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    // Empty line
    if (!trimmed) {
      flushList()
      flushTable()
      i++
      continue
    }

        // Table row (starts with |)
        if (trimmed.startsWith('|')) {
          flushList()
          tableBuffer.push(trimmed)
          i++
          continue
        } else {
          flushTable()
        }

        // Sub-section headings (### and deeper) — wrap in card
        if (/^#{3,6}\s/.test(trimmed)) {
          flushList()
          closeCard()
          const match = trimmed.match(/^(#{3,6})\s+(.+)/)
          if (match) {
            const level = match[1].length
            const text = match[2]
            const tag = level === 3 ? 'h4' : level === 4 ? 'h5' : 'h6'
            html.push('<div class="md-subsection">')
            inCard = true
            html.push(`<${tag} class="md-subheading">${inlineFormat(text)}</${tag}>`)
          }
          i++
          continue
        }

        // Level 1-2 headings — render as plain heading, close any card
        if (/^#{1,2}\s/.test(trimmed)) {
          flushList()
          closeCard()
          const match = trimmed.match(/^(#{1,2})\s+(.+)/)
          if (match) {
            html.push(`<h3 class="md-heading">${inlineFormat(match[2])}</h3>`)
          }
          i++
          continue
        }

        // Blockquote
        if (trimmed.startsWith('>')) {
          flushList()
          const quoteText = trimmed.replace(/^>\s?/, '')
          html.push(`<blockquote class="md-quote">${inlineFormat(quoteText)}</blockquote>`)
          i++
          continue
        }

        // Unordered list
        if (/^[-*+]\s/.test(trimmed)) {
          if (inList !== 'ul') {
            flushList()
            html.push('<ul class="md-ul">')
            inList = 'ul'
          }
          const itemText = trimmed.replace(/^[-*+]\s+/, '')
          html.push(`<li>${inlineFormat(itemText)}</li>`)
          i++
          continue
        }

        // Ordered list
        if (/^\d+\.\s/.test(trimmed)) {
          if (inList !== 'ol') {
            flushList()
            html.push('<ol class="md-ol">')
            inList = 'ol'
          }
          const itemText = trimmed.replace(/^\d+\.\s+/, '')
          html.push(`<li>${inlineFormat(itemText)}</li>`)
          i++
          continue
        }

        // Horizontal rule
        if (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed)) {
          flushList()
          closeCard()
          html.push('<hr class="md-hr" />')
          i++
          continue
        }

        // Regular paragraph
        flushList()
        html.push(`<p class="md-p">${inlineFormat(trimmed)}</p>`)
        i++
      }

      flushList()
      flushTable()
      closeCard()

      return html.join('\n')
}

const canEdit = computed(() => ['admin', 'researcher'].includes(props.identity.role))
const canEditContent = computed(() => canEdit.value)

function statusLabel(status: string) {
  return status === 'active' ? '持续更新' : '已停用'
}

function statusType(status: string) {
  return status === 'active' ? 'success' : 'info'
}

function sourceTypeLabel(type: string) {
  const labels: Record<string, string> = {
    manual: '人工补录',
    internal_doc: '内部文档',
    research: '调研报告',
    amazon: 'Amazon',
    search: '搜索资料',
    social: '社媒',
    media: '专业媒体',
  }
  return labels[type] || type
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('zh-CN')
}

function isStale(dateStr?: string | null): boolean {
  if (!dateStr) return false
  const days = (Date.now() - new Date(dateStr).getTime()) / 86_400_000
  return days > 30
}

async function loadCategory() {
  if (!props.categoryCode) return
  loading.value = true
  try {
    category.value = await apiRequest<CategoryDetail>(`/categories/${props.categoryCode}`)
    const sourceResponse = await apiRequest<{ items: SourceMaterial[] }>(
      `/categories/${props.categoryCode}/source-materials`,
    )
    const hotLinkResponse = await apiRequest<{ items: HotLink[] }>(
      `/categories/${props.categoryCode}/hot-links?days=7`,
    )
    const trendResponse = await apiRequest<{ items: TrendSignal[] }>(
      `/categories/${props.categoryCode}/trend-signals?days=7`,
    )
    sources.value = sourceResponse.items
    hotLinks.value = hotLinkResponse.items
    trendSignals.value = trendResponse.items
    await nextTick()
    scrollToSection()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

function scrollToSection() {
  if (!props.focusSection) return
  document.getElementById(props.focusSection)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function openEdit(section: EncyclopediaSection) {
  editSection.value = section
  editContent.value = section.content
  selectedSourceIds.value = section.evidence
    .filter((item) => item.source_type === 'source_material')
    .map((item) => item.source_id)
  editVisible.value = true
}

function openBoundaryEdit() {
  if (!category.value) return
  boundaryForm.value = {
    description: category.value.description,
    aliases: category.value.aliases.join('\n'),
    included_items: category.value.included_items.join('\n'),
    excluded_items: category.value.excluded_items.join('\n'),
  }
  boundaryVisible.value = true
}

async function saveBoundary() {
  if (!category.value) return
  const lines = (value: string) => value.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean)
  try {
    await apiRequest(
      `/categories/${category.value.code}`,
      {
        method: 'PATCH',
        body: JSON.stringify({
          description: boundaryForm.value.description,
          aliases: lines(boundaryForm.value.aliases),
          included_items: lines(boundaryForm.value.included_items),
          excluded_items: lines(boundaryForm.value.excluded_items),
        }),
      },
    )
    boundaryVisible.value = false
    ElMessage.success('品类边界已保存')
    await loadCategory()
    emit('changed')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

async function saveEdit() {
  if (!editSection.value || !category.value) return
  try {
    await apiRequest(
      `/categories/${category.value.code}/sections/${editSection.value.section_key}`,
      {
        method: 'PUT',
        body: JSON.stringify({
          content: editContent.value,
          evidence_source_ids: selectedSourceIds.value,
          generation_mode: 'human',
        }),
      },
    )
    editVisible.value = false
    ElMessage.success('内容已保存并锁定为人工编辑')
    await loadCategory()
    emit('changed')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

function buildSectionMarkdown(): string {
  if (!activeSection.value || !category.value) return ''
  let md = `# ${category.value.name} — ${activeSection.value.title}\n\n`
  md += activeSection.value.content + '\n\n'
  // Append hot links if market section
  if (activeSectionKey.value === 'market' && filteredHotLinks.value.length) {
    md += `## 热点链接\n\n`
    for (const group of Object.entries(groupedHotLinks.value)) {
      md += `### ${linkTypeLabels[group[0]] || group[0]}\n\n`
      for (const link of group[1]) {
        md += `- [${hotLinkTitle(link)}](${link.url}) — ${platformLabel(link.platform)}${link.hotness_score ? ` (热度 ${link.hotness_score})` : ''}\n`
      }
      md += '\n'
    }
  }
  // Append trend signals if market section
  if (activeSectionKey.value === 'market' && sectionTrendSignals.value.length) {
    md += `## 趋势信号\n\n`
    for (const sig of sectionTrendSignals.value) {
      md += `- **${signalTypeLabel(sig.signal_type)}** | ${platformLabel(sig.platform)} | 关键词: ${sig.keyword}${sig.metric_value ? ` | 值: ${sig.metric_value}${sig.metric_unit ? ' ' + metricUnitLabel(sig.metric_unit) : ''}` : ''} | ${trendSignalSummary(sig)}\n`
    }
    md += '\n'
  }
  // Append evidence
  if (activeSection.value.evidence.length) {
    md += `## 证据来源\n\n`
    for (const ev of activeSection.value.evidence) {
      const title = ev.source?.title || `${ev.source_type} #${ev.source_id}`
      const url = ev.source?.url || ''
      md += `- ${url ? `[${title}](${url})` : title}\n`
    }
  }
  return md
}

async function copySection() {
  const md = buildSectionMarkdown()
  if (!md) return
  try {
    await navigator.clipboard.writeText(md)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('当前浏览器不允许复制')
  }
}

function downloadSection() {
  const md = buildSectionMarkdown()
  if (!md || !category.value || !activeSection.value) return
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${category.value.code}-${activeSection.value.section_key}.md`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已下载 Markdown 文件')
}

function downloadFullCategory() {
  if (!category.value) return
  let md = `# ${category.value.name} — 品类百科\n\n`
  md += `> 品类编码: ${category.value.code}\n`
  if (category.value.description) md += `> 描述: ${category.value.description}\n\n`
  for (const section of category.value.sections) {
    md += `---\n\n## ${section.title}\n\n${section.content || '暂无内容'}\n\n`
    if (section.evidence.length) {
      md += `**证据来源:**\n`
      for (const ev of section.evidence) {
        const title = ev.source?.title || `${ev.source_type} #${ev.source_id}`
        const url = ev.source?.url || ''
        md += `- ${url ? `[${title}](${url})` : title}\n`
      }
      md += '\n'
    }
  }
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${category.value.code}-百科全文.md`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已下载完整百科 Markdown')
}

async function addSource() {
  if (!category.value || !sourceForm.value.title.trim()) return
  try {
    await apiRequest(
      '/source-materials',
      {
        method: 'POST',
        body: JSON.stringify({
          category_code: category.value.code,
          ...sourceForm.value,
          url: sourceForm.value.url || null,
        }),
      },
    )
    sourceVisible.value = false
    sourceForm.value = { source_type: 'manual', title: '', url: '', content: '' }
    ElMessage.success('来源材料已登记')
    await loadCategory()
    emit('changed')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

watch(() => props.categoryCode, () => {
  activeSectionKey.value = 'definition'
  loadCategory()
})
watch(() => props.focusSection, (val) => { if (val) activeSectionKey.value = val })

// 术语词典
const glossary: Record<string, string> = {
  'TENS': '经皮神经电刺激 (Transcutaneous Electrical Nerve Stimulation)',
  'EMS': '电肌肉刺激 (Electrical Muscle Stimulation)',
  'FIR': '远红外 (Far Infrared Radiation)',
  'BSR': 'Best Seller Rank，亚马逊畅销排名',
  'ASIN': '亚马逊标准识别号 (Amazon Standard Identification Number)',
  'Vasodilation': '血管扩张',
  'Gate Control Theory': '门控理论 — 疼痛信号传导机制',
  'PTC': '正温度系数热敏陶瓷 (Positive Temperature Coefficient)',
  'DOMS': '延迟性肌肉酸痛 (Delayed Onset Muscle Soreness)',
  'Graphene': '石墨烯 — 碳纳米材料，远红外发射率高',
  'Neoprene': '氯丁橡胶 — 弹性好，运动护具常用材料',
  'Polyurethane': '聚氨酯 — 记忆棉主要材料',
}

function enhanceGlossary(html: string): string {
  return html.split(/(<[^>]+>)/g).map((part) => {
    if (part.startsWith('<')) return part
    let text = part
    for (const [term, explanation] of Object.entries(glossary)) {
      const regex = new RegExp(`\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi')
      text = text.replace(regex, `<span class="glossary-term" title="${explanation}">${term}</span>`)
    }
    return text
  }).join('')
}

// 收藏功能 — localStorage 存储
const favorites = ref<Set<string>>(new Set())

// 全部品类列表（用于关联推荐）
const allCategories = ref<CategorySummary[]>([])

// 关联品类推荐 — 同父品类的兄弟品类
const relatedCategories = computed(() => {
  if (!category.value || !allCategories.value.length) return []
  const current = category.value
  // 如果是子品类，找同父的其他子品类
  if (current.parent_code) {
    return allCategories.value.filter(c =>
      c.parent_code === current.parent_code && c.code !== current.code
    ).slice(0, 4)
  }
  // 如果是一级品类，找其他一级品类
  return allCategories.value.filter(c =>
    !c.parent_code && c.code !== current.code
  ).slice(0, 4)
})

async function loadAllCategories() {
  try {
    const result = await apiRequest<{ items: CategorySummary[] }>('/categories')
    allCategories.value = result.items
  } catch { /* ignore */ }
}

function loadFavorites() {
  try {
    const saved = localStorage.getItem('encyclopedia_favorites')
    if (saved) favorites.value = new Set(JSON.parse(saved))
  } catch { /* ignore */ }
}

function saveFavorites() {
  localStorage.setItem('encyclopedia_favorites', JSON.stringify([...favorites.value]))
}

function toggleFavorite(url: string) {
  if (favorites.value.has(url)) {
    favorites.value.delete(url)
  } else {
    favorites.value.add(url)
  }
  favorites.value = new Set(favorites.value)
  saveFavorites()
}

function isFavorited(url: string): boolean {
  return favorites.value.has(url)
}

function goToNotes() {
  if (category.value) {
    emit('addNote', category.value.code)
  }
}

onMounted(() => {
  loadFavorites()
  loadAllCategories()
  loadCategory()
})
</script>

<template>
  <main v-loading="loading" class="workspace-main">
    <template v-if="category">
      <header class="category-header">
        <div>
          <div class="eyebrow">{{ category.parent_code ? '子品类' : '一级品类' }} · {{ category.code }}</div>
          <div class="title-row">
            <h1>{{ category.name }}</h1>
            <el-tag :type="statusType(category.status)" size="small">{{ statusLabel(category.status) }}</el-tag>
          </div>
          <p>{{ category.description }}</p>
        </div>
        <div class="header-actions">
          <el-button :icon="Refresh" @click="loadCategory">刷新</el-button>
          <el-button text :icon="Download" @click="downloadFullCategory">导出全文</el-button>
          <el-button text :icon="EditPen" @click="goToNotes">📝 添加笔记</el-button>
        </div>
      </header>

      <!-- 品类快速摘要 — 业务同事秒懂核心信息 -->
      <section v-if="category" class="quick-summary">
        <div class="qs-item">
          <span class="qs-label">所属大类</span>
          <span class="qs-value">{{ category.parent_code ? category.parent_code : '一级品类' }}</span>
        </div>
        <div class="qs-item">
          <span class="qs-label">数据状态</span>
          <span class="qs-value">{{ marketTimestamp ? `今日已更新` : `等待爬取` }}</span>
        </div>
        <div class="qs-item">
          <span class="qs-label">热点</span>
          <span class="qs-value">{{ hotLinks.length }} 条</span>
        </div>
        <div class="qs-item">
          <span class="qs-label">趋势</span>
          <span class="qs-value">{{ trendSignals.length }} 条</span>
        </div>
        <div class="qs-item">
          <span class="qs-label">来源</span>
          <span class="qs-value">{{ sources.length }} 条</span>
        </div>
        <div class="qs-item">
          <span class="qs-label">完整度</span>
          <span class="qs-value">{{ category.sections.filter((s) => s.content).length }}/{{ category.sections.length }}</span>
        </div>
      </section>

      <section v-if="activeSectionKey === 'market'" class="summary-strip">
        <div class="stat-hot"><strong>{{ filteredHotLinks.length }}</strong><span>🔥 热点链接</span></div>
        <div><strong>{{ sectionTrendSignals.length }}</strong><span>📊 趋势信号</span></div>
        <div><strong>{{ sources.length }}</strong><span>📎 来源材料</span></div>
        <div><strong>{{ category.sections.filter((item) => item.content).length }}/{{ category.sections.length }}</strong><span>已填写模块</span></div>
      </section>

      <section v-if="!category.sections.some((item) => item.content)" class="getting-started">
        <div class="getting-started-icon">→</div>
        <div>
          <strong>先准备数据，再开始建立百科</strong>
          <p>可以登记一条研究来源，或在「06 舆情与市场趋势」中点击「手动爬取」获取热点数据。</p>
        </div>
      </section>

      <div class="content-card">
        <aside class="document-outline">
          <span>本页目录</span>
          <button
            v-for="(section, index) in category.sections"
            :key="section.id"
            class="outline-item"
            :class="{ active: section.section_key === activeSectionKey }"
            @click="activeSectionKey = section.section_key"
          >
            <span class="outline-num">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="outline-label" :title="section.title">{{ section.title }}</span>
            <i v-if="section.content" class="outline-dot filled"></i>
            <i v-else class="outline-dot"></i>
          </button>
        </aside>
        <div class="content-body">
          <!-- Boundary panel (only on first section) -->
          <section v-if="activeSectionKey === 'definition'" class="boundary-panel">
            <div class="boundary-heading"><span class="field-label">品类边界</span><el-button v-if="canEditContent" text @click="openBoundaryEdit">编辑边界</el-button></div>
            <div>
              <span class="field-label">包含</span>
              <el-tag v-for="item in category.included_items" :key="item" type="success" effect="plain" size="small">{{ item }}</el-tag>
            </div>
            <div>
              <span class="field-label">排除</span>
              <el-tag v-for="item in category.excluded_items" :key="item" type="danger" effect="plain" size="small">{{ item }}</el-tag>
            </div>
          </section>

          <!-- Single section view -->
          <article v-if="activeSection" class="document-canvas">
            <section class="document-section active-section">
              <header>
                <div>
                  <span class="section-number">{{ String(category.sections.findIndex((s) => s.section_key === activeSectionKey) + 1).padStart(2, '0') }}</span>
                  <h2>{{ activeSection.title }}</h2>
                </div>
                <div class="section-header-actions">
                  <el-button text :icon="CopyDocument" @click="copySection">复制</el-button>
                  <el-button text :icon="Download" @click="downloadSection">导出</el-button>
                  <el-button v-if="canEditContent" text :icon="EditPen" @click="openEdit(activeSection)">编辑</el-button>
                </div>
              </header>

              <!-- ⏰ 数据采集时间 — market 章节顶置 -->
              <div v-if="activeSectionKey === 'market' && marketTimestamp" class="market-timestamp">
                <span>⏰ 数据采集时间: {{ marketTimestamp }}</span>
              </div>

              <!-- 06 章节分块 tab — 内容太多，按类型切换 -->
              <div v-if="activeSectionKey === 'market'" class="market-tabs">
                <button :class="{ active: marketTab === 'products' }" @click="marketTab = 'products'">🛒 爆品监控</button>
                <button :class="{ active: marketTab === 'videos' }" @click="marketTab = 'videos'">📺 视频测评</button>
                <button :class="{ active: marketTab === 'discussions' }" @click="marketTab = 'discussions'">💬 社区讨论</button>
                <button :class="{ active: marketTab === 'trends' }" @click="marketTab = 'trends'">📊 趋势信号</button>
                <button :class="{ active: marketTab === 'analysis' }" @click="marketTab = 'analysis'">📝 分析正文</button>
              </div>

              <!-- 爆品监控 (Amazon product) -->
              <div v-if="activeSectionKey === 'market' && marketTab === 'products'" class="hot-links-section hot-links-priority">
                <div class="hot-links-header">
                  <span class="evidence-label">🛒 爆品监控</span>
                  <span v-if="lastHotLinkUpdate" class="hot-links-update">最后更新: {{ formatRelativeTime(lastHotLinkUpdate) }}</span>
                  <el-button v-if="canEdit" size="small" :loading="crawlLoading" :icon="Refresh" @click="triggerCrawl">手动爬取</el-button>
                </div>
                <div v-if="groupedHotLinks['product']" class="hot-link-group">
                  <div class="hot-links-list">
                    <a v-for="link in groupedHotLinks['product'].filter(l => l.description && !l.description.includes('\$?') && !l.description.includes('0 reviews')).slice(0, 20)" :key="link.id" :href="link.url" target="_blank" rel="noreferrer noopener" class="hot-link-item" :class="{ 'is-hot': link.is_hot, 'is-fav': isFavorited(link.url) }">
                      <div class="hot-link-title"><span v-if="link.is_hot" class="hot-badge">🔥</span>{{ hotLinkTitle(link) }}</div>
                      <div class="hl-keywords">
                        <span v-for="kw in linkKeywords(link)" :key="kw" class="hl-keyword-tag">{{ kw }}</span>
                      </div>
                      <div class="hot-link-meta">
                        <el-tag size="small" effect="plain" type="success">Amazon</el-tag>
                        <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
                        <button class="fav-btn" :class="{ active: isFavorited(link.url) }" @click.prevent="toggleFavorite(link.url)">⭐</button>
                      </div>
                      <div v-if="hotLinkDescription(link)" class="hot-link-desc" v-html="linkify(hotLinkDescription(link))"></div>
                      <small class="hot-link-date">{{ formatDate(link.collected_at) }}</small>
                    </a>
                  </div>
                </div>
                <el-empty v-else description="暂无 Amazon 产品数据" :image-size="60" />
              </div>

              <!-- 视频测评 (YouTube) -->
              <div v-if="activeSectionKey === 'market' && marketTab === 'videos'" class="hot-links-section">
                <div class="hot-links-header"><span class="evidence-label">📺 视频测评</span></div>
                <div v-if="groupedHotLinks['video']" class="hot-link-group">
                  <div class="hot-links-list">
                    <a v-for="link in groupedHotLinks['video']" :key="link.id" :href="link.url" target="_blank" rel="noreferrer noopener" class="hot-link-item" :class="{ 'is-hot': link.is_hot, 'is-fav': isFavorited(link.url) }">
                      <div class="hot-link-title"><span v-if="link.is_hot" class="hot-badge">🔥</span>{{ hotLinkTitle(link) }}</div>
                      <div v-if="linkKeywords(link).length" class="hl-keywords">
                        <span v-for="kw in linkKeywords(link)" :key="kw" class="hl-keyword-tag">{{ kw }}</span>
                      </div>
                      <div class="hot-link-meta">
                        <el-tag size="small" effect="plain">YouTube</el-tag>
                        <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
                        <button class="fav-btn" :class="{ active: isFavorited(link.url) }" @click.prevent="toggleFavorite(link.url)">⭐</button>
                      </div>
                      <div v-if="hotLinkDescription(link)" class="hot-link-desc" v-html="linkify(hotLinkDescription(link))"></div>
                      <small class="hot-link-date">{{ formatDate(link.collected_at) }}</small>
                    </a>
                  </div>
                </div>
                <el-empty v-else description="暂无 YouTube 视频数据" :image-size="60" />
              </div>

              <!-- 社区讨论 (Reddit + 小红书) -->
              <div v-if="activeSectionKey === 'market' && marketTab === 'discussions'" class="hot-links-section">
                <div class="hot-links-header"><span class="evidence-label">💬 社区讨论</span></div>
                <div v-if="groupedHotLinks['discussion'] || groupedHotLinks['social_post']" class="hot-link-group">
                  <div class="hot-links-list">
                    <a v-for="link in [...(groupedHotLinks['social_post'] || []), ...(groupedHotLinks['discussion'] || [])]" :key="link.id" :href="link.url" target="_blank" rel="noreferrer noopener" class="hot-link-item" :class="{ 'is-hot': link.is_hot, 'is-fav': isFavorited(link.url) }">
                      <div class="hot-link-title"><span v-if="link.is_hot" class="hot-badge">🔥</span>{{ hotLinkTitle(link) }}</div>
                      <div v-if="linkKeywords(link).length" class="hl-keywords">
                        <span v-for="kw in linkKeywords(link)" :key="kw" class="hl-keyword-tag">{{ kw }}</span>
                      </div>
                      <div class="hot-link-meta">
                        <el-tag size="small" effect="plain" :type="link.platform === 'reddit' ? '' : 'danger'">{{ platformLabel(link.platform) }}</el-tag>
                        <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
                        <button class="fav-btn" :class="{ active: isFavorited(link.url) }" @click.prevent="toggleFavorite(link.url)">⭐</button>
                      </div>
                      <div v-if="hotLinkDescription(link)" class="hot-link-desc" v-html="linkify(hotLinkDescription(link))"></div>
                      <small class="hot-link-date">{{ formatDate(link.collected_at) }}</small>
                    </a>
                  </div>
                </div>
                <el-empty v-else description="暂无社区讨论数据" :image-size="60" />
              </div>

              <!-- 趋势信号 -->
              <div v-if="activeSectionKey === 'market' && marketTab === 'trends' && sectionTrendSignals.length" class="trend-signals trend-signals-priority">
                <span class="evidence-label">📊 趋势信号</span>
                <div class="trend-signal-grid">
                  <div v-for="signal in sectionTrendSignals" :key="signal.id" class="trend-signal-card" :class="`trend-dir-${signal.trend_direction || 'stable'}`">
                    <div class="trend-signal-header">
                      <span class="trend-signal-type">{{ signalTypeLabel(signal.signal_type) }}</span>
                      <span class="trend-signal-platform">{{ platformLabel(signal.platform) }}</span>
                      <span v-if="signal.trend_direction" class="trend-signal-direction" :class="`dir-${signal.trend_direction}`">{{ trendDirectionLabel(signal.trend_direction) }}</span>
                    </div>
                    <div v-if="signalKeywords(signal).length" class="hl-keywords">
                      <span v-for="kw in signalKeywords(signal)" :key="kw" class="hl-keyword-tag">{{ kw }}</span>
                    </div>
                    <div v-if="trendSignalTitle(signal)" class="trend-signal-title">{{ trendSignalTitle(signal) }}</div>
                    <div v-if="signal.keyword" class="trend-signal-keyword">关键词：{{ signal.keyword }}</div>
                    <div v-if="signal.metric_value !== null && signal.metric_value !== undefined" class="trend-signal-metric">
                      <span class="metric-value">{{ signal.metric_value }}</span>
                      <span v-if="signal.metric_unit" class="metric-unit">{{ metricUnitLabel(signal.metric_unit) }}</span>
                    </div>
                    <div v-if="trendSignalSummary(signal)" class="trend-signal-summary" v-html="linkify(trendSignalSummary(signal), true)"></div>
                    <small class="trend-signal-date">{{ formatDate(signal.collected_at) }}</small>
                  </div>
                </div>
              </div>

              <!-- 分析正文 -->
              <div v-if="activeSectionKey === 'market' && marketTab === 'analysis'">
                <div v-if="activeSection.content" class="section-content" v-html="enhanceGlossary(renderMarkdown(renderedContentWithoutTimestamp))"></div>
                <div v-else class="section-empty">暂无内容。可以补充材料或编辑章节。</div>
              </div>

              <!-- 非 market 章节 — 保持原有逻辑 -->
              <div v-if="activeSectionKey !== 'market'">
                <!-- 🔥 热点链接 — 顶置 -->
                <div v-if="filteredHotLinks.length" class="hot-links-section hot-links-priority">
                  <div class="hot-links-header">
                    <span class="evidence-label">🔥 今日热点</span>
                    <span v-if="lastHotLinkUpdate" class="hot-links-update">最后更新: {{ formatRelativeTime(lastHotLinkUpdate) }}</span>
                    <el-button v-if="canEdit" size="small" :loading="crawlLoading" :icon="Refresh" @click="triggerCrawl">手动爬取</el-button>
                    <el-select v-model="filterPlatform" placeholder="全部平台" size="small" clearable style="width: 140px; margin-left: auto">
                      <el-option v-for="p in hotLinkPlatforms" :key="p" :label="platformLabel(p)" :value="p" />
                    </el-select>
                  </div>
                  <div v-for="type in linkTypeOrder.filter((t) => groupedHotLinks[t])" :key="type" class="hot-link-group">
                    <div class="hot-link-group-title">{{ linkTypeLabels[type] || type }}</div>
                    <div class="hot-links-list">
                      <a v-for="link in groupedHotLinks[type]" :key="link.id" :href="link.url" target="_blank" rel="noreferrer noopener" class="hot-link-item" :class="{ 'is-hot': link.is_hot, 'is-fav': isFavorited(link.url) }">
                        <div class="hot-link-title"><span v-if="link.is_hot" class="hot-badge">🔥</span>{{ hotLinkTitle(link) }}</div>
                        <div class="hl-keywords">
                          <span v-for="kw in linkKeywords(link)" :key="kw" class="hl-keyword-tag">{{ kw }}</span>
                        </div>
                        <div class="hot-link-meta">
                          <el-tag size="small" effect="plain">{{ platformLabel(link.platform) }}</el-tag>
                          <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
                          <button class="fav-btn" :class="{ active: isFavorited(link.url) }" @click.prevent="toggleFavorite(link.url)">⭐</button>
                        </div>
                        <div v-if="hotLinkDescription(link)" class="hot-link-desc" v-html="linkify(hotLinkDescription(link))"></div>
                        <small class="hot-link-date">{{ formatDate(link.collected_at) }}</small>
                      </a>
                    </div>
                  </div>
                </div>
                <div v-else-if="activeSectionKey === 'market'" class="hot-links-empty">
                  <span class="evidence-label">🔥 今日热点</span>
                  <p>该品类暂无爬取到的热点数据。可点击「手动爬取」触发一次数据采集。</p>
                  <el-button v-if="canEdit" size="small" :loading="crawlLoading" :icon="Refresh" @click="triggerCrawl">手动爬取</el-button>
                </div>
                <!-- 📊 趋势信号 -->
                <div v-if="sectionTrendSignals.length" class="trend-signals trend-signals-priority">
                  <span class="evidence-label">📊 趋势信号</span>
                  <div class="trend-signal-grid">
                    <div v-for="signal in sectionTrendSignals" :key="signal.id" class="trend-signal-card" :class="`trend-dir-${signal.trend_direction || 'stable'}`">
                      <div class="trend-signal-header">
                        <span class="trend-signal-type">{{ signalTypeLabel(signal.signal_type) }}</span>
                        <span class="trend-signal-platform">{{ platformLabel(signal.platform) }}</span>
                        <span v-if="signal.trend_direction" class="trend-signal-direction" :class="`dir-${signal.trend_direction}`">{{ trendDirectionLabel(signal.trend_direction) }}</span>
                      </div>
                      <div v-if="signalKeywords(signal).length" class="hl-keywords">
                        <span v-for="kw in signalKeywords(signal)" :key="kw" class="hl-keyword-tag">{{ kw }}</span>
                      </div>
                      <div v-if="trendSignalTitle(signal)" class="trend-signal-title">{{ trendSignalTitle(signal) }}</div>
                      <div v-if="signal.keyword" class="trend-signal-keyword">关键词：{{ signal.keyword }}</div>
                      <div v-if="signal.metric_value !== null && signal.metric_value !== undefined" class="trend-signal-metric">
                        <span class="metric-value">{{ signal.metric_value }}</span>
                        <span v-if="signal.metric_unit" class="metric-unit">{{ metricUnitLabel(signal.metric_unit) }}</span>
                      </div>
                      <div v-if="trendSignalSummary(signal)" class="trend-signal-summary" v-html="linkify(trendSignalSummary(signal), true)"></div>
                      <small class="trend-signal-date">{{ formatDate(signal.collected_at) }}</small>
                    </div>
                  </div>
                </div>
                <!-- 📝 分析内容 -->
                <div v-if="activeSection.content" class="section-content" v-html="enhanceGlossary(renderMarkdown(renderedContentWithoutTimestamp))"></div>
                <div v-else class="section-empty">暂无内容。可以补充材料或编辑章节。</div>
              </div>
              <footer>
                <span>{{ activeSection.generation_mode === 'human' ? '人工编辑' : activeSection.generation_mode === 'generated' ? '已填充' : '未填写' }}</span>
                <span v-if="activeSection.locked_by_human">已锁定</span>
                <span>{{ activeSection.evidence.length }} 条证据</span>
                <span v-if="activeSection.updated_by">更新人：{{ activeSection.updated_by }}</span>
                <span v-if="activeSection.updated_at" :class="{ stale: isStale(activeSection.updated_at) }">{{ formatDate(activeSection.updated_at) }}{{ isStale(activeSection.updated_at) ? ' · 数据可能过时' : '' }}</span>
              </footer>

              <!-- 📎 证据 — 最后，原始来源材料 -->
              <div v-if="activeSection.evidence.length" class="evidence-list">
                <span class="evidence-label">📎 证据来源</span>
                <a
                  v-for="evidence in activeSection.evidence"
                  :key="evidence.id"
                  :href="evidence.source?.url || undefined"
                  target="_blank"
                  rel="noreferrer"
                  class="evidence-chip"
                >
                  {{ evidence.source?.title || `${evidence.source_type} #${evidence.source_id}` }}
                  <small>{{ formatDate(evidence.source?.collected_at) }}</small>
                </a>
              </div>
            </section>
          </article>
        </div>
      </div>

      <el-dialog v-model="editVisible" :title="editSection?.title" width="min(760px, 92vw)">
        <el-input v-model="editContent" type="textarea" :rows="14" resize="vertical" />
        <div v-if="sources.length" class="evidence-picker">
          <div class="field-label">绑定研究来源</div>
          <el-checkbox-group v-model="selectedSourceIds">
            <el-checkbox v-for="source in sources" :key="source.id" :value="source.id">{{ source.title }}</el-checkbox>
          </el-checkbox-group>
        </div>
        <template #footer>
          <el-button @click="editVisible = false">取消</el-button>
          <el-button type="primary" @click="saveEdit">保存并锁定</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="sourceVisible" title="登记来源材料" width="min(620px, 92vw)">
        <el-form label-position="top">
          <el-form-item label="来源类型">
            <el-select v-model="sourceForm.source_type" style="width: 100%">
              <el-option label="人工补充" value="manual" />
              <el-option label="内部文档" value="internal_doc" />
              <el-option label="调研报告" value="research" />
              <el-option label="搜索数据" value="search" />
              <el-option label="社媒" value="social" />
              <el-option label="专业媒体" value="media" />
            </el-select>
          </el-form-item>
          <el-form-item label="标题"><el-input v-model="sourceForm.title" /></el-form-item>
          <el-form-item label="链接"><el-input v-model="sourceForm.url" placeholder="https://" /></el-form-item>
          <el-form-item label="摘要或备注"><el-input v-model="sourceForm.content" type="textarea" :rows="6" /></el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="sourceVisible = false">取消</el-button>
          <el-button type="primary" @click="addSource">保存来源</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="boundaryVisible" title="编辑品类边界" width="min(680px, 92vw)">
        <el-form label-position="top">
          <el-form-item label="品类描述"><el-input v-model="boundaryForm.description" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="别名"><el-input v-model="boundaryForm.aliases" type="textarea" :rows="2" placeholder="每行一个，也可以用逗号分隔" /></el-form-item>
          <el-form-item label="包含项"><el-input v-model="boundaryForm.included_items" type="textarea" :rows="3" placeholder="每行一个" /></el-form-item>
          <el-form-item label="排除项"><el-input v-model="boundaryForm.excluded_items" type="textarea" :rows="3" placeholder="每行一个" /></el-form-item>
        </el-form>
        <template #footer><el-button @click="boundaryVisible = false">取消</el-button><el-button type="primary" @click="saveBoundary">保存边界</el-button></template>
      </el-dialog>
    </template>
  </main>
</template>
