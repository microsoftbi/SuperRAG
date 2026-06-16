<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>SPRAG 客服助手</h1>
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
  min-height: 100vh; background: #f5f5f5;
}
.auth-card {
  background: #fff; padding: 40px; border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08); width: 360px;
}
h1 { font-size: 20px; text-align: center; color: #1976d2; margin-bottom: 4px; }
h2 { font-size: 16px; text-align: center; color: #666; margin-bottom: 24px; }
.field { margin-bottom: 12px; }
.field input {
  width: 100%; padding: 10px 12px; border: 1px solid #d0d0d0;
  border-radius: 6px; font-size: 14px; box-sizing: border-box;
}
.btn {
  width: 100%; padding: 10px; background: #1976d2; color: #fff;
  border: none; border-radius: 6px; font-size: 14px; cursor: pointer;
}
.btn:disabled { background: #ccc; }
.error { color: #c62828; font-size: 13px; margin-bottom: 8px; }
.switch { text-align: center; font-size: 13px; color: #888; margin-top: 16px; }
.switch a { color: #1976d2; text-decoration: none; }
</style>