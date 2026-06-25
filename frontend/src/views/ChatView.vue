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
    <nav class="mode-tabs">
      <button :class="['mode-tab', { active: chatMode === 'rag' }]" @click="chatMode = 'rag'">RAG</button>
      <button
        :class="['mode-tab', { active: chatMode === 'kg', disabled: !kgAvailable }]"
        :disabled="!kgAvailable"
        @click="chatMode = 'kg'"
      >知识图谱</button>
      <button :class="['mode-tab', { active: chatMode === 'nl2sql' }]" @click="chatMode = 'nl2sql'">问数</button>
    </nav>
    <div class="chat-body">
      <SessionSidebar
        :sessions="sessions"
        :currentSessionId="currentSessionId"
        :collapsed="sidebarCollapsed"
        @select="switchSession"
        @new="startNewSession"
        @delete="handleDeleteSession"
        @rename="handleRenameSession"
        @toggle="sidebarCollapsed = !sidebarCollapsed; localStorage.setItem('sidebar_collapsed', sidebarCollapsed)"
      />
      <ChatWindow v-if="chatMode === 'rag'" mode="rag" :session-key="currentSessionId" />
      <ChatWindow v-if="chatMode === 'kg'" mode="kg" :session-key="currentSessionId" />
      <Nl2SqlChat v-if="chatMode === 'nl2sql'" :session-key="currentSessionId" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import ChatWindow from '../components/chat/ChatWindow.vue'
import Nl2SqlChat from '../components/chat/Nl2SqlChat.vue'
import SessionSidebar from '../components/chat/SessionSidebar.vue'
import { getChatSessions, deleteChatSession } from '../api/index.js'

const router = useRouter()

const user = computed(() => {
  try { return JSON.parse(localStorage.getItem('user')) } catch { return null }
})
const username = computed(() => user.value?.username || '')
const isAdmin = computed(() => user.value?.role === 'admin')

const chatMode = ref(localStorage.getItem('chat_mode') || 'rag')
const sessions = ref([])
const currentSessionId = ref('')
const sidebarCollapsed = ref(localStorage.getItem('sidebar_collapsed') === 'true')
const kgAvailable = ref(true)  // 由后端返回，Neo4j 不可用时置 false

const sessionIdKeys = { rag: 'chat_session_id', kg: 'kg_session_id', nl2sql: 'nl2sql_session_id' }
const sessionIdPrefixes = { rag: 'session_', kg: 'kg_', nl2sql: 'nl2sql_' }

// 初始化 sessionId
function initSessionId() {
  const key = sessionIdKeys[chatMode.value] || 'chat_session_id'
  const stored = localStorage.getItem(key)
  const prefix = sessionIdPrefixes[chatMode.value] || 'session_'
  currentSessionId.value = stored || prefix + Date.now()
}

async function loadSessions() {
  localStorage.setItem('chat_mode', chatMode.value)
  const key = sessionIdKeys[chatMode.value] || 'chat_session_id'
  localStorage.setItem(key, currentSessionId.value)
  try {
    const res = await getChatSessions(chatMode.value)
    if (res.data?.sessions) {
      sessions.value = res.data.sessions
    }
  } catch { /* ignore */ }
}

onMounted(async () => {
  initSessionId()
  await loadSessions()
})

watch(chatMode, async () => {
  initSessionId()
  await loadSessions()
})

function switchSession(sessionId) {
  currentSessionId.value = sessionId
  const key = sessionIdKeys[chatMode.value] || 'chat_session_id'
  localStorage.setItem(key, sessionId)
}

async function handleDeleteSession(sessionId) {
  if (!confirm(`确定删除此会话以及所有相关日志？`)) return
  try {
    await deleteChatSession(sessionId, chatMode.value)
    if (currentSessionId.value === sessionId) {
      startNewSession()
    }
    await loadSessions()
  } catch (e) {
    alert('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

function handleRenameSession(sessionId, title) {
  const s = sessions.value.find(x => x.session_id === sessionId)
  if (s) s.title = title
}

function startNewSession() {
  const prefix = sessionIdPrefixes[chatMode.value] || 'session_'
  currentSessionId.value = prefix + Date.now()
  const key = sessionIdKeys[chatMode.value] || 'chat_session_id'
  localStorage.setItem(key, currentSessionId.value)
}

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
  max-width: 1100px;
  margin: 0 auto;
}
.chat-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}
.chat-header h1 { font-size: 18px; color: #333; }
.header-right { display: flex; align-items: center; gap: 12px; }
.admin-link { color: #1976d2; text-decoration: none; font-size: 14px; }
.user-info { font-size: 13px; color: #888; }
.logout-btn {
  padding: 4px 12px; border: 1px solid #d0d0d0; border-radius: 4px;
  background: #fff; cursor: pointer; font-size: 12px; color: #666;
}
.logout-btn:hover { background: #f5f5f5; }
.mode-tabs {
  display: flex; gap: 2px;
  border-bottom: 2px solid #e0e0e0;
  padding: 0 20px;
}
.mode-tab {
  padding: 8px 20px; border: none; background: none; cursor: pointer;
  font-size: 14px; color: #666;
  border-bottom: 2px solid transparent; margin-bottom: -2px;
}
.mode-tab.active { color: #1976d2; border-bottom-color: #1976d2; font-weight: 600; }
.mode-tab:hover:not(.active):not(.disabled) { color: #333; }
.mode-tab.disabled { color: #ccc; cursor: not-allowed; }
</style>