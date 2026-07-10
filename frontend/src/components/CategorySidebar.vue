<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowDown, ArrowRight, Document, FolderOpened } from '@element-plus/icons-vue'
import type { CategorySummary } from '../types'

const props = defineProps<{
  categories: CategorySummary[]
  selectedCode: string
  query: string
}>()
const emit = defineEmits<{ select: [code: string] }>()

const collapsed = ref<Set<string>>(new Set())

function toggleCollapse(code: string) {
  const next = new Set(collapsed.value)
  if (next.has(code)) next.delete(code)
  else next.add(code)
  collapsed.value = next
}

function isCollapsed(code: string) {
  return collapsed.value.has(code)
}

const roots = computed(() => props.categories.filter((item) => !item.parent_code))

function statusColor(status: string) {
  if (status === 'published') return '#4d9466'
  if (status === 'pending_review') return '#ff7d00'
  if (status === 'approved') return '#4d9466'
  return '#86909c'
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    data_preparation: '准备',
    draft: '草稿',
    pending_review: '审核',
    approved: '通过',
    published: '已发',
  }
  return labels[status] || status
}
</script>

<template>
  <aside class="category-sidebar">
    <div class="sidebar-label">品类目录</div>
    <div v-if="!roots.length" class="sidebar-empty">暂无匹配品类</div>
    <nav class="tree-nav">
      <div v-for="root in roots" :key="root.code" class="tree-node">
        <div class="tree-row">
          <button
            v-if="root.children.length"
            class="tree-arrow"
            @click.stop="toggleCollapse(root.code)"
          >
            <el-icon v-if="!isCollapsed(root.code)"><ArrowDown /></el-icon>
            <el-icon v-else><ArrowRight /></el-icon>
          </button>
          <span v-else class="tree-arrow-placeholder"></span>
          <button
            class="tree-btn"
            :class="{ active: selectedCode === root.code }"
            @click="emit('select', root.code)"
          >
            <el-icon class="tree-icon"><FolderOpened /></el-icon>
            <span class="tree-text">{{ root.name }}</span>
            <span class="tree-status" :style="{ background: statusColor(root.workflow_status) }"></span>
          </button>
        </div>
        <div v-if="root.children.length && !isCollapsed(root.code)" class="tree-children">
          <button
            v-for="child in root.children"
            :key="child.code"
            class="tree-btn tree-child-btn"
            :class="{ active: selectedCode === child.code }"
            @click="emit('select', child.code)"
          >
            <el-icon class="tree-icon"><Document /></el-icon>
            <span class="tree-text">{{ child.name }}</span>
            <span class="tree-status small" :style="{ background: statusColor(child.workflow_status) }"></span>
          </button>
        </div>
      </div>
    </nav>
  </aside>
</template>
