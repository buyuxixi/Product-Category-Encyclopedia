<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, UploadFilled } from '@element-plus/icons-vue'
import { apiRequest, type Identity } from '../api'
import type { ImportCatalogItem, ImportJob } from '../types'

const props = defineProps<{ identity: Identity }>()
const emit = defineEmits<{ changed: [] }>()

const rootPath = ref('/imports')
const catalog = ref<ImportCatalogItem[]>([])
const selectedCodes = ref<string[]>([])
const jobs = ref<ImportJob[]>([])
const importing = ref(false)
const catalogLoading = ref(false)

function statusType(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'completed_with_errors') return 'warning'
  if (status === 'running') return 'primary'
  return 'danger'
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    queued: '排队中',
    running: '导入中',
    completed: '已完成',
    completed_with_errors: '部分失败',
    failed: '失败',
  }
  return labels[status] || status
}

function selectedDirectories() {
  return catalog.value
    .filter((item) => selectedCodes.value.includes(item.code))
    .flatMap((item) => item.directories)
}

async function loadJobs() {
  try {
    const result = await apiRequest<{ items: ImportJob[] }>('/imports')
    jobs.value = result.items
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

async function loadCatalog() {
  catalogLoading.value = true
  try {
    const result = await apiRequest<{ items: ImportCatalogItem[] }>(
      `/imports/catalog?root_path=${encodeURIComponent(rootPath.value)}`,
    )
    catalog.value = result.items
    selectedCodes.value = result.items.map((item) => item.code)
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    catalogLoading.value = false
  }
}

async function startImport() {
  importing.value = true
  try {
    const job = await apiRequest<ImportJob>(
      '/imports/amazon',
      {
        method: 'POST',
        body: JSON.stringify({ root_path: rootPath.value, directories: selectedDirectories() }),
      },
    )
    ElMessage.success(`导入完成：新增 ${job.inserted_count}，重复 ${job.duplicate_count}，失败 ${job.failed_count}`)
    await loadJobs()
    emit('changed')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadJobs(), loadCatalog()])
})
</script>

<template>
  <main class="page-shell import-page">
    <header class="page-header">
      <div>
        <div class="eyebrow">数据与来源中心</div>
        <h1>把数据变成可检索的品类资产</h1>
        <p>系统会按稳定品类编码归并别名目录，按站点、ASIN 和采集时间去重，并保留失败明细。</p>
      </div>
    </header>

    <section class="import-panel">
      <div class="step-heading"><span>01</span><div><h2>选择数据目录</h2><p>当前数据根目录由部署配置提供，业务人员只需要选择要导入的品类。</p></div></div>
      <el-form label-position="top">
        <el-form-item label="数据根目录">
          <div class="path-input-row">
            <el-input v-model="rootPath" />
            <el-button :loading="catalogLoading" :icon="Refresh" @click="loadCatalog">扫描目录</el-button>
          </div>
        </el-form-item>
        <el-form-item label="可导入品类">
          <div v-loading="catalogLoading" class="catalog-grid">
            <el-checkbox-group v-model="selectedCodes" class="directory-grid">
              <label v-for="item in catalog" :key="item.code" class="catalog-card">
                <el-checkbox :value="item.code"><strong>{{ item.name }}</strong></el-checkbox>
                <span>{{ item.file_count }} 个文件</span>
                <small>{{ item.directories.join(' / ') }}</small>
              </label>
            </el-checkbox-group>
            <el-empty v-if="!catalog.length && !catalogLoading" description="没有发现可导入的品类目录" :image-size="72" />
          </div>
        </el-form-item>
        <el-button
          type="primary"
          :icon="UploadFilled"
          :loading="importing"
          :disabled="!selectedCodes.length || !['admin', 'data'].includes(identity.role)"
          @click="startImport"
        >
          导入选中品类
        </el-button>
        <p v-if="!['admin', 'data'].includes(identity.role)" class="permission-note">当前角色仅可查看导入记录。</p>
      </el-form>
    </section>

    <section class="history-section">
      <div class="section-heading"><div><h2>导入记录</h2><p>每次导入都会留下新增、重复和失败的可追溯记录。</p></div><el-button text @click="loadJobs">刷新</el-button></div>
      <el-table class="desktop-record-table" :data="jobs" stripe empty-text="尚无导入记录">
        <el-table-column prop="id" label="任务" width="80" />
        <el-table-column label="状态" width="120">
          <template #default="scope"><el-tag :type="statusType(scope.row.status)">{{ statusLabel(scope.row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="total_count" label="扫描" width="80" />
        <el-table-column prop="inserted_count" label="新增" width="80" />
        <el-table-column prop="duplicate_count" label="重复" width="80" />
        <el-table-column prop="failed_count" label="失败" width="80" />
        <el-table-column prop="created_by" label="操作人" width="140" />
        <el-table-column prop="created_at" label="时间" min-width="190" />
      </el-table>
      <div class="mobile-record-list">
        <article v-for="job in jobs" :key="job.id" class="mobile-record-card">
          <header><div><strong>导入任务 #{{ job.id }}</strong></div><el-tag :type="statusType(job.status)">{{ statusLabel(job.status) }}</el-tag></header>
          <dl class="record-metrics">
            <div><dt>扫描</dt><dd>{{ job.total_count }}</dd></div>
            <div><dt>新增</dt><dd>{{ job.inserted_count }}</dd></div>
            <div><dt>重复</dt><dd>{{ job.duplicate_count }}</dd></div>
            <div><dt>失败</dt><dd>{{ job.failed_count }}</dd></div>
          </dl>
          <footer class="record-byline">{{ job.created_by }} · {{ job.created_at }}</footer>
        </article>
        <el-empty v-if="!jobs.length" description="尚无导入记录" :image-size="72" />
      </div>
    </section>
  </main>
</template>
