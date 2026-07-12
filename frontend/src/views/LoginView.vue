<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, Right } from '@element-plus/icons-vue'
import { apiRequest } from '../api'

const props = defineProps<{
  localEnabled: boolean
  feishuEnabled: boolean
  authError?: string
}>()
const emit = defineEmits<{ loggedIn: [] }>()

const username = ref('')
const password = ref('')
const loading = ref(false)

async function login() {
  if (!username.value.trim() || !password.value) return
  loading.value = true
  try {
    await apiRequest('/auth/local/login', {
      method: 'POST',
      body: JSON.stringify({ username: username.value.trim(), password: password.value }),
    })
    emit('loggedIn')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-shell">
    <!-- 左侧品牌区 -->
    <aside class="login-hero">
      <div class="login-hero-content">
        <div class="login-hero-logo"><span class="brand-mark">P</span><span>产品品类百科</span></div>
        <h2 class="login-hero-title">跨境电商<br/>品类情报中心</h2>
        <p class="login-hero-desc">聚合 Amazon、YouTube、Reddit、Google Trends 数据，为选品决策提供实时洞察。</p>
        <div class="login-hero-stats">
          <div class="hero-stat"><strong>5</strong><span>品类</span></div>
          <div class="hero-stat"><strong>659+</strong><span>热点链接</span></div>
          <div class="hero-stat"><strong>84</strong><span>数据来源</span></div>
        </div>
      </div>
      <div class="login-hero-deco"></div>
    </aside>
    <!-- 右侧表单区 -->
    <section class="login-form-side">
      <div class="login-card">
        <div class="login-copy">
          <div class="eyebrow">内部工作台</div>
          <h1>登录后开始研究</h1>
          <p>统一查看品类、竞品数据、研究来源和审核版本。</p>
        </div>

        <el-alert v-if="props.authError" type="warning" :closable="false" show-icon class="login-alert">
          {{ props.authError }}
        </el-alert>

        <form v-if="props.localEnabled" class="login-form" @submit.prevent="login">
          <div class="form-field">
            <label>账号</label>
            <el-input v-model="username" autocomplete="username" placeholder="输入工作账号" />
          </div>
          <div class="form-field">
            <label>密码</label>
            <el-input v-model="password" type="password" show-password autocomplete="current-password" placeholder="输入密码" />
          </div>
          <el-button type="primary" native-type="submit" :loading="loading" :disabled="!username.trim() || !password" :icon="Lock" class="login-submit">
            登录工作台
          </el-button>
        </form>

        <el-button v-if="props.feishuEnabled" class="feishu-login" :icon="Right" tag="a" href="/api/v1/auth/feishu/start">
          使用飞书账号登录
        </el-button>

        <el-empty v-if="!props.localEnabled && !props.feishuEnabled" description="管理员尚未配置登录方式" :image-size="90" />
        <p class="login-footnote">你的编辑、审核和发布操作都会记录在版本历史中。</p>
      </div>
    </section>
  </main>
</template>
