<template>
  <div :class="['session-sidebar', { collapsed }]">
    <div class="sidebar-header">
      <span v-if="!collapsed" class="sidebar-title">历史会话</span>
      <button class="toggle-btn" @click="$emit('toggle')">
        {{ collapsed ? '▶' : '◀' }}
      </button>
    </div>
    <div v-if="!collapsed" class="session-list">
      <div
        v-for="s in sessions"
        :key="s.session_id"
        :class="['session-item', { active: s.session_id === currentSessionId }]"
      >
        <div class="session-main" @click="$emit('select', s.session_id)">
          <div class="session-query">{{ s.title || s.first_query || '新对话' }}</div>
          <div class="session-time">{{ formatTime(s.last_active) }}</div>
        </div>
        <div class="session-actions">
          <button
            class="sess-btn rename-btn"
            title="重命名"
            @click.stop="startRename(s)"
          >✏️</button>
          <button
            class="sess-btn del-btn"
            title="删除"
            @click.stop="$emit('delete', s.session_id)"
          >🗑️</button>
        </div>
      </div>
      <div v-if="sessions.length === 0" class="session-empty">暂无历史会话</div>
    </div>

    <div v-if="!collapsed && renamingSession" class="rename-bar">
      <input
        v-model="renameText"
        ref="renameInputRef"
        @keydown.enter="confirmRename"
        @keydown.esc="cancelRename"
        placeholder="输入新名称..."
      />
      <button class="rename-ok" @click="confirmRename">✓</button>
      <button class="rename-cancel" @click="cancelRename">✕</button>
    </div>

    <button v-if="!collapsed" class="new-chat-btn" @click="$emit('new')">＋ 新对话</button>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { renameChatSession } from '../../api/index.js'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  currentSessionId: { type: String, default: '' },
  collapsed: { type: Boolean, default: false },
})
const emit = defineEmits(['select', 'new', 'toggle', 'delete', 'rename'])

const renamingSession = ref(null)
const renameText = ref('')
const renameInputRef = ref(null)

function startRename(s) {
  renamingSession.value = s.session_id
  renameText.value = s.title || s.first_query || ''
  nextTick(() => renameInputRef.value?.focus())
}

function cancelRename() {
  renamingSession.value = null
  renameText.value = ''
}

async function confirmRename() {
  const title = renameText.value.trim()
  if (!title) return
  try {
    await renameChatSession(renamingSession.value, title)
    emit('rename', renamingSession.value, title)
  } catch (e) {
    alert('重命名失败')
  }
  cancelRename()
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const now = Date.now()
  const diff = now - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  return month + '-' + day
}
</script>

<style scoped>
.session-sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e0e0e0;
  background: #fafafa;
  transition: width 0.2s ease;
  overflow: hidden;
  flex-shrink: 0;
}
.session-sidebar.collapsed {
  width: 36px;
}
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 16px 8px 12px;
  border-bottom: 1px solid #e0e0e0;
  min-height: 20px;
}
.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: #555;
  margin-right: auto;
  margin-left: 8px;
}
.toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  color: #888;
  padding: 4px 4px;
  border-radius: 4px;
  line-height: 1;
}
.toggle-btn:hover { background: #e8e8e8; color: #555; }
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
.session-item {
  display: flex; align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.15s;
}
.session-item:hover { background: #f0f0f0; }
.session-item.active { background: #e3f2fd; }
.session-main { flex: 1; min-width: 0; }
.session-actions {
  display: none; gap: 2px; flex-shrink: 0; margin-left: 4px;
}
.session-item:hover .session-actions { display: flex; }
.session-item.active { background: #e3f2fd; }
.sess-btn {
  background: none; border: none; cursor: pointer;
  font-size: 11px; padding: 2px 4px; border-radius: 3px; line-height: 1;
}
.sess-btn:hover { background: #e0e0e0; }
.del-btn:hover { background: #ffcdd2; }
.rename-bar {
  display: flex; align-items: center; gap: 4px;
  padding: 8px 12px; border-top: 1px solid #e0e0e0;
}
.rename-bar input {
  flex: 1; padding: 4px 8px; font-size: 13px;
  border: 1px solid #1976d2; border-radius: 4px; outline: none;
}
.rename-ok, .rename-cancel {
  background: none; border: 1px solid; border-radius: 4px;
  cursor: pointer; font-size: 12px; padding: 3px 8px;
}
.rename-ok { color: #2e7d32; border-color: #2e7d32; }
.rename-ok:hover { background: #e8f5e9; }
.rename-cancel { color: #c62828; border-color: #c62828; }
.rename-cancel:hover { background: #ffebee; }
.session-query {
  font-size: 13px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-time {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}
.session-empty {
  padding: 24px 16px;
  text-align: center;
  color: #bbb;
  font-size: 13px;
}
.new-chat-btn {
  margin: 12px 16px;
  padding: 8px 0;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  background: #fff;
  color: #555;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}
.new-chat-btn:hover { background: #f0f0f0; border-color: #bbb; }
</style>