<template>
  <div class="chat-page">
    <header class="chat-header">
      <h1>SuperRAG 客服助手 <span class="version">v{{ appVersion }}</span></h1>
      <div class="header-right">
        <router-link v-if="isAdmin" to="/admin" class="admin-link">管理后台</router-link>
        <button class="theme-toggle" @click="toggleTheme" :title="isDark ? '切换到浅色模式' : '切换到深色模式'">{{ isDark ? '🌙' : '☀️' }}</button>
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
import { getChatSessions, deleteChatSession, getRuntimeConfig } from '../api/index.js'
import { useTheme } from '../composables/useTheme.js'

const router = useRouter()
const { isDark, toggle: toggleTheme } = useTheme()
const appVersion = ref('')

async function loadVersion() {
  try {
    const res = await getRuntimeConfig()
    appVersion.value = res.data?.app_version || ''
  } catch { /* ignore */ }
}

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
  loadVersion()
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
  background: var(--bg-card);
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
  border-bottom: 1px solid var(--border-default);
}
.chat-header h1 { font-size: 18px; color: var(--text-primary); }
.chat-header .version { font-size: 11px; color: var(--text-tertiary); font-weight: 400; margin-left: 4px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.theme-toggle {
  background: none; border: none; cursor: pointer;
  font-size: 18px; padding: 4px; line-height: 1;
  border-radius: 4px; transition: background 0.2s;
}
.theme-toggle:hover { background: var(--bg-hover); }
.admin-link { color: var(--color-primary); text-decoration: none; font-size: 14px; }
.user-info { font-size: 13px; color: var(--text-tertiary); }
.logout-btn {
  padding: 4px 12px; border: 1px solid var(--border-input); border-radius: 4px;
  background: var(--bg-card); cursor: pointer; font-size: 12px; color: var(--text-secondary);
}
.logout-btn:hover { background: var(--bg-hover); }
.mode-tabs {
  display: flex; gap: 2px;
  border-bottom: 2px solid var(--border-default);
  padding: 0 20px;
  background: var(--bg-card);
}
.mode-tab {
  padding: 8px 20px; border: none; background: none; cursor: pointer;
  font-size: 14px; color: var(--text-secondary);
  border-bottom: 2px solid transparent; margin-bottom: -2px;
}
.mode-tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); font-weight: 600; }
.mode-tab:hover:not(.active):not(.disabled) { color: var(--text-primary); }
.mode-tab.disabled { color: var(--text-muted); cursor: not-allowed; }
</style>