<template>
  <div class="chat-page">
    <header class="chat-header">
      <h1>SPRAG 客服助手</h1>
      <router-link to="/admin" class="admin-link">管理后台</router-link>
    </header>
    <ChatWindow />
  </div>
</template>

<script setup>
import ChatWindow from '../components/chat/ChatWindow.vue'
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
.admin-link {
  color: #1976d2;
  text-decoration: none;
  font-size: 14px;
}
</style>
