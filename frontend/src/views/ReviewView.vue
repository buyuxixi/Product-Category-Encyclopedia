<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, CopyDocument, Download, DocumentChecked, View } from '@element-plus/icons-vue'
import { apiRequest, type Identity } from '../api'
import type { VersionDetail, VersionDiff, VersionRecord } from '../types'

const props = defineProps<{ identity: Identity }>()
const emit = defineEmits<{ changed: [] }>()

const versions = ref<VersionRecord[]>([])
const loading = ref(false)
const previewVisible = ref(false)
const previewContent = ref('')
const selectedVersion = ref<VersionDetail | null>(null)
const selectedDiff = ref<VersionDiff | null>(null)
const publishProvider = ref<'local' | 'feishu'>('local')
const feishuPublishEnabled = ref(false)

function statusType(status: string) {
  if (status === 'published' || status === 'approved') return 'success'
  if (status === 'pending_review') return 'warning'
  if (status === 'rejected') return 'danger'
  return 'info'
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending_review: '待审核',
    approved: '已通过',
    rejected: '已退回',
    published: '已发布',
  }
  return labels[status] || status
}

async function loadVersions() {
  loading.value = true
  try {
    const result = await apiRequest<{ items: VersionRecord[] }>('/versions')
    versions.value = result.items
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

async function review(version: VersionRecord, decision: 'approve' | 'reject') {
  try {
    const result = await ElMessageBox.prompt(
      decision === 'approve' ? '可以补充审核意见。' : '退回时必须填写修改意见。',
      decision === 'approve' ? '通过版本' : '退回版本',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        inputValidator: (value) => decision === 'approve' || Boolean(value?.trim()) || '请填写退回原因',
      },
    )
    await apiRequest(
      `/versions/${version.id}/review`,
      { method: 'POST', body: JSON.stringify({ decision, comment: result.value || '' }) },
    )
    ElMessage.success(decision === 'approve' ? '版本已通过' : '版本已退回')
    await loadVersions()
    emit('changed')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error((error as Error).message)
  }
}

async function preview(version: VersionRecord) {
  try {
    const [detail, diff] = await Promise.all([
      apiRequest<VersionDetail>(`/versions/${version.id}`),
      apiRequest<VersionDiff>(`/versions/${version.id}/diff`),
    ])
    selectedVersion.value = detail
    selectedDiff.value = diff
    await loadPreview(version)
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

async function publish(version: VersionRecord) {
  try {
    await apiRequest(
      `/versions/${version.id}/publish`,
      { method: 'POST', body: JSON.stringify({ provider: publishProvider.value }) },
    )
    ElMessage.success(publishProvider.value === 'feishu' ? '已发布到飞书' : '已生成本地发布记录')
    await loadVersions()
    emit('changed')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

async function loadPreview(version: VersionRecord) {
  const result = await apiRequest<{ content: string }>(`/versions/${version.id}/publication-preview`)
  previewContent.value = result.content
  previewVisible.value = true
  return result.content
}

async function copyPreview() {
  try {
    await navigator.clipboard.writeText(previewContent.value)
    ElMessage.success('已复制发布内容')
  } catch {
    ElMessage.error('当前浏览器不允许复制，请使用下载 Markdown')
  }
}

async function downloadPreview() {
  const blob = new Blob([previewContent.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `category-encyclopedia-${Date.now()}.md`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已下载 Markdown 文件')
}

async function loadPublishConfig() {
  try {
    const result = await apiRequest<{ feishu_publish_enabled: boolean }>('/auth/config')
    feishuPublishEnabled.value = result.feishu_publish_enabled
  } catch {
    feishuPublishEnabled.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadVersions(), loadPublishConfig()])
})
</script>

<template>
  <main v-loading="loading" class="page-shell review-page">
    <header class="page-header">
      <div>
        <div class="eyebrow">审核与发布</div>
        <h1>版本审核中心</h1>
        <p>审核的是不可变版本；通过后才能执行单向发布，发布失败不会影响已审核内容。</p>
      </div>
      <el-select v-model="publishProvider" style="width: 150px" aria-label="发布方式">
        <el-option label="本地发布记录" value="local" />
        <el-option v-if="feishuPublishEnabled" label="发布到飞书" value="feishu" />
      </el-select>
    </header>

    <section class="history-section">
      <el-table class="desktop-record-table" :data="versions" stripe empty-text="尚无待审核版本">
        <el-table-column prop="category_name" label="品类" min-width="160" />
        <el-table-column label="版本" width="90"><template #default="scope">v{{ scope.row.version_number }}</template></el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="scope"><el-tag :type="statusType(scope.row.status)">{{ statusLabel(scope.row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_by" label="提交人" width="130" />
        <el-table-column prop="created_at" label="提交时间" min-width="180" />
        <el-table-column label="操作" width="330" fixed="right">
          <template #default="scope">
            <el-button text :icon="View" @click="preview(scope.row)">预览</el-button>
            <template v-if="scope.row.status === 'pending_review' && ['admin', 'reviewer'].includes(identity.role)">
              <el-button text type="success" :icon="CircleCheck" @click="review(scope.row, 'approve')">通过</el-button>
              <el-button text type="danger" @click="review(scope.row, 'reject')">退回</el-button>
            </template>
            <el-button
              v-if="scope.row.status === 'approved' && ['admin', 'reviewer'].includes(identity.role)"
              text
              type="primary"
              :icon="DocumentChecked"
              @click="publish(scope.row)"
            >发布</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="mobile-record-list">
        <article v-for="version in versions" :key="version.id" class="mobile-record-card">
          <header>
            <div>
              <strong>{{ version.category_name }}</strong>
              <span>v{{ version.version_number }}</span>
            </div>
            <el-tag :type="statusType(version.status)">{{ statusLabel(version.status) }}</el-tag>
          </header>
          <dl>
            <div><dt>提交人</dt><dd>{{ version.created_by }}</dd></div>
            <div><dt>提交时间</dt><dd>{{ version.created_at }}</dd></div>
          </dl>
          <footer>
            <el-button text :icon="View" @click="preview(version)">预览</el-button>
            <template v-if="version.status === 'pending_review' && ['admin', 'reviewer'].includes(identity.role)">
              <el-button text type="success" :icon="CircleCheck" @click="review(version, 'approve')">通过</el-button>
              <el-button text type="danger" @click="review(version, 'reject')">退回</el-button>
            </template>
            <el-button
              v-if="version.status === 'approved' && ['admin', 'reviewer'].includes(identity.role)"
              text
              type="primary"
              :icon="DocumentChecked"
              @click="publish(version)"
            >发布</el-button>
          </footer>
        </article>
        <el-empty v-if="!versions.length" description="尚无待审核版本" :image-size="72" />
      </div>
    </section>

    <el-drawer v-model="previewVisible" title="发布内容预览" size="min(720px, 92vw)">
      <div v-if="selectedVersion" class="review-inspector">
        <div class="review-inspector-meta"><strong>{{ selectedVersion.category_name }} · v{{ selectedVersion.version_number }}</strong><span>{{ statusLabel(selectedVersion.status) }}</span></div>
        <div v-for="section in selectedVersion.content_snapshot.sections" :key="section.section_key" class="review-section">
          <header><strong>{{ section.title }}</strong><span>{{ section.evidence.length }} 条证据</span></header>
          <p>{{ section.content || '暂无数据，待补充。' }}</p>
        </div>
        <div v-if="selectedDiff?.previous_version_id" class="review-diff">
          <strong>相对上一版本的变化</strong>
          <p v-if="!selectedDiff.changes.length">没有正文变化。</p>
          <div v-for="change in selectedDiff.changes" :key="change.section_key" class="review-diff-item">
            <span>{{ change.title }}</span>
            <del>{{ change.before || '新增内容' }}</del>
            <ins>{{ change.after || '删除内容' }}</ins>
          </div>
        </div>
      </div>
      <pre class="markdown-preview">{{ previewContent }}</pre>
      <template #footer>
        <el-button :icon="CopyDocument" @click="copyPreview">复制内容</el-button>
        <el-button type="primary" :icon="Download" @click="downloadPreview">下载 Markdown</el-button>
      </template>
    </el-drawer>
  </main>
</template>
