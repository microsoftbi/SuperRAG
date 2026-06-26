<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>SuperRAG 客服助手</h1>
      <h2>创建账号</h2>
      <form @submit.prevent="handleRegister">
        <div class="field">
          <input v-model="username" placeholder="用户名" required />
        </div>
        <div class="field">
          <input v-model="email" type="email" placeholder="邮箱" required />
        </div>
        <div class="field">
          <input v-model="password" type="password" placeholder="密码（至少6位）" required />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading" class="btn">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>
      <p class="switch">
        已有账号？<router-link to="/login">去登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '../api/index.js'

const router = useRouter()
const username = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await register({
      username: username.value,
      email: email.value,
      password: password.value,
    })
    router.push('/login?registered=1')
  } catch (err) {
    error.value = err.response?.data?.detail?.[0]?.msg
      || err.response?.data?.detail
      || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; background: var(--bg-page);
}
.auth-card {
  background: var(--bg-card); padding: 40px; border-radius: 12px;
  box-shadow: var(--shadow-sm); width: 360px;
}
h1 { font-size: 20px; text-align: center; color: var(--color-primary); margin-bottom: 4px; }
h2 { font-size: 16px; text-align: center; color: var(--text-secondary); margin-bottom: 24px; }
.field { margin-bottom: 12px; }
.field input {
  width: 100%; padding: 10px 12px; border: 1px solid var(--border-input);
  border-radius: 6px; font-size: 14px; box-sizing: border-box;
  background: var(--bg-card); color: var(--text-primary);
}
.btn {
  width: 100%; padding: 10px; background: var(--color-primary); color: var(--text-inverse);
  border: none; border-radius: 6px; font-size: 14px; cursor: pointer;
}
.btn:disabled { background: var(--text-muted); }
.error { color: var(--color-danger); font-size: 13px; margin-bottom: 8px; }
.switch { text-align: center; font-size: 13px; color: var(--text-tertiary); margin-top: 16px; }
.switch a { color: var(--color-primary); text-decoration: none; }
</style>