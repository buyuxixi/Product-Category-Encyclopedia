<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete, Download } from '@element-plus/icons-vue'
import { type Identity } from '../api'
import type { CategorySummary } from '../types'

const props = defineProps<{ identity: Identity; categories: CategorySummary[]; presetCategory?: string | null }>()
const emit = defineEmits<{ select: [code: string] }>()

interface Note {
  id: string
  category: string
  categoryCode: string
  tag: string
  content: string
  createdAt: string
}

const notes = ref<Note[]>([])
const showAddDialog = ref(false)
const newNote = ref({ categoryCode: '', tag: '选品机会', content: '' })
const NOTES_STORAGE_KEY = 'encyclopedia_notes'
const NOTES_SEEDED_KEY = 'encyclopedia_notes_seeded_v1'

const tagLabels: Record<string, string> = {
  '选品机会': '🎯 选品机会',
  '竞品分析': '🔍 竞品分析',
  '用户洞察': '💡 用户洞察',
  '技术趋势': '📈 技术趋势',
  '其他': '📝 其他',
}
const tagTypes: Record<string, string> = {
  '选品机会': 'success',
  '竞品分析': 'warning',
  '用户洞察': 'primary',
  '技术趋势': 'info',
  '其他': '',
}

/** 首次进入时空列表种入示例笔记，便于演示；用户清空后不再自动回填 */
function buildDemoNotes(): Note[] {
  const hoursAgo = (h: number) => new Date(Date.now() - h * 3600000).toISOString()
  return [
    {
      id: 'demo-1',
      category: '电疗 TENS',
      categoryCode: 'TENS_THERAPY',
      tag: '选品机会',
      content:
        '无线 TENS + 加热二合一仍是空白带：Amazon 评论高频吐槽「贴片不粘 / 线材缠绕」，可做磁吸电极式电极 + APP 预设模式，客单价冲 $39–$59。',
      createdAt: hoursAgo(2),
    },
    {
      id: 'demo-2',
      category: '夜间照明-夜灯',
      categoryCode: 'NIGHT_LIGHT',
      tag: '竞品分析',
      content:
        'GE SleepLite / AUVON 主打暖黄低蓝光，但缺少「起床模式」渐亮。可对标做日出模拟 + 人体感应双模，差异化卖点更清晰。',
      createdAt: hoursAgo(8),
    },
    {
      id: 'demo-3',
      category: '坐垫健康-办公坐垫',
      categoryCode: 'SEAT_CUSHION',
      tag: '用户洞察',
      content:
        '久坐办公人群最在意的是「下午不塌陷」和「夏天不闷热」。凝胶网格比纯记忆棉差评更少；航空便携充气垫可作为第二 SKU 切入差旅场景。',
      createdAt: hoursAgo(20),
    },
    {
      id: 'demo-4',
      category: '肩颈热敷',
      categoryCode: 'SHOULDER_NECK_HEAT_THERAPY',
      tag: '技术趋势',
      content:
        '石墨烯快热 + USB-C 供电成为新标配；远红外宣称需注意合规表述。建议 Listing 强调升温曲线与安全自动断电，而非医疗疗效。',
      createdAt: hoursAgo(36),
    },
    {
      id: 'demo-5',
      category: '药物管理-药盒',
      categoryCode: 'PILL_ORGANIZER',
      tag: '选品机会',
      content:
        '智能药盒「提醒准时吃」需求稳定，但老人场景要极简交互。可考虑大字屏 + 语音播报 + 子女端 App 远程确认，避开纯蓝牙复杂配对。',
      createdAt: hoursAgo(52),
    },
    {
      id: 'demo-6',
      category: '远红外热疗',
      categoryCode: 'FAR_INFRARED',
      tag: '竞品分析',
      content:
        'UTK / RENPHO 大尺寸加热垫卷价格战。中尺寸肩颈专用 + 可水洗外套更易做溢价；关注退货原因里「味道 / 过热」占比。',
      createdAt: hoursAgo(70),
    },
    {
      id: 'demo-7',
      category: '热疗',
      categoryCode: 'HEAT_THERAPY',
      tag: '其他',
      content:
        '下周同步运营：把 Rufus / 搜索建议里「labour pain relief」「period cramps heat pad」相关意图词并入广告词库，先跑小预算测转化。',
      createdAt: hoursAgo(96),
    },
    {
      id: 'demo-8',
      category: '电疗 TENS',
      categoryCode: 'TENS_THERAPY',
      tag: '用户洞察',
      content:
        '小红书侧「贴片不粘 / 皮肤灼伤 / 没效果」吐槽集中。选品时优先验证电极材质与电流档位说明是否清晰，客服话术要前置预期管理。',
      createdAt: hoursAgo(120),
    },
  ]
}

function loadNotes() {
  try {
    const saved = localStorage.getItem(NOTES_STORAGE_KEY)
    if (saved) notes.value = JSON.parse(saved)
  } catch { /* ignore */ }

  if (notes.value.length === 0 && !localStorage.getItem(NOTES_SEEDED_KEY)) {
    notes.value = buildDemoNotes()
    saveNotes()
    localStorage.setItem(NOTES_SEEDED_KEY, '1')
  }
}

function saveNotes() {
  localStorage.setItem(NOTES_STORAGE_KEY, JSON.stringify(notes.value))
}

function addNote() {
  if (!newNote.value.content.trim() || !newNote.value.categoryCode) return
  const cat = props.categories.find(c => c.code === newNote.value.categoryCode)
  const note: Note = {
    id: Date.now().toString(),
    category: cat?.name || newNote.value.categoryCode,
    categoryCode: newNote.value.categoryCode,
    tag: newNote.value.tag,
    content: newNote.value.content.trim(),
    createdAt: new Date().toISOString(),
  }
  notes.value.unshift(note)
  saveNotes()
  newNote.value = { categoryCode: '', tag: '选品机会', content: '' }
  showAddDialog.value = false
  ElMessage.success('笔记已保存')
}

function deleteNote(id: string) {
  notes.value = notes.value.filter(n => n.id !== id)
  saveNotes()
  ElMessage.success('已删除')
}

function exportNotes() {
  let md = '# 选品笔记\n\n'
  for (const note of notes.value) {
    md += `## ${tagLabels[note.tag] || note.tag} — ${note.category}\n\n`
    md += `${note.content}\n\n`
    md += `> ${new Date(note.createdAt).toLocaleString('zh-CN')}\n\n---\n\n`
  }
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `选品笔记-${Date.now()}.md`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出 Markdown')
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 3600000
  if (diff < 1) return `${Math.floor(diff * 60)}分钟前`
  if (diff < 24) return `${Math.floor(diff)}小时前`
  return `${Math.floor(diff / 24)}天前`
}

const notesByTag = computed(() => {
  const groups: Record<string, Note[]> = {}
  for (const note of notes.value) {
    if (!groups[note.tag]) groups[note.tag] = []
    groups[note.tag].push(note)
  }
  return groups
})

onMounted(() => {
  loadNotes()
  // 如果没有笔记，显示引导提示
  if (notes.value.length === 0) {
    showGuide.value = true
  }
})

const showGuide = ref(false)

// 从品类详情页跳转来时，自动弹出新建笔记对话框
watch(() => props.presetCategory, (code) => {
  if (code) {
    newNote.value.categoryCode = code
    showAddDialog.value = true
  }
}, { immediate: true })
</script>

<template>
  <main class="dashboard-page">
    <!-- 顶部操作栏 -->
    <div class="notes-toolbar">
      <h2>📋 选品笔记</h2>
      <div class="notes-actions">
        <span class="notes-count">{{ notes.length }} 条笔记</span>
        <el-button :icon="Plus" type="primary" size="small" @click="showAddDialog = true">新建笔记</el-button>
        <el-button :icon="Download" size="small" @click="exportNotes" :disabled="!notes.length">导出</el-button>
      </div>
    </div>

    <!-- 笔记列表 -->
    <div v-if="notes.length" class="notes-list">
      <div v-for="note in notes" :key="note.id" class="note-card" :class="`tag-${note.tag}`">
        <div class="note-header">
          <el-tag :type="tagTypes[note.tag] as any" size="small">{{ tagLabels[note.tag] }}</el-tag>
          <span class="note-category" @click="emit('select', note.categoryCode)">{{ note.category }} →</span>
          <span class="note-time">{{ formatTime(note.createdAt) }}</span>
          <el-button text :icon="Delete" size="small" @click="deleteNote(note.id)" class="note-delete" />
        </div>
        <p class="note-content">{{ note.content }}</p>
      </div>
    </div>
    <div v-if="!notes.length && showGuide" class="notes-guide">
      <h3>📋 如何使用选品笔记？</h3>
      <div class="guide-steps">
        <div class="guide-step">
          <span class="guide-num">1</span>
          <div><strong>浏览品类百科</strong><p>在「品类百科」中查看各品类的用户画像、技术趋势和热点数据</p></div>
        </div>
        <div class="guide-step">
          <span class="guide-num">2</span>
          <div><strong>记录选品想法</strong><p>点击品类详情页的「📝 添加笔记」按钮，快速记录想法</p></div>
        </div>
        <div class="guide-step">
          <span class="guide-num">3</span>
          <div><strong>标签分类管理</strong><p>用 5 种标签（选品机会/竞品分析/用户洞察/技术趋势/其他）分类</p></div>
        </div>
        <div class="guide-step">
          <span class="guide-num">4</span>
          <div><strong>导出汇报</strong><p>一键导出 Markdown 格式的笔记汇总，用于团队汇报</p></div>
        </div>
      </div>
      <el-button type="primary" :icon="Plus" @click="showAddDialog = true">立即创建第一条笔记</el-button>
    </div>
    <el-empty v-else-if="!notes.length" description="还没有笔记" :image-size="60" />

    <!-- 新建笔记对话框 -->
    <el-dialog v-model="showAddDialog" title="新建笔记" width="min(560px, 92vw)">
      <el-form label-position="top">
        <el-form-item label="关联品类">
          <el-select v-model="newNote.categoryCode" placeholder="选择品类" style="width: 100%">
            <el-option v-for="c in categories" :key="c.code" :label="c.name" :value="c.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="newNote.tag" style="width: 100%">
            <el-option v-for="t in Object.keys(tagLabels)" :key="t" :label="tagLabels[t]" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="newNote.content" type="textarea" :rows="4" placeholder="记录你的选品想法、竞品观察、用户洞察..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addNote">保存</el-button>
      </template>
    </el-dialog>
  </main>
</template>
