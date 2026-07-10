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
    <section class="login-card">
      <div class="login-brand"><span class="brand-mark">P</span><div><strong>产品品类百科</strong><small>Category Intelligence</small></div></div>
      <div class="login-copy">
        <div class="eyebrow">内部工作台</div>
        <h1>登录后开始研究</h1>
        <p>统一查看品类、竞品数据、研究来源和审核版本。</p>
      </div>

      <el-alert v-if="props.authError" type="warning" :closable="false" show-icon class="login-alert">
        {{ props.authError }}
      </el-alert>

      <form v-if="props.localEnabled" class="login-form" @submit.prevent="login">
        <el-form-item label="账号">
          <el-input v-model="username" autocomplete="username" placeholder="输入工作账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password autocomplete="current-password" placeholder="输入密码" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" :disabled="!username.trim() || !password" :icon="Lock" class="login-submit">
          登录工作台
        </el-button>
      </form>

      <el-button v-if="props.feishuEnabled" class="feishu-login" :icon="Right" tag="a" href="/api/v1/auth/feishu/start">
        使用飞书账号登录
      </el-button>

      <el-empty v-if="!props.localEnabled && !props.feishuEnabled" description="管理员尚未配置登录方式" :image-size="90" />
      <p class="login-footnote">你的编辑、审核和发布操作都会记录在版本历史中。</p>
    </section>
  </main>
</template>
