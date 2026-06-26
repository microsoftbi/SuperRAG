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
  border-right: 1px solid var(--border-default);
  background: var(--bg-surface);
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
  border-bottom: 1px solid var(--border-default);
  min-height: 20px;
}
.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-right: auto;
  margin-left: 8px;
}
.toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-tertiary);
  padding: 4px 4px;
  border-radius: 4px;
  line-height: 1;
}
.toggle-btn:hover { background: var(--bg-hover); color: var(--text-secondary); }
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
.session-item {
  display: flex; align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--bg-hover);
  transition: background 0.15s;
}
.session-item:hover { background: var(--bg-hover); }
.session-item.active { background: var(--bg-active); }
.session-main { flex: 1; min-width: 0; }
.session-actions {
  display: none; gap: 2px; flex-shrink: 0; margin-left: 4px;
}
.session-item:hover .session-actions { display: flex; }
.sess-btn {
  background: none; border: none; cursor: pointer;
  font-size: 11px; padding: 2px 4px; border-radius: 3px; line-height: 1;
}
.sess-btn:hover { background: var(--border-default); }
.del-btn:hover { background: var(--color-danger-light); }
.rename-bar {
  display: flex; align-items: center; gap: 4px;
  padding: 8px 12px; border-top: 1px solid var(--border-default);
}
.rename-bar input {
  flex: 1; padding: 4px 8px; font-size: 13px;
  border: 1px solid var(--color-primary); border-radius: 4px; outline: none;
}
.rename-ok, .rename-cancel {
  background: none; border: 1px solid; border-radius: 4px;
  cursor: pointer; font-size: 12px; padding: 3px 8px;
}
.rename-ok { color: var(--color-success); border-color: var(--color-success); }
.rename-ok:hover { background: var(--color-success-light); }
.rename-cancel { color: var(--color-danger); border-color: var(--color-danger); }
.rename-cancel:hover { background: var(--color-danger-light); }
.session-query {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-time {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
}
.session-empty {
  padding: 24px 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
.new-chat-btn {
  margin: 12px 16px;
  padding: 8px 0;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}
.new-chat-btn:hover { background: var(--bg-hover); border-color: var(--text-muted); }
</style>