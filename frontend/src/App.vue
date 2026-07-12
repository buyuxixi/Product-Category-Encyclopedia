<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataBoard, Document, Fold, Search, Setting } from '@element-plus/icons-vue'
import { ApiError, apiRequest, type Identity } from './api'
import CategorySidebar from './components/CategorySidebar.vue'
import DashboardView from './views/DashboardView.vue'
import EncyclopediaView from './views/EncyclopediaView.vue'
import LoginView from './views/LoginView.vue'
import type { CategorySummary, Role, SearchResult } from './types'

type ViewName = 'dashboard' | 'encyclopedia'
type AuthConfig = {
  mode: string
  local_enabled: boolean
  feishu_enabled: boolean
}
type CurrentUser = { id: number; name: string; role: Role; provider: string }

const activeView = ref<ViewName>('dashboard')
const categories = ref<CategorySummary[]>([])
const selectedCode = ref('FAR_INFRARED')
const query = ref('')
const searchResults = ref<SearchResult[]>([])
const targetSection = ref<string | null>(null)
const dashboard = ref({ category_count: 0, source_count: 0 })
const authLoading = ref(true)
const authenticated = ref(false)
const authConfig = ref<AuthConfig>({ mode: 'local', local_enabled: false, feishu_enabled: false })
const user = ref<CurrentUser | null>(null)
const sidebarCollapsed = ref(false)

const identity = computed<Identity>(() => ({
  id: user.value?.id,
  actor: user.value?.name || '',
  role: user.value?.role || 'researcher',
  provider: user.value?.provider,
}))

const roleLabel = computed(() => {
  const labels: Record<Role, string> = { admin: '管理员', data: '数据人员', researcher: '研究人员', reviewer: '审核人员' }
  return user.value ? labels[user.value.role] : ''
})

const filteredCategories = computed(() => {
  if (!query.value.trim()) return categories.value
  const keyword = query.value.trim().toLowerCase()
  const matchedCodes = new Set(
    categories.value
      .filter((item) =>
        [item.name, item.code, item.description, ...item.aliases].some((value) =>
          value?.toLowerCase().includes(keyword),
        ),
      )
      .map((item) => item.code),
  )
  return categories.value.filter(
    (item) => matchedCodes.has(item.code) || item.children.some((child) => matchedCodes.has(child.code)),
  )
})

async function loadSession() {
  authLoading.value = true
  try {
    authConfig.value = await apiRequest<AuthConfig>('/auth/config')
    user.value = await apiRequest<CurrentUser>('/auth/me')
    authenticated.value = true
    await refresh()
  } catch (error) {
    authenticated.value = false
    user.value = null
    if (error instanceof ApiError && error.status !== 401) {
      ElMessage.error(error.message)
    }
  } finally {
    authLoading.value = false
  }
}

async function refresh() {
  if (!authenticated.value) return
  try {
    const [categoryResult, dashboardResult] = await Promise.all([
      apiRequest<{ items: CategorySummary[] }>('/categories'),
      apiRequest<typeof dashboard.value>('/dashboard'),
    ])
    categories.value = categoryResult.items
    dashboard.value = dashboardResult
    if (!categories.value.some((item) => item.code === selectedCode.value)) {
      selectedCode.value = categories.value.find((item) => item.parent_code)?.code || categories.value[0]?.code || ''
    }
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      authenticated.value = false
      user.value = null
    } else {
      ElMessage.error((error as Error).message)
    }
  }
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(query, (value) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!value.trim()) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    try {
      const result = await apiRequest<{ items: SearchResult[] }>(`/search?q=${encodeURIComponent(value.trim())}`)
      searchResults.value = result.items
    } catch {
      searchResults.value = []
    }
  }, 220)
})

function selectCategory(code: string) {
  selectedCode.value = code
  targetSection.value = null
  activeView.value = 'encyclopedia'
}

function openSearchResult(result: SearchResult) {
  selectedCode.value = result.category_code
  targetSection.value = result.section_key
  activeView.value = 'encyclopedia'
  query.value = ''
  searchResults.value = []
}

async function logout() {
  try {
    await ElMessageBox.confirm('退出后需要重新登录才能查看和编辑业务数据。', '退出登录', {
      confirmButtonText: '退出登录',
      cancelButtonText: '取消',
    })
    await apiRequest('/auth/logout', { method: 'POST' })
    authenticated.value = false
    user.value = null
    categories.value = []
  } catch (error) {
    if (error !== 'cancel') ElMessage.error((error as Error).message)
  }
}

onMounted(loadSession)
</script>

<template>
  <div v-loading="authLoading" class="app-root">
    <LoginView
      v-if="!authLoading && !authenticated"
      :local-enabled="authConfig.local_enabled"
      :feishu-enabled="authConfig.feishu_enabled"
      @logged-in="loadSession"
    />

    <div v-else-if="authenticated" class="app-shell">
      <header class="topbar">
        <button class="brand" @click="activeView = 'dashboard'">
          <span class="brand-mark">P</span>
          <span><strong>产品品类百科</strong><small>Category Intelligence</small></span>
        </button>
        <div class="global-search">
          <el-icon><Search /></el-icon>
          <input v-model="query" placeholder="搜索品类、别名或业务术语…" aria-label="搜索品类、别名或业务术语" />
          <span class="search-kbd">⌘K</span>
          <div v-if="query.trim() && searchResults.length" class="search-popover">
            <button v-for="result in searchResults" :key="`${result.kind}-${result.category_code}-${result.section_key}-${result.title}`" class="search-result" @click="openSearchResult(result)">
              <strong>{{ result.title }}</strong>
              <span>{{ result.snippet }}</span>
            </button>
          </div>
        </div>
        <div class="identity-controls">
          <div class="current-user"><strong>{{ user?.name }}</strong><span>{{ roleLabel }}</span></div>
          <el-button text size="small" @click="logout">退出</el-button>
        </div>
      </header>

      <nav class="primary-nav">
        <button :class="{ active: activeView === 'dashboard' }" @click="activeView = 'dashboard'">
          <el-icon><DataBoard /></el-icon>总览
        </button>
        <button :class="{ active: activeView === 'encyclopedia' }" @click="activeView = 'encyclopedia'">
          <el-icon><Document /></el-icon>品类百科
        </button>
        <span class="nav-spacer"></span>
        <span class="system-stat">{{ dashboard.category_count }} 个品类 · {{ dashboard.source_count }} 条来源</span>
        <button class="settings-button" title="系统设置（后续开放）"><el-icon><Setting /></el-icon></button>
      </nav>

      <div class="body-layout">
        <!-- Dashboard: no sidebar -->
        <DashboardView
          v-if="activeView === 'dashboard'"
          :identity="identity"
          @select="selectCategory"
        />
        <!-- Encyclopedia: with sidebar -->
        <template v-else>
          <div class="sidebar-wrapper" :class="{ collapsed: sidebarCollapsed }">
            <CategorySidebar
              :categories="filteredCategories"
              :selected-code="selectedCode"
              :query="query"
              @select="selectCategory"
            />
            <button class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
              <el-icon><Fold /></el-icon>
            </button>
          </div>
          <button
            v-if="sidebarCollapsed"
            class="sidebar-expand-btn"
            @click="sidebarCollapsed = false"
          >
            <el-icon><Document /></el-icon>
            <span>目录</span>
          </button>
          <EncyclopediaView
            v-if="activeView === 'encyclopedia'"
            :category-code="selectedCode"
            :focus-section="targetSection"
            :identity="identity"
            @changed="refresh"
            @navigate="selectCategory"
          />
        </template>
      </div>
    </div>
  </div>
</template>
