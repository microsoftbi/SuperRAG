<template>
  <div class="chat-page">
    <header class="chat-header">
      <h1>SPRAG 客服助手</h1>
      <div class="header-right">
        <router-link v-if="isAdmin" to="/admin" class="admin-link">管理后台</router-link>
        <span class="user-info">{{ username }}</span>
        <button @click="logout" class="logout-btn">退出</button>
      </div>
    </header>
    <ChatWindow />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import ChatWindow from '../components/chat/ChatWindow.vue'

const router = useRouter()

const user = computed(() => {
  try { return JSON.parse(localStorage.getItem('user')) } catch { return null }
})
const username = computed(() => user.value?.username || '')
const isAdmin = computed(() => user.value?.role === 'admin')

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0 auto;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}
.chat-header h1 {
  font-size: 18px;
  color: #333;
}
.header-right { display: flex; align-items: center; gap: 12px; }
.admin-link {
  color: #1976d2;
  text-decoration: none;
  font-size: 14px;
}
.user-info { font-size: 13px; color: #888; }
.logout-btn {
  padding: 4px 12px; border: 1px solid #d0d0d0; border-radius: 4px;
  background: #fff; cursor: pointer; font-size: 12px; color: #666;
}
.logout-btn:hover { background: #f5f5f5; }
</style>