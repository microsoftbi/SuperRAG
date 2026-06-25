<template>
  <div class="kg-node-table">
    <div class="toolbar">
      <input
        v-model="searchText"
        placeholder="按名称搜索..."
        class="search-input"
      />
      <select v-model="filterType" class="type-filter">
        <option value="">全部类型</option>
        <option v-for="t in allTypes" :key="t" :value="t">{{ t }}</option>
      </select>
      <span class="count-hint">共 {{ filteredNodes.length }} / {{ graphData.nodes.length }} 个节点</span>
      <div class="spacer" />
      <button v-if="selectedIds.size" class="btn-batch-delete" @click="$emit('batch-delete', [...selectedIds])">
        🗑️ 删除选中 ({{ selectedIds.size }})
      </button>
      <button @click="$emit('new')" class="btn-create">+ 新建节点</button>
    </div>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th class="col-cb">
              <input type="checkbox" :checked="allSelected" @change="toggleAll" />
            </th>
            <th class="col-idx">#</th>
            <th>名称</th>
            <th class="col-type">类型</th>
            <th class="col-num">关系数</th>
            <th class="col-num">Chunk数</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(n, i) in pagedNodes" :key="n.id" :class="{ selected: selectedIds.has(n.id) }">
            <td class="col-cb">
              <input type="checkbox" :checked="selectedIds.has(n.id)" @change="toggleOne(n.id)" />
            </td>
            <td class="col-idx">{{ (page - 1) * pageSize + i + 1 }}</td>
            <td class="col-name" :title="n.name">{{ n.name }}</td>
            <td class="col-type">
              <span class="type-tag">{{ n.type }}</span>
            </td>
            <td class="col-num">{{ relCountMap[n.id] || 0 }}</td>
            <td class="col-num">{{ n.chunk_count || 0 }}</td>
            <td class="col-actions">
              <button class="icon-btn locate" @click="$emit('locate', n)" title="在图谱中定位">🔍</button>
              <button class="icon-btn edit" @click="$emit('edit', n)" title="编辑">✏️</button>
              <button class="icon-btn delete" @click="$emit('delete', n)" title="删除">🗑️</button>
            </td>
          </tr>
          <tr v-if="!filteredNodes.length">
            <td colspan="7" class="empty">没有符合条件的节点</td>
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
const emit = defineEmits(['new', 'edit', 'delete', 'locate', 'batch-delete'])

const searchText = ref('')
const filterType = ref('')
const page = ref(1)
const pageSize = 30
const selectedIds = ref(new Set())

const allSelected = computed(() =>
  pagedNodes.value.length > 0 && pagedNodes.value.every(n => selectedIds.value.has(n.id))
)

function toggleAll() {
  if (allSelected.value) {
    pagedNodes.value.forEach(n => selectedIds.value.delete(n.id))
  } else {
    pagedNodes.value.forEach(n => selectedIds.value.add(n.id))
  }
  selectedIds.value = new Set(selectedIds.value)
}

function toggleOne(id) {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
  selectedIds.value = new Set(selectedIds.value)
}

watch([searchText, filterType], () => { selectedIds.value = new Set(); page.value = 1 })

const allTypes = computed(() => {
  const s = new Set()
  props.graphData.nodes.forEach(n => n.type && s.add(n.type))
  return [...s].sort()
})

// 关系数：从 edges 聚合
const relCountMap = computed(() => {
  const m = {}
  props.graphData.edges.forEach(e => {
    m[e.source] = (m[e.source] || 0) + 1
    m[e.target] = (m[e.target] || 0) + 1
  })
  return m
})

const filteredNodes = computed(() => {
  const t = searchText.value.trim().toLowerCase()
  return props.graphData.nodes.filter(n => {
    if (filterType.value && n.type !== filterType.value) return false
    if (t && !n.name.toLowerCase().includes(t)) return false
    return true
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredNodes.value.length / pageSize)))

const pagedNodes = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredNodes.value.slice(start, start + pageSize)
})

watch([searchText, filterType], () => { page.value = 1 })
</script>

<style scoped>
.kg-node-table { display: flex; flex-direction: column; gap: 10px; height: 100%; }
.toolbar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.search-input {
  padding: 6px 10px; border: 1px solid #d0d0d0; border-radius: 4px;
  font-size: 13px; min-width: 200px;
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
table {
  width: 100%; border-collapse: collapse; font-size: 13px;
}
thead {
  position: sticky; top: 0; z-index: 1;
  background: #eef1f5;
}
th {
  font-weight: 600; color: #333; padding: 10px;
  border-bottom: 2px solid #d0d4db; text-align: left;
  font-size: 12px;
}
td {
  padding: 8px 10px; border-bottom: 1px solid #eef0f3;
  color: #444;
}
tbody tr:nth-child(even) td { background: #f8f9fb; }
tbody tr:hover td { background: #e3f0fa; }
.col-idx { width: 50px; color: #aaa; text-align: center; }
.col-cb { width: 32px; text-align: center; }
.col-type { width: 110px; }
.col-num { width: 70px; text-align: right; font-variant-numeric: tabular-nums; }
.col-actions { width: 130px; text-align: right; white-space: nowrap; }
.col-name {
  max-width: 280px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.type-tag {
  display: inline-block; padding: 2px 8px; border-radius: 3px;
  font-size: 11px; color: #fff; background: #607d8b;
}
.icon-btn {
  background: none; border: 1px solid; border-radius: 4px;
  cursor: pointer; padding: 3px 6px; margin-left: 4px; font-size: 12px;
}
.icon-btn.locate { color: #1976d2; border-color: #1976d2; }
.icon-btn.locate:hover { background: #e3f2fd; }
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
