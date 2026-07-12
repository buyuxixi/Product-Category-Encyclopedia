<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen, MagicStick, Refresh, View, CopyDocument, Download } from '@element-plus/icons-vue'
import { apiRequest, type Identity } from '../api'
import type {
  CategoryDetail,
  CategorySummary,
  DraftSuggestion,
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
    groups[type].push(link)
  }
  return groups
})

const linkTypeOrder = ['product', 'video', 'discussion', 'trend', 'news', 'keyword']
const linkTypeLabels: Record<string, string> = {
  product: '🔥 爆品监控',
  video: '📺 视频测评',
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
  }
  return labels[type] || type
}

function trendDirectionLabel(dir: string | null): string {
  if (!dir) return ''
  const labels: Record<string, string> = { up: '↑ 上升', down: '↓ 下降', stable: '→ 平稳', new: '★ 新增' }
  return labels[dir] || dir
}

function platformLabel(p: string): string {
  const labels: Record<string, string> = {
    google: 'Google', amazon: 'Amazon', reddit: 'Reddit',
    youtube: 'YouTube', tiktok: 'TikTok', x: 'X', facebook: 'Facebook', news: 'News', other: 'Other',
  }
  return labels[p] || p
}
const editVisible = ref(false)
const editSection = ref<EncyclopediaSection | null>(null)
const editContent = ref('')
const selectedSourceIds = ref<number[]>([])
const draftVisible = ref(false)
const draftLoading = ref(false)
const suggestions = ref<DraftSuggestion[]>([])
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

function renderedContent(section: EncyclopediaSection): string {
  return renderMarkdown(section.content)
}

const canEdit = computed(() => ['admin', 'researcher'].includes(props.identity.role))
const canEditContent = computed(
  () => canEdit.value && ['data_preparation', 'draft', 'rejected'].includes(category.value?.workflow_status || ''),
)

function workflowLabel(status: string) {
  const labels: Record<string, string> = {
    data_preparation: '数据准备中',
    draft: '草稿',
    pending_review: '待审核',
    approved: '已通过',
    published: '已发布',
  }
  return labels[status] || status
}

function statusType(status: string) {
  if (status === 'published' || status === 'approved') return 'success'
  if (status === 'pending_review') return 'warning'
  return 'info'
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
          evidence_listing_ids: editSection.value.evidence
            .filter((item) => item.source_type === 'listing_snapshot')
            .map((item) => item.source_id),
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
        md += `- [${link.title}](${link.url}) — ${platformLabel(link.platform)}${link.hotness_score ? ` (热度 ${link.hotness_score})` : ''}\n`
      }
      md += '\n'
    }
  }
  // Append trend signals if market section
  if (activeSectionKey.value === 'market' && sectionTrendSignals.value.length) {
    md += `## 趋势信号\n\n`
    for (const sig of sectionTrendSignals.value) {
      md += `- **${signalTypeLabel(sig.signal_type)}** | ${platformLabel(sig.platform)} | 关键词: ${sig.keyword}${sig.metric_value ? ` | 值: ${sig.metric_value}${sig.metric_unit ? ' ' + sig.metric_unit : ''}` : ''} | ${sig.summary}\n`
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

async function generateDraft() {
  if (!category.value) return
  draftLoading.value = true
  draftVisible.value = true
  try {
    const result = await apiRequest<{ listing_count: number; suggestions: DraftSuggestion[] }>(
      `/categories/${category.value.code}/drafts`,
      {
        method: 'POST',
        body: JSON.stringify({ listing_limit: 100, source_material_ids: sources.value.map((item) => item.id) }),
      },
    )
    suggestions.value = result.suggestions.map((item) => ({ ...item, selected: true }))
  } catch (error) {
    ElMessage.error((error as Error).message)
    draftVisible.value = false
  } finally {
    draftLoading.value = false
  }
}

async function applyDraft() {
  if (!category.value) return
  const selected = suggestions.value.filter((item) => item.selected)
  if (!selected.length) return
  let applied = 0
  const skipped: string[] = []
  for (const item of selected) {
    try {
      await apiRequest(
        `/categories/${category.value.code}/sections/${item.section_key}`,
        {
          method: 'PUT',
          body: JSON.stringify({
            content: item.content,
            evidence_listing_ids: item.evidence_listing_ids,
            evidence_source_ids: item.evidence_source_ids,
            generation_mode: 'generated',
          }),
        },
      )
      applied += 1
    } catch {
      skipped.push(item.title)
    }
  }
  draftVisible.value = false
  await loadCategory()
  emit('changed')
  if (skipped.length) {
    ElMessage.warning(`已应用 ${applied} 个模块；人工锁定未覆盖：${skipped.join('、')}`)
  } else {
    ElMessage.success(`已应用 ${applied} 个草稿模块`)
  }
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
  let result = html
  for (const [term, explanation] of Object.entries(glossary)) {
    const regex = new RegExp(`\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi')
    result = result.replace(regex, `<span class="glossary-term" title="${explanation}">${term}</span>`)
  }
  return result
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
            <el-tag :type="statusType(category.workflow_status)" size="small">{{ workflowLabel(category.workflow_status) }}</el-tag>
          </div>
          <p>{{ category.description }}</p>
        </div>
        <div class="header-actions">
          <el-button :icon="Refresh" @click="loadCategory">刷新</el-button>
          <el-button text :icon="Download" @click="downloadFullCategory">导出全文</el-button>
          <el-button v-if="canEditContent" :icon="MagicStick" @click="generateDraft">生成草稿</el-button>
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
          <span class="qs-value">{{ marketTimestamp ? `今日已更新` : '待更新' }}</span>
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
            <span class="outline-label">{{ section.title }}</span>
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
                    <a v-for="link in groupedHotLinks['product']" :key="link.id" :href="link.url" target="_blank" rel="noreferrer noopener" class="hot-link-item" :class="{ 'is-hot': link.is_hot, 'is-fav': isFavorited(link.url) }">
                      <div class="hot-link-title"><span v-if="link.is_hot" class="hot-badge">🔥</span>{{ link.title }}</div>
                      <div class="hot-link-meta">
                        <el-tag size="small" effect="plain" type="success">Amazon</el-tag>
                        <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
                        <button class="fav-btn" :class="{ active: isFavorited(link.url) }" @click.prevent="toggleFavorite(link.url)">⭐</button>
                      </div>
                      <div v-if="link.description" class="hot-link-desc">{{ link.description }}</div>
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
                      <div class="hot-link-title"><span v-if="link.is_hot" class="hot-badge">🔥</span>{{ link.title }}</div>
                      <div class="hot-link-meta">
                        <el-tag size="small" effect="plain">YouTube</el-tag>
                        <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
                        <button class="fav-btn" :class="{ active: isFavorited(link.url) }" @click.prevent="toggleFavorite(link.url)">⭐</button>
                      </div>
                      <div v-if="link.description" class="hot-link-desc">{{ link.description }}</div>
                      <small class="hot-link-date">{{ formatDate(link.collected_at) }}</small>
                    </a>
                  </div>
                </div>
                <el-empty v-else description="暂无 YouTube 视频数据" :image-size="60" />
              </div>

              <!-- 社区讨论 (Reddit) -->
              <div v-if="activeSectionKey === 'market' && marketTab === 'discussions'" class="hot-links-section">
                <div class="hot-links-header"><span class="evidence-label">💬 社区讨论</span></div>
                <div v-if="groupedHotLinks['discussion']" class="hot-link-group">
                  <div class="hot-links-list">
                    <a v-for="link in groupedHotLinks['discussion']" :key="link.id" :href="link.url" target="_blank" rel="noreferrer noopener" class="hot-link-item" :class="{ 'is-hot': link.is_hot, 'is-fav': isFavorited(link.url) }">
                      <div class="hot-link-title"><span v-if="link.is_hot" class="hot-badge">🔥</span>{{ link.title }}</div>
                      <div class="hot-link-meta">
                        <el-tag size="small" effect="plain">Reddit</el-tag>
                        <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
                        <button class="fav-btn" :class="{ active: isFavorited(link.url) }" @click.prevent="toggleFavorite(link.url)">⭐</button>
                      </div>
                      <div v-if="link.description" class="hot-link-desc">{{ link.description }}</div>
                      <small class="hot-link-date">{{ formatDate(link.collected_at) }}</small>
                    </a>
                  </div>
                </div>
                <el-empty v-else description="暂无 Reddit 讨论数据" :image-size="60" />
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
                    <div v-if="signal.title" class="trend-signal-title">{{ signal.title }}</div>
                    <div v-if="signal.keyword" class="trend-signal-keyword">关键词：{{ signal.keyword }}</div>
                    <div v-if="signal.metric_value !== null && signal.metric_value !== undefined" class="trend-signal-metric">
                      <span class="metric-value">{{ signal.metric_value }}</span>
                      <span v-if="signal.metric_unit" class="metric-unit">{{ signal.metric_unit }}</span>
                    </div>
                    <div v-if="signal.summary" class="trend-signal-summary">{{ signal.summary }}</div>
                    <small class="trend-signal-date">{{ formatDate(signal.collected_at) }}</small>
                  </div>
                </div>
              </div>

              <!-- 分析正文 -->
              <div v-if="activeSectionKey === 'market' && marketTab === 'analysis'">
                <div v-if="activeSection.content" class="section-content" v-html="enhanceGlossary(renderMarkdown(renderedContentWithoutTimestamp))"></div>
                <div v-else class="section-empty">暂无内容。可以补充材料或生成草稿。</div>
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
                        <div class="hot-link-title"><span v-if="link.is_hot" class="hot-badge">🔥</span>{{ link.title }}</div>
                        <div class="hot-link-meta">
                          <el-tag size="small" effect="plain">{{ platformLabel(link.platform) }}</el-tag>
                          <span v-if="link.hotness_score" class="hot-score">热度 {{ link.hotness_score }}</span>
                          <button class="fav-btn" :class="{ active: isFavorited(link.url) }" @click.prevent="toggleFavorite(link.url)">⭐</button>
                        </div>
                        <div v-if="link.description" class="hot-link-desc">{{ link.description }}</div>
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
                      <div v-if="signal.title" class="trend-signal-title">{{ signal.title }}</div>
                      <div v-if="signal.keyword" class="trend-signal-keyword">关键词：{{ signal.keyword }}</div>
                      <div v-if="signal.metric_value !== null && signal.metric_value !== undefined" class="trend-signal-metric">
                        <span class="metric-value">{{ signal.metric_value }}</span>
                        <span v-if="signal.metric_unit" class="metric-unit">{{ signal.metric_unit }}</span>
                      </div>
                      <div v-if="signal.summary" class="trend-signal-summary">{{ signal.summary }}</div>
                      <small class="trend-signal-date">{{ formatDate(signal.collected_at) }}</small>
                    </div>
                  </div>
                </div>
                <!-- 📝 分析内容 -->
                <div v-if="activeSection.content" class="section-content" v-html="enhanceGlossary(renderMarkdown(renderedContentWithoutTimestamp))"></div>
                <div v-else class="section-empty">暂无内容。可以补充材料或生成草稿。</div>
              </div>
              <footer>
                <span>{{ activeSection.generation_mode === 'human' ? '人工编辑' : activeSection.generation_mode === 'generated' ? '系统草稿' : '未填写' }}</span>
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
                  <small>{{ evidence.source?.asin || formatDate(evidence.source?.collected_at || evidence.source?.scraped_at) }}</small>
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

      <el-drawer v-model="draftVisible" title="百科草稿建议" size="min(720px, 92vw)">
        <div v-loading="draftLoading" class="draft-list">
          <div v-for="item in suggestions" :key="item.section_key" class="draft-item">
            <el-checkbox v-model="item.selected">
              <strong>{{ item.title }}</strong>
            </el-checkbox>
            <el-tag v-if="item.missing_evidence" type="warning" size="small">证据待补充</el-tag>
            <p>{{ item.content }}</p>
            <span>{{ item.evidence_listing_ids.length }} 条证据 · {{ item.evidence_source_ids.length }} 条来源</span>
          </div>
        </div>
        <template #footer>
          <el-button @click="draftVisible = false">取消</el-button>
          <el-button type="primary" @click="applyDraft">应用选中模块</el-button>
        </template>
      </el-drawer>

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
