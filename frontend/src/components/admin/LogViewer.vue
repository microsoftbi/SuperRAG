<template>
  <div class="log-viewer">
    <div class="log-header">
      <h2>问答日志</h2>
      <div class="filters">
        <input v-model="searchSession" placeholder="会话ID筛选" @input="loadLogs" />
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
      </div>
    </div>
    <div v-if="hasMore" class="load-more">
      <button @click="loadMore">加载更多</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listLogs } from '../../api/index.js'

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
</script>

<style scoped>
.log-viewer { }
.log-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.log-header h2 { font-size: 16px; }
.filters input { padding: 6px 10px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 13px; width: 200px; }
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
</style>
