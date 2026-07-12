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

function loadNotes() {
  try {
    const saved = localStorage.getItem('encyclopedia_notes')
    if (saved) notes.value = JSON.parse(saved)
  } catch { /* ignore */ }
}

function saveNotes() {
  localStorage.setItem('encyclopedia_notes', JSON.stringify(notes.value))
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

onMounted(loadNotes)

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
    <el-empty v-else description="还没有笔记。在浏览品类百科时，点击「新建笔记」记录你的选品想法。" :image-size="80" />

    <!-- 新建笔记对话框 -->
    <el-dialog v-model="showAddDialog" title="新建笔记" width="min(560px, 92vw)">
      <el-form label-position="top">
        <el-form-item label="关联品类">
          <el-select v-model="newNote.categoryCode" placeholder="选择品类" style="width: 100%">
            <el-option v-for="c in categories.filter(c => !c.parent_code)" :key="c.code" :label="c.name" :value="c.code" />
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
