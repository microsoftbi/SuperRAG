<template>
  <div class="retrieval-debug">
    <button class="debug-toggle" @click="expanded = !expanded">
      {{ expanded ? '▼' : '▶' }} 检索详情
    </button>
    <div v-if="expanded" class="debug-body">
      <div class="debug-tabs">
        <button
          v-for="t in tabs"
          :key="t.key"
          :class="['debug-tab', { active: activeTab === t.key }]"
          @click="activeTab = t.key"
        >
          {{ t.label }} ({{ (detail[t.key] || []).length }})
        </button>
      </div>
      <div class="debug-table-wrap">
        <table class="debug-table" v-if="items.length">
          <thead>
            <tr>
              <th class="row-num">#</th>
              <th>内容</th>
              <th class="col-score">得分</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in items" :key="i">
              <td class="row-num">{{ i + 1 }}</td>
              <td class="col-content" :title="item.content">{{ item.content }}</td>
              <td class="col-score">{{ item.score }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="debug-empty">暂无数据</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  detail: { type: Object, default: () => ({}) },
})

const expanded = ref(false)
const activeTab = ref('dense')

const tabs = [
  { key: 'dense', label: '稠密检索' },
  { key: 'sparse', label: 'BM25 检索' },
  { key: 'fused', label: '融合结果' },
]

const items = computed(() => {
  return props.detail[activeTab.value] || []
})
</script>

<style scoped>
.retrieval-debug {
  margin-top: 8px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  overflow: hidden;
}
.debug-toggle {
  width: 100%;
  background: var(--bg-surface);
  border: none;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--text-tertiary);
  cursor: pointer;
  text-align: left;
}
.debug-toggle:hover { background: var(--bg-hover); color: var(--text-secondary); }
.debug-body {
  border-top: 1px solid var(--border-default);
}
.debug-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-default);
}
.debug-tab {
  flex: 1;
  background: none;
  border: none;
  padding: 6px 8px;
  font-size: 11px;
  cursor: pointer;
  color: var(--text-tertiary);
  border-bottom: 2px solid transparent;
}
.debug-tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}
.debug-table-wrap {
  max-height: 300px;
  overflow: auto;
}
.debug-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}
.debug-table th {
  background: var(--bg-page);
  padding: 6px 8px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
  position: sticky;
  top: 0;
}
.debug-table td {
  padding: 5px 8px;
  border-bottom: 1px solid var(--bg-page);
  color: var(--text-secondary);
}
.debug-table .row-num {
  width: 28px;
  text-align: center;
  color: var(--text-muted);
  font-size: 10px;
}
.col-content {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.col-score {
  width: 50px;
  text-align: right;
  font-family: 'SF Mono', 'Consolas', monospace;
}
.debug-table tbody tr:hover td { background: #f0f7ff; }
.debug-empty {
  padding: 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}
</style>
