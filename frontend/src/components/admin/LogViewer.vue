<template>
  <div class="log-viewer">
    <div class="log-header">
      <h2>问答日志</h2>
      <div class="log-actions">
        <input v-model="searchSession" placeholder="会话ID筛选" @input="loadLogs" />
        <button class="clear-btn" @click="handleClear">清空日志</button>
      </div>
    </div>
    <div v-if="logs.length === 0" class="empty">暂无日志记录</div>
    <div v-for="log in logs" :key="log.id" class="log-card" @click="toggleExpand(log.id)">
      <div class="log-meta">
        <span class="session-id">{{ log.session_id.slice(0, 20) }}...</span>
        <span class="time">{{ new Date(log.created_at).toLocaleString() }}</span>
        <span class="latency">{{ log.latency_ms }}ms</span>
        <span class="badge" :class="log.rewritten_query && log.rewritten_query !== log.query ? 'rewritten' : ''">
          {{ log.rewritten_query && log.rewritten_query !== log.query ? '已重写' : '原始' }}
        </span>
      </div>
      <div class="log-query">{{ log.query }}</div>
      <div v-if="expanded[log.id]" class="log-detail">
        <div v-if="log.rewritten_query && log.rewritten_query !== log.query" class="detail-row">
          <span class="label">改写后：</span>
          <span>{{ log.rewritten_query }}</span>
        </div>
        <div class="detail-row">
          <span class="label">回答：</span>
          <span>{{ log.answer.slice(0, 500) }}{{ log.answer.length > 500 ? '...' : '' }}</span>
        </div>
        <div class="detail-row">
          <span class="label">来源数：</span>
          <span>{{ JSON.parse(log.sources || '[]').length }}</span>
        </div>
        <div class="detail-row">
          <span class="label">Token数：</span>
          <span>{{ log.token_count }}</span>
        </div>
        <div v-if="log.nl2sql_sql" class="detail-row nl2sql-block">
          <span class="label">生成的SQL：</span>
          <div class="code-block">
            <code>{{ log.nl2sql_sql }}</code>
            <button class="copy-btn" @click.stop="copyText(log.nl2sql_sql)">复制</button>
          </div>
        </div>
        <div v-if="log.nl2sql_prompt" class="detail-row nl2sql-block">
          <span class="label">SQL提示词：</span>
          <div class="code-block">
            <code>{{ log.nl2sql_prompt }}</code>
            <button class="copy-btn" @click.stop="copyText(log.nl2sql_prompt)">复制</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="hasMore" class="load-more">
      <button @click="loadMore">加载更多</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listLogs, clearLogs } from '../../api/index.js'

const logs = ref([])
const expanded = ref({})
const searchSession = ref('')
const page = ref(0)
const hasMore = ref(true)
const limit = 20

function toggleExpand(id) {
  expanded.value[id] = !expanded.value[id]
}

async function loadLogs() {
  page.value = 0
  const res = await listLogs({
    session_id: searchSession.value || undefined,
    skip: 0,
    limit,
  })
  logs.value = res.data.items
  hasMore.value = res.data.total > limit
}

async function loadMore() {
  page.value++
  const res = await listLogs({
    session_id: searchSession.value || undefined,
    skip: page.value * limit,
    limit,
  })
  logs.value.push(...res.data.items)
  hasMore.value = res.data.total > (page.value + 1) * limit
}

onMounted(loadLogs)

function copyText(text) {
  navigator.clipboard.writeText(text).catch(() => {})
}

async function handleClear() {
  if (!confirm('确定清空所有问答日志？此操作不可撤销。')) return
  try {
    await clearLogs()
    logs.value = []
    hasMore.value = false
  } catch { /* ignore */ }
}
</script>

<style scoped>
.log-viewer { }
.log-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.log-header h2 { font-size: 16px; }
.log-actions { display: flex; gap: 8px; align-items: center; }
.log-actions input { padding: 6px 10px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 13px; width: 200px; }
.clear-btn {
  padding: 6px 12px; font-size: 12px; color: #c62828; background: #fff;
  border: 1px solid #e57373; border-radius: 4px; cursor: pointer;
}
.clear-btn:hover { background: #ffebee; }
.empty { text-align: center; color: #999; padding: 40px; }
.log-card {
  padding: 12px; border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 8px; cursor: pointer;
  transition: background 0.15s;
}
.log-card:hover { background: #fafafa; }
.log-meta { display: flex; gap: 12px; align-items: center; font-size: 12px; color: #666; margin-bottom: 4px; }
.session-id { font-family: monospace; }
.latency { color: #888; }
.badge { padding: 1px 6px; border-radius: 3px; font-size: 11px; background: #e0e0e0; color: #555; }
.badge.rewritten { background: #e3f2fd; color: #1976d2; }
.log-query { font-size: 14px; font-weight: 500; color: #333; }
.log-detail { margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee; }
.detail-row { font-size: 13px; margin-bottom: 4px; line-height: 1.5; }
.label { color: #888; margin-right: 4px; }
.load-more { text-align: center; margin-top: 12px; }
.load-more button { padding: 6px 20px; border: 1px solid #d0d0d0; border-radius: 4px; background: #fff; cursor: pointer; font-size: 13px; }
.nl2sql-block { margin-top: 8px; }
.code-block {
  position: relative; margin-top: 4px; max-height: 300px; overflow: auto;
  background: #f6f8fa; border: 1px solid #dde0e4; border-radius: 6px; padding: 10px;
}
.code-block code {
  font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-all; color: #333;
}
.copy-btn {
  position: absolute; top: 6px; right: 6px;
  font-size: 11px; color: #1976d2; background: #fff;
  border: 1px solid #1976d2; border-radius: 4px; padding: 2px 8px; cursor: pointer;
}
.copy-btn:hover { background: #e3f2fd; }
</style>
