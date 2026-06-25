<template>
  <div class="kg-edge-table">
    <div class="toolbar">
      <input
        v-model="searchSource"
        placeholder="源实体..."
        class="search-input"
      />
      <input
        v-model="searchTarget"
        placeholder="目标实体..."
        class="search-input"
      />
      <select v-model="filterType" class="type-filter">
        <option value="">全部关系类型</option>
        <option v-for="t in allRelTypes" :key="t" :value="t">{{ t }}</option>
      </select>
      <span class="count-hint">共 {{ filteredEdges.length }} / {{ graphData.edges.length }} 条关系</span>
      <div class="spacer" />
      <button v-if="selectedEdges.size" class="btn-batch-delete" @click="$emit('batch-delete', [...selectedEdges])">
        🗑️ 删除选中 ({{ selectedEdges.size }})
      </button>
      <button @click="$emit('new')" class="btn-create">+ 新建关系</button>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th class="col-cb">
              <input type="checkbox" :checked="allSelected" @change="toggleAll" />
            </th>
            <th class="col-idx">#</th>
            <th>源实体</th>
            <th class="col-type">关系类型</th>
            <th>目标实体</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(e, i) in pagedEdges" :key="i" :class="{ selected: selectedEdges.has(i) }">
            <td class="col-cb">
              <input type="checkbox" :checked="selectedEdges.has(i)" @change="toggleOne(i)" />
            </td>
            <td class="col-idx">{{ (page - 1) * pageSize + i + 1 }}</td>
            <td class="col-name" :title="e.sourceName">{{ e.sourceName }}</td>
            <td class="col-type">
              <span class="rel-tag">{{ e.type }}</span>
            </td>
            <td class="col-name" :title="e.targetName">{{ e.targetName }}</td>
            <td class="col-actions">
              <button class="icon-btn edit" @click="$emit('edit', e)" title="改类型">✏️</button>
              <button class="icon-btn delete" @click="$emit('delete', e)" title="删除">🗑️</button>
            </td>
          </tr>
          <tr v-if="!filteredEdges.length">
            <td colspan="6" class="empty">没有符合条件的关系</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="totalPages > 1" class="pager">
      <button :disabled="page <= 1" @click="page--">‹</button>
      <span>第 {{ page }} / {{ totalPages }} 页</span>
      <button :disabled="page >= totalPages" @click="page++">›</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  graphData: { type: Object, required: true },
})
const emit = defineEmits(['new', 'edit', 'delete', 'batch-delete'])

const searchSource = ref('')
const searchTarget = ref('')
const filterType = ref('')
const page = ref(1)
const pageSize = 30
const selectedEdges = ref(new Set())

// 把 edge 拼出 sourceName / targetName 方便筛选展示
const allSelected = computed(() =>
  pagedEdges.value.length > 0 && pagedEdges.value.every((_, i) => selectedEdges.value.has(i))
)

function toggleAll() {
  if (allSelected.value) {
    pagedEdges.value.forEach((_, i) => selectedEdges.value.delete(i))
  } else {
    pagedEdges.value.forEach((_, i) => selectedEdges.value.add(i))
  }
  selectedEdges.value = new Set(selectedEdges.value)
}

function toggleOne(idx) {
  if (selectedEdges.value.has(idx)) selectedEdges.value.delete(idx)
  else selectedEdges.value.add(idx)
  selectedEdges.value = new Set(selectedEdges.value)
}

const enrichedEdges = computed(() => {
  const nodeMap = {}
  props.graphData.nodes.forEach(n => { nodeMap[n.id] = n.name })
  return props.graphData.edges.map(e => ({
    ...e,
    sourceName: nodeMap[e.source] || e.source,
    targetName: nodeMap[e.target] || e.target,
  }))
})

const allRelTypes = computed(() => {
  const s = new Set()
  enrichedEdges.value.forEach(e => e.type && s.add(e.type))
  return [...s].sort()
})

const filteredEdges = computed(() => {
  const s = searchSource.value.trim().toLowerCase()
  const t = searchTarget.value.trim().toLowerCase()
  return enrichedEdges.value.filter(e => {
    if (filterType.value && e.type !== filterType.value) return false
    if (s && !e.sourceName.toLowerCase().includes(s)) return false
    if (t && !e.targetName.toLowerCase().includes(t)) return false
    return true
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredEdges.value.length / pageSize)))

const pagedEdges = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredEdges.value.slice(start, start + pageSize)
})

watch([searchSource, searchTarget, filterType], () => { selectedEdges.value = new Set(); page.value = 1 })
</script>

<style scoped>
.kg-edge-table { display: flex; flex-direction: column; gap: 10px; height: 100%; }
.toolbar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.search-input {
  padding: 6px 10px; border: 1px solid #d0d0d0; border-radius: 4px;
  font-size: 13px; min-width: 140px;
}
.type-filter {
  padding: 6px 8px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 13px;
}
.count-hint { font-size: 12px; color: #999; }
.spacer { flex: 1; }
.btn-create {
  padding: 6px 12px; background: #1976d2; color: #fff;
  border: none; border-radius: 4px; cursor: pointer; font-size: 13px;
}
.btn-create:hover { background: #1565c0; }
.btn-batch-delete {
  padding: 6px 12px; background: #c62828; color: #fff;
  border: none; border-radius: 4px; cursor: pointer; font-size: 13px;
}
.btn-batch-delete:hover { background: #b71c1c; }
.table-scroll {
  flex: 1; min-height: 0; max-height: 600px; overflow: auto;
  border: 1px solid #dde0e4; border-radius: 8px;
}
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead { position: sticky; top: 0; z-index: 1; background: #eef1f5; }
th {
  font-weight: 600; color: #333; padding: 10px;
  border-bottom: 2px solid #d0d4db; text-align: left; font-size: 12px;
}
td {
  padding: 8px 10px; border-bottom: 1px solid #eef0f3; color: #444;
}
tbody tr:nth-child(even) td { background: #f8f9fb; }
tbody tr:hover td { background: #e3f0fa; }
.col-idx { width: 50px; color: #aaa; text-align: center; }
.col-cb { width: 32px; text-align: center; }
.col-type { width: 160px; }
.col-actions { width: 100px; text-align: right; white-space: nowrap; }
.col-name {
  max-width: 280px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.rel-tag {
  display: inline-block; padding: 2px 8px; border-radius: 3px;
  font-size: 11px; color: #fff; background: #5e35b1;
}
.icon-btn {
  background: none; border: 1px solid; border-radius: 4px;
  cursor: pointer; padding: 3px 6px; margin-left: 4px; font-size: 12px;
}
.icon-btn.edit { color: #43a047; border-color: #43a047; }
.icon-btn.edit:hover { background: #e8f5e9; }
.icon-btn.delete { color: #c62828; border-color: #c62828; }
.icon-btn.delete:hover { background: #ffebee; }
.empty { text-align: center; color: #999; padding: 40px; }
.pager {
  display: flex; align-items: center; justify-content: center; gap: 12px;
  font-size: 13px; color: #666;
}
.pager button {
  padding: 4px 10px; border: 1px solid #d0d0d0;
  background: #fff; border-radius: 4px; cursor: pointer;
}
.pager button:disabled { color: #ccc; cursor: not-allowed; }
</style>
