<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Promotion, Plus, Loading, ChatDotRound, DataLine, WarningFilled } from '@element-plus/icons-vue'
import { apiRequest, apiStreamChat, type Identity } from '../api'
import { renderMarkdown } from '../lib/markdown'
import type { AgentScan, ProductDiscovery, AgentMessage, CategorySummary } from '../types'

const props = defineProps<{ identity: Identity }>()

const loading = ref(false)
const chatLoading = ref(false)
const scanning = ref(false)
const scans = ref<AgentScan[]>([])
const currentScan = ref<AgentScan | null>(null)
const categories = ref<CategorySummary[]>([])
const discoveries = ref<ProductDiscovery[]>([])
const messages = ref<AgentMessage[]>([])
const chatInput = ref('')
let chatAbortController: AbortController | null = null

const scanType = ref<'full' | 'category' | 'topic'>('full')
const selectedCategory = ref('')
const topicInput = ref('')
const showScanPanel = ref(false)
const chatScrollRef = ref<HTMLElement | null>(null)
// 中间区域tab: chat=纯对话, discoveries=发现列表
const mainTab = ref<'chat' | 'discoveries'>('chat')
const showErrorDetails = ref(false)

const opportunityTypeLabel: Record<string, string> = {
  hot_product: '🔥 爆品', rising_trend: '📈 上升趋势',
  gap_opportunity: '🎯 机会空白', emerging_category: '🚀 新兴品类',
}
const opportunityColor: Record<string, string> = {
  hot_product: '#e63757', rising_trend: '#1aae39',
  gap_opportunity: '#7c3aed', emerging_category: '#f5a623',
}
const statusLabel: Record<string, string> = {
  new: '新发现', reviewed: '已查看', selected: '已选中', archived: '已归档',
}

function scoreColor(s: number | null): string {
  if (s === null) return '#a39e98'
  if (s >= 80) return '#1aae39'; if (s >= 60) return '#f5a623'
  if (s >= 40) return '#dd5b00'; return '#a39e98'
}

onMounted(async () => { await Promise.all([loadCategories(), loadScans()]) })

async function loadCategories() {
  try { const res = await apiRequest<{ items: CategorySummary[] }>('/categories'); categories.value = res.items } catch {}
}

async function loadScans() {
  loading.value = true
  try {
    // `_route=v2` 绕过旧 Nginx 尾斜杠配置留下的浏览器 301 永久重定向缓存。
    const res = await apiRequest<{ items: AgentScan[] }>('/agent/scans?limit=100&_route=v2')
    scans.value = res.items
    if (res.items.length > 0 && !currentScan.value) await openScan(res.items[0].id)
  } catch (e) { ElMessage.error((e as Error).message) }
  finally { loading.value = false }
}

async function openScan(id: number) {
  loading.value = true
  try {
    const d = await apiRequest<AgentScan>(`/agent/scans/${id}`)
    currentScan.value = d
    discoveries.value = d.discoveries || []
    messages.value = d.messages || []
    mainTab.value = 'chat'
    showErrorDetails.value = false
    await nextTick(); scrollToBottom()
  } catch (e) { ElMessage.error((e as Error).message) }
  finally { loading.value = false }
}

async function triggerScan() {
  scanning.value = true
  try {
    const body: Record<string, unknown> = { scan_type: scanType.value }
    if (scanType.value === 'category' && selectedCategory.value) body.category_code = selectedCategory.value
    if (scanType.value === 'topic' && topicInput.value.trim()) body.topic = topicInput.value.trim()
    const r = await apiRequest<AgentScan>('/agent/scan', { method: 'POST', body: JSON.stringify(body) })
    currentScan.value = r; discoveries.value = r.discoveries || []; messages.value = r.messages || []
    scans.value.unshift(r); showScanPanel.value = false
    mainTab.value = 'discoveries'
    ElMessage.success('扫描完成')
  } catch (e) { ElMessage.error((e as Error).message) }
  finally { scanning.value = false }
}

async function retryScan() {
  if (!currentScan.value || scanning.value) return
  scanning.value = true
  showErrorDetails.value = false
  try {
    const body: Record<string, unknown> = { scan_type: currentScan.value.scan_type }
    if (currentScan.value.scan_type === 'category' && currentScan.value.category_code)
      body.category_code = currentScan.value.category_code
    if (currentScan.value.scan_type === 'topic' && currentScan.value.topic)
      body.topic = currentScan.value.topic
    const r = await apiRequest<AgentScan>('/agent/scan', { method: 'POST', body: JSON.stringify(body) })
    currentScan.value = r; discoveries.value = r.discoveries || []; messages.value = r.messages || []
    scans.value.unshift(r)
    if (r.status === 'completed') { mainTab.value = 'discoveries'; ElMessage.success('扫描完成') }
    else if (r.status === 'failed') { mainTab.value = 'chat'; ElMessage.warning('扫描仍失败，请检查LLM服务') }
  } catch (e) { ElMessage.error((e as Error).message) }
  finally { scanning.value = false }
}

const failErrorMessage = computed(() => {
  const msg = currentScan.value?.error_message || '未记录具体错误'
  return msg.length > 120 ? msg.slice(0, 120) + '…' : msg
})

async function sendChat() {
  if (!chatInput.value.trim() || !currentScan.value || chatLoading.value) return
  const userMsg = chatInput.value.trim()
  chatInput.value = ''
  chatLoading.value = true
  mainTab.value = 'chat'
  const controller = new AbortController()
  chatAbortController = controller

  messages.value.push({
    id: -Date.now(),
    role: 'user',
    content: userMsg,
    created_at: new Date().toISOString(),
  })
  const assistantId = Date.now()
  const assistantIdx = messages.value.length
  messages.value.push({
    id: assistantId,
    role: 'assistant',
    content: '',
    created_at: new Date().toISOString(),
  })
  await nextTick()
  scrollToBottom()

  try {
    await apiStreamChat(
      `/agent/scans/${currentScan.value.id}/chat/stream`,
      { message: userMsg },
      (event) => {
        const msg = messages.value[assistantIdx]
        if (!msg) return
        if (event.event === 'text-delta') {
          const delta = event.data?.delta || event.data?.textDelta || ''
          if (delta) {
            msg.content += delta
            nextTick(() => scrollToBottom())
          }
        } else if (event.event === 'error') {
          const err = event.data?.message || '对话失败'
          msg.content = msg.content ? `${msg.content}\n\n错误：${err}` : `错误：${err}`
        } else if (event.event === 'done' && event.data?.content && !msg.content) {
          msg.content = event.data.content
        }
      },
      controller.signal,
    )
    const final = messages.value[assistantIdx]
    if (final && !final.content.trim()) {
      final.content = '（空回复）'
    }
  } catch (e) {
    if (!controller.signal.aborted) {
      const msg = messages.value[assistantIdx]
      if (msg) {
        msg.content = msg.content
          ? `${msg.content}\n\n错误：${(e as Error).message}`
          : `错误：${(e as Error).message}`
      }
    } else {
      const msg = messages.value[assistantIdx]
      if (msg && !msg.content.trim()) msg.content = '（已中断）'
    }
  } finally {
    if (chatAbortController === controller) chatAbortController = null
    chatLoading.value = false
    await nextTick()
    scrollToBottom()
  }
}

function stopChat() {
  chatAbortController?.abort()
  chatAbortController = null
  chatLoading.value = false
}

function onChatKeydown(e: KeyboardEvent) {
  if (e.key !== 'Enter' || e.shiftKey) return
  if (e.isComposing || (e as KeyboardEvent & { keyCode?: number }).keyCode === 229) return
  e.preventDefault()
  void sendChat()
}

function escapeUserText(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

function scrollToBottom() { const el = chatScrollRef.value; if (el) el.scrollTop = el.scrollHeight }

// 点击右侧横线——只在messages容器内滚动，不动外部布局
function jumpToMessage(msgId: number) {
  mainTab.value = 'chat'
  nextTick(() => {
    const container = chatScrollRef.value
    const msgEl = container?.querySelector(`[data-msg-id="${msgId}"]`) as HTMLElement | null
    if (container && msgEl) {
      // 只滚动messages容器，不用scrollIntoView（会滚动所有父级）
      container.scrollTop = msgEl.offsetTop - container.offsetTop - 60
    }
  })
}

async function updateDiscoveryStatus(d: ProductDiscovery, status: string) {
  try {
    const r = await apiRequest<ProductDiscovery>(`/agent/discoveries/${d.id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
    const i = discoveries.value.findIndex(x => x.id === d.id); if (i >= 0) Object.assign(discoveries.value[i], r)
    ElMessage.success('已更新')
  } catch (e) { ElMessage.error((e as Error).message) }
}

async function addDiscoveryNote(d: ProductDiscovery) {
  try {
    const { value } = await ElMessageBox.prompt('备注：', '添加备注', { confirmButtonText: '保存', cancelButtonText: '取消', inputValue: d.user_note || '' })
    const r = await apiRequest<ProductDiscovery>(`/agent/discoveries/${d.id}`, { method: 'PATCH', body: JSON.stringify({ user_note: value }) })
    const i = discoveries.value.findIndex(x => x.id === d.id); if (i >= 0) Object.assign(discoveries.value[i], r)
    ElMessage.success('已保存')
  } catch {}
}

function scanTitle(s: AgentScan): string {
  if (s.scan_type === 'full') return '全品类扫描'
  if (s.scan_type === 'category') return s.category_code || '品类扫描'
  return s.topic || '话题探索'
}

function scanPreview(s: AgentScan): string {
  if (s.report?.summary) return s.report.summary.slice(0, 60)
  if (s.status === 'failed') return s.error_message || '扫描失败'
  return '...'
}

// 右侧历史对话索引——只取user消息，不要AI回复
const conversationIndex = computed(() => {
  return messages.value
    .filter(m => m.role === 'user')
    .map((m, i) => ({
      id: m.id,
      index: i,
      preview: m.content.slice(0, 40),
      time: new Date(m.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }),
    }))
})

const stats = computed(() => {
  const total = discoveries.value.length
  let avg = 0, n = 0
  for (const d of discoveries.value) if (d.opportunity_score !== null) { avg += d.opportunity_score; n++ }
  return { total, avgScore: n > 0 ? Math.round(avg / n) : 0 }
})
</script>

<template>
  <div class="agent-view">
    <!-- ========== 左侧：对话列表 ========== -->
    <aside class="sidebar">
      <button class="new-chat-btn" @click="showScanPanel = !showScanPanel">
        <el-icon><Plus /></el-icon> 发起选品扫描
      </button>

      <div v-if="showScanPanel" class="scan-panel">
        <div class="scan-modes">
          <button :class="{ active: scanType === 'full' }" @click="scanType = 'full'">全站</button>
          <button :class="{ active: scanType === 'category' }" @click="scanType = 'category'">品类</button>
          <button :class="{ active: scanType === 'topic' }" @click="scanType = 'topic'">话题</button>
        </div>
        <select v-if="scanType === 'category'" v-model="selectedCategory" class="scan-input">
          <option value="">选择品类…</option>
          <template v-for="cat in categories.filter(c => !c.parent_code)" :key="cat.code">
            <option :value="cat.code">{{ cat.name }}</option>
            <option v-for="ch in cat.children" :key="ch.code" :value="ch.code">  {{ ch.name }}</option>
          </template>
        </select>
        <input v-if="scanType === 'topic'" v-model="topicInput" placeholder="如：便携风扇…" class="scan-input" @keydown.enter="triggerScan" />
        <button class="scan-go" :disabled="scanning || (scanType === 'category' && !selectedCategory) || (scanType === 'topic' && !topicInput.trim())" @click="triggerScan">
          <el-icon v-if="scanning" class="is-loading"><Loading /></el-icon>
          {{ scanning ? 'AI分析中…' : '开始扫描' }}
        </button>
      </div>

      <div class="conv-list">
        <div v-if="!scans.length" class="conv-empty">暂无对话</div>
        <button v-for="s in scans" :key="s.id" class="conv-item" :class="{ active: currentScan?.id === s.id }" @click="openScan(s.id)">
          <div class="conv-title">{{ scanTitle(s) }}</div>
          <div class="conv-preview">{{ scanPreview(s) }}</div>
          <div class="conv-meta">
            <span :class="s.status">{{ s.status === 'completed' ? '✓' : s.status === 'failed' ? '✗' : '⏳' }}</span>
            <span class="conv-time">{{ new Date(s.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }}</span>
          </div>
        </button>
      </div>
    </aside>

    <!-- ========== 中间：聊天/发现区（tab切换） ========== -->
    <main class="main-area">
      <div v-if="!currentScan" class="empty-state">
        <div class="empty-icon"><el-icon :size="40"><Promotion /></el-icon></div>
        <h3>选品Agent</h3>
        <p>左侧发起扫描，或点击历史对话</p>
      </div>

      <template v-else>
        <!-- 失败状态：紧凑错误栏 -->
        <div v-if="currentScan.status === 'failed'" class="fail-banner">
          <el-icon class="fail-banner-icon"><WarningFilled /></el-icon>
          <span class="fail-banner-text">{{ failErrorMessage }}</span>
          <button class="fail-banner-retry" :disabled="scanning" @click="retryScan">
            <el-icon v-if="scanning" class="is-loading"><Loading /></el-icon>
            {{ scanning ? '重试中…' : '重新扫描' }}
          </button>
          <button class="fail-banner-detail" @click="showErrorDetails = !showErrorDetails">
            {{ showErrorDetails ? '收起' : '详情' }}
          </button>
        </div>
        <!-- 可折叠的完整错误信息 -->
        <div v-if="currentScan.status === 'failed' && showErrorDetails" class="fail-detail-bar">
          <pre>{{ currentScan.error_message || '未记录具体错误' }}</pre>
        </div>

        <!-- 成功扫描的Tab栏（失败时不显示发现tab） -->
        <div v-if="currentScan.status !== 'failed'" class="tab-bar">
          <button :class="{ active: mainTab === 'chat' }" @click="mainTab = 'chat'">
            <el-icon><ChatDotRound /></el-icon> 对话
          </button>
          <button :class="{ active: mainTab === 'discoveries' }" @click="mainTab = 'discoveries'">
            <el-icon><DataLine /></el-icon> 发现 ({{ discoveries.length }})
          </button>
        </div>

        <!-- Tab 内容：对话 / 发现互斥，各占满中间区域 -->
        <div
          v-show="mainTab === 'chat' || currentScan.status === 'failed'"
          class="chat-container"
        >
          <div class="messages" ref="chatScrollRef">
            <!-- 失败时如果没有对话消息，显示引导卡 -->
            <div v-if="currentScan.status === 'failed' && !messages.length" class="chat-guide">
              <div class="guide-icon">💬</div>
              <p>扫描失败，但你仍可以提问</p>
              <ul>
                <li>「{{ scanTitle(currentScan) }}这个品类的市场概况是什么？」</li>
                <li>「有哪些值得关注的产品方向？」</li>
                <li>「帮我分析这个品类的竞争格局」</li>
              </ul>
            </div>
            <div v-for="msg in messages" :key="msg.id" class="msg" :class="msg.role" :data-msg-id="msg.id">
              <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
              <div class="msg-content">
                <div class="msg-time">{{ new Date(msg.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }}</div>
                <div
                  v-if="msg.role === 'assistant' && !msg.content && chatLoading"
                  class="msg-bubble loading"
                >
                  <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                  <button class="stop-btn" type="button" @click="stopChat">停止</button>
                </div>
                <div
                  v-else
                  class="msg-bubble"
                  :class="{ streaming: msg.role === 'assistant' && chatLoading && msg === messages[messages.length - 1] }"
                  v-html="msg.role === 'assistant' ? renderMarkdown(msg.content) : escapeUserText(msg.content)"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <div
          v-show="mainTab === 'discoveries' && currentScan.status !== 'failed'"
          class="discoveries-container"
        >
          <div v-if="!discoveries.length" class="disc-empty">本次扫描暂无发现</div>
          <div class="disc-stats" v-if="discoveries.length">
            <div class="stat"><span class="stat-num">{{ stats.total }}</span><span class="stat-label">发现</span></div>
            <div class="stat"><span class="stat-num" :style="{ color: scoreColor(stats.avgScore) }">{{ stats.avgScore }}</span><span class="stat-label">均分</span></div>
          </div>
          <div class="disc-list">
            <div v-for="d in discoveries" :key="d.id" class="disc-card">
              <div class="disc-top">
                <span class="disc-type" :style="{ background: (opportunityColor[d.opportunity_type]||'#888')+'20', color: opportunityColor[d.opportunity_type]||'#888' }">
                  {{ opportunityTypeLabel[d.opportunity_type] || d.opportunity_type }}
                </span>
                <span class="disc-score" :style="{ color: scoreColor(d.opportunity_score) }">{{ d.opportunity_score ?? '—' }}</span>
              </div>
              <div class="disc-name">{{ d.product_name }}</div>
              <div class="disc-reason">{{ d.reasoning }}</div>
              <div v-if="d.keywords?.length" class="disc-kws">
                <span v-for="kw in d.keywords.slice(0,5)" :key="kw" class="kw">{{ kw }}</span>
              </div>
              <div v-if="d.source_links?.length" class="disc-links">
                <a
                  v-for="(src,i) in d.source_links.slice(0,3)"
                  :key="i"
                  :href="src.url"
                  :title="src.title || src.url"
                  target="_blank"
                  rel="noreferrer noopener"
                  class="src-link"
                >{{ src.title || src.platform }} ↗</a>
              </div>
              <div class="disc-actions">
                <button @click="updateDiscoveryStatus(d,'reviewed')">查看</button>
                <button @click="updateDiscoveryStatus(d,'selected')">选中</button>
                <button @click="addDiscoveryNote(d)">备注</button>
                <span class="disc-status-tag" :class="d.status">{{ statusLabel[d.status]||d.status }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入框固定在主区域底部，始终全宽 -->
        <div class="input-bar">
          <input
            v-model="chatInput"
            placeholder="输入问题，Enter发送…"
            @keydown="onChatKeydown"
            :disabled="chatLoading"
          />
          <button v-if="chatLoading" class="send stop" @click="stopChat">停止</button>
          <button v-else class="send" @click="sendChat" :disabled="!chatInput.trim()">
            <el-icon><Promotion /></el-icon>
          </button>
        </div>
      </template>
    </main>

    <!-- ========== 右侧：用户消息索引（Hermes式竖线刻度） ========== -->
    <aside class="msg-index" v-if="currentScan && conversationIndex.length">
      <div class="mi-list">
        <button
          v-for="(item, i) in conversationIndex"
          :key="item.id"
          class="mi-mark"
          :title="item.preview"
          @click="jumpToMessage(item.id)"
        >
          <span class="mi-tick"></span>
          <span class="mi-label">{{ i + 1 }}</span>
        </button>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.agent-view { display: flex; flex: 1; min-width: 0; width: 100%; height: calc(100vh - 52px); overflow: hidden; min-height: 0; }

/* === 左侧：对话列表 === */
.sidebar { width: 240px; flex-shrink: 0; border-right: 1px solid #e5e5e2; display: flex; flex-direction: column; overflow: hidden; background: #fafaf8; }
.new-chat-btn { margin: 10px; padding: 9px; display: flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid #1aae39; border-radius: 8px; background: #1aae3910; color: #1aae39; font-size: 13px; font-weight: 600; cursor: pointer; flex-shrink: 0; }
.new-chat-btn:hover { background: #1aae3920; }

.scan-panel { padding: 0 10px 10px; border-bottom: 1px solid #eee; flex-shrink: 0; }
.scan-modes { display: flex; gap: 4px; margin-bottom: 6px; }
.scan-modes button { flex: 1; padding: 5px 0; border: 1px solid #ddd; border-radius: 6px; background: #fff; font-size: 12px; color: #666; cursor: pointer; }
.scan-modes button.active { border-color: #1aae39; color: #1aae39; font-weight: 600; background: #1aae3910; }
.scan-input { width: 100%; padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; margin-bottom: 6px; outline: none; background: #fff; }
.scan-input:focus { border-color: #1aae39; }
.scan-go { width: 100%; padding: 7px; background: #1aae39; color: #fff; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px; }
.scan-go:disabled { opacity: 0.5; cursor: not-allowed; }

.conv-list { flex: 1; overflow-y: auto; }
.conv-empty { padding: 20px 12px; text-align: center; color: #b0aaa5; font-size: 13px; }
.conv-item { width: 100%; text-align: left; padding: 8px 12px; border: none; border-left: 3px solid transparent; background: transparent; cursor: pointer; transition: background 0.1s; }
.conv-item:hover { background: #f0efed; }
.conv-item.active { border-left-color: #1aae39; background: #1aae3908; }
.conv-title { font-size: 13px; font-weight: 600; color: #2a2520; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-preview { font-size: 11px; color: #8a8580; margin: 1px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-meta { display: flex; align-items: center; gap: 6px; font-size: 10px; }
.conv-meta .completed { color: #1aae39; } .conv-meta .failed { color: #e63757; }
.conv-time { color: #b0aaa5; }

/* === 中间：主区域 === */
.main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; min-height: 0; }
.empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #8a8580; }
.empty-icon { width: 64px; height: 64px; display: flex; align-items: center; justify-content: center; background: #1aae3910; border-radius: 16px; margin-bottom: 10px; color: #1aae39; }
.empty-state h3 { margin: 0 0 4px; color: #3a3530; font-size: 16px; }
.empty-state p { font-size: 13px; }
.scan-error-banner { margin: 12px 20px 0; padding: 10px 12px; border: 1px solid #f5c2c7; border-radius: 7px; background: #fff5f5; color: #b42318; font-size: 12px; line-height: 1.5; }
.scan-error-banner strong { margin-right: 8px; }

/* 失败状态：紧凑错误栏 */
.fail-banner { display: flex; align-items: center; gap: 8px; padding: 10px 20px; border-bottom: 1px solid #f5c2c7; background: #fef6f6; flex-shrink: 0; }
.fail-banner-icon { color: #e63757; font-size: 16px; flex-shrink: 0; }
.fail-banner-text { flex: 1; min-width: 0; font-size: 13px; color: #b42318; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fail-banner-retry { display: flex; align-items: center; gap: 4px; padding: 5px 14px; border: none; border-radius: 6px; background: #1aae39; color: #fff; font-size: 12px; font-weight: 600; cursor: pointer; flex-shrink: 0; white-space: nowrap; }
.fail-banner-retry:disabled { opacity: 0.5; cursor: not-allowed; }
.fail-banner-retry:hover:not(:disabled) { background: #159030; }
.fail-banner-detail { padding: 5px 12px; border: 1px solid #ddd; border-radius: 6px; background: #fff; font-size: 12px; color: #666; cursor: pointer; flex-shrink: 0; white-space: nowrap; }
.fail-banner-detail:hover { border-color: #aaa; color: #333; }
.fail-detail-bar { padding: 0 20px; border-bottom: 1px solid #eee; background: #fafaf8; flex-shrink: 0; }
.fail-detail-bar pre { margin: 0; padding: 10px 0; font-size: 11px; line-height: 1.5; color: #6a6560; white-space: pre-wrap; word-break: break-word; max-height: 200px; overflow-y: auto; }

/* 失败状态下的聊天引导 */
.chat-guide { margin: 0 auto; max-width: 460px; padding: 24px 20px; text-align: center; }
.chat-guide .guide-icon { font-size: 28px; margin-bottom: 8px; }
.chat-guide p { margin: 0 0 10px; font-size: 13px; font-weight: 600; color: #3a3530; }
.chat-guide ul { margin: 0; padding-left: 0; list-style: none; text-align: left; }
.chat-guide li { font-size: 12px; color: #8a8580; margin: 5px 0; line-height: 1.5; padding-left: 12px; position: relative; }
.chat-guide li::before { content: '›'; position: absolute; left: 0; color: #1aae39; font-weight: 700; }

/* Tab栏 */
.tab-bar { display: flex; align-items: center; gap: 4px; padding: 8px 16px; border-bottom: 1px solid #eee; background: #fff; flex-shrink: 0; }
.tab-bar button { display: flex; align-items: center; gap: 4px; padding: 6px 14px; border: none; background: none; font-size: 13px; color: #8a8580; cursor: pointer; border-bottom: 2px solid transparent; }
.tab-bar button:hover { color: #3a3530; }
.tab-bar button.active { color: #1aae39; border-bottom-color: #1aae39; font-weight: 600; }

/* 聊天容器（与发现列表互斥，各占满中间区域） */
.chat-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; min-height: 0; width: 100%; }
.messages { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 16px 20px; display: flex; flex-direction: column; gap: 14px; min-height: 0; }
.msg { display: flex; gap: 10px; max-width: 75%; }
.msg.user { align-self: flex-end; flex-direction: row-reverse; }
.msg.assistant { align-self: flex-start; }
.msg-avatar { width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 14px; }
.msg-content { display: flex; flex-direction: column; min-width: 0; max-width: 100%; }
.msg.user .msg-content { align-items: flex-end; }
.msg-time { font-size: 10px; color: #b0aaa5; margin-bottom: 2px; }
.msg-bubble { padding: 9px 14px; border-radius: 10px; font-size: 14px; line-height: 1.7; word-break: break-word; }
.msg.user .msg-bubble { background: #1aae39; color: #fff; }
.msg.assistant .msg-bubble { background: #f5f3f0; color: #1a1a1a; }
.msg-bubble.streaming::after {
  content: "▋";
  display: inline-block;
  margin-left: 2px;
  color: #1aae39;
  animation: blink 1s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }
.msg-bubble :deep(h2), .msg-bubble :deep(h3), .msg-bubble :deep(h4), .msg-bubble :deep(h5), .msg-bubble :deep(h6) { margin: 8px 0 4px; font-weight: 600; }
.msg-bubble :deep(h2) { font-size: 15px; } .msg-bubble :deep(h3) { font-size: 14px; } .msg-bubble :deep(h4) { font-size: 13px; }
.msg-bubble :deep(ul), .msg-bubble :deep(ol) { padding-left: 18px; margin: 4px 0; }
.msg-bubble :deep(li) { margin: 2px 0; }
.msg-bubble :deep(p) { margin: 4px 0; }
.msg-bubble :deep(pre), .msg-bubble :deep(.md-code) { background: #e9e7e3; padding: 8px 12px; border-radius: 6px; font-size: 12px; overflow-x: auto; margin: 6px 0; }
.msg-bubble :deep(code) { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.92em; }
.msg-bubble :deep(pre code) { font-size: inherit; }
.msg-bubble :deep(a) { color: #1aae39; text-decoration: none; }
.msg-bubble :deep(strong) { font-weight: 600; }
.msg-bubble :deep(blockquote) { margin: 6px 0; padding: 4px 10px; border-left: 3px solid #1aae39; color: #5a5550; background: #fff; }
.msg-bubble :deep(table.md-table) {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 12px;
  display: block;
  overflow-x: auto;
  max-width: 100%;
}
.msg-bubble :deep(table.md-table th),
.msg-bubble :deep(table.md-table td) {
  border: 1px solid #ddd8d0;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
  white-space: normal;
}
.msg-bubble :deep(table.md-table th) { background: #ebe8e3; font-weight: 600; }
.msg-bubble :deep(hr) { border: none; border-top: 1px solid #ddd8d0; margin: 10px 0; }

.loading { display: flex; align-items: center; gap: 4px; }
.dot { width: 7px; height: 7px; background: #b0aaa5; border-radius: 50%; animation: bounce 1.4s infinite; }
.dot:nth-child(2) { animation-delay: 0.2s; } .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-5px); } }
.stop-btn { margin-left: 8px; padding: 2px 8px; border: 1px solid #e63757; border-radius: 4px; background: #fff; color: #e63757; font-size: 11px; cursor: pointer; }

/* 输入框固定主区域底部，始终全宽 */
.input-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
  padding: 10px 20px;
  border-top: 1px solid #e5e5e2;
  background: #fff;
  flex-shrink: 0;
}
.input-bar input {
  flex: 1 1 0%;
  min-width: 0;
  width: 100%;
  padding: 9px 14px;
  border: 1px solid #ddd;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}
.input-bar input:focus { border-color: #1aae39; }
.send { display: flex; align-items: center; justify-content: center; width: 38px; height: 38px; background: #1aae39; color: #fff; border: none; border-radius: 10px; cursor: pointer; flex-shrink: 0; }
.send:disabled { opacity: 0.4; cursor: not-allowed; }
.send.stop { background: #e63757; width: auto; padding: 0 14px; font-size: 13px; font-weight: 600; }

/* 发现列表 */
.discoveries-container { flex: 1; overflow-y: auto; padding: 16px 20px; min-width: 0; min-height: 0; width: 100%; }
.disc-empty { padding: 40px; text-align: center; color: #b0aaa5; font-size: 14px; }
.disc-stats { display: flex; gap: 16px; margin-bottom: 14px; }
.stat { display: flex; flex-direction: column; align-items: center; }
.stat-num { font-size: 22px; font-weight: 700; color: #3a3530; }
.stat-label { font-size: 11px; color: #8a8580; }
.disc-card { background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 12px; margin-bottom: 10px; transition: box-shadow 0.15s; }
.disc-card:hover { box-shadow: 0 1px 10px rgba(0,0,0,0.06); }
.disc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
.disc-type { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.disc-score { font-size: 20px; font-weight: 700; }
.disc-name { font-size: 14px; font-weight: 600; color: #1a1a1a; margin-bottom: 4px; }
.disc-reason { font-size: 13px; line-height: 1.6; color: #4a4540; margin-bottom: 8px; }
.disc-kws { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px; }
.kw { padding: 2px 6px; background: #1aae3910; border-radius: 3px; font-size: 11px; color: #1aae39; }
.disc-links { display: flex; gap: 8px; margin-bottom: 6px; }
.src-link { font-size: 12px; color: #1aae39; text-decoration: none; }
.src-link:hover { text-decoration: underline; }
.disc-actions { display: flex; gap: 4px; align-items: center; padding-top: 6px; border-top: 1px solid #f5f3f0; }
.disc-actions button { padding: 3px 10px; border: 1px solid #eee; border-radius: 5px; background: #fff; font-size: 12px; color: #666; cursor: pointer; }
.disc-actions button:hover { border-color: #1aae39; color: #1aae39; }
.disc-status-tag { margin-left: auto; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }
.disc-status-tag.new { background: #1aae3910; color: #1aae39; }
.disc-status-tag.reviewed { background: #f5a62310; color: #f5a623; }
.disc-status-tag.selected { background: #7c3aed10; color: #7c3aed; }

/* === 右侧：用户消息索引（Hermes式窄竖线刻度） === */
.msg-index { width: 44px; flex-shrink: 0; border-left: 1px solid #e5e5e2; display: flex; flex-direction: column; overflow: hidden; background: #fafaf8; position: relative; }
.mi-list { flex: 1; overflow-y: auto; padding: 16px 0; display: flex; flex-direction: column; align-items: center; gap: 0; position: relative; }
.mi-list::before { content: ''; position: absolute; left: 50%; top: 0; bottom: 0; width: 1.5px; background: #d5d3ce; transform: translateX(-50%); }
.mi-mark { border: none; background: transparent; cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 14px 0; position: relative; width: 100%; transition: all 0.1s; }
.mi-mark:hover .mi-tick { background: #1aae39; width: 22px; height: 3px; }
.mi-mark:hover .mi-label { color: #1aae39; opacity: 1; font-weight: 600; }
.mi-tick { width: 12px; height: 2.5px; background: #9a958e; border-radius: 2px; transition: all 0.15s; position: relative; z-index: 1; }
.mi-label { font-size: 10px; color: #b0aaa5; opacity: 0.4; transition: all 0.15s; }
</style>
