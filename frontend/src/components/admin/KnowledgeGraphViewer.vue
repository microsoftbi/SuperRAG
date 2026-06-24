<template>
  <div class="kg-container">
    <div class="kg-header">
      <h3>全局知识图谱</h3>
      <span v-if="graphData.nodes.length" class="kg-badge">
        {{ graphData.nodes.length }} 实体 · {{ graphData.edges.length }} 关系
      </span>
      <div class="header-actions">
        <button @click="loadGraph" class="btn-primary" :disabled="loading">
          {{ loading ? '加载中...' : '🔄 刷新' }}
        </button>
        <button @click="handleRebuild" class="btn-rebuild" :disabled="rebuilding">
          {{ rebuilding ? '重建中...' : '🛠 重建图谱' }}
        </button>
      </div>
    </div>

    <div class="kg-tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        :class="['kg-tab', { active: activeTab === t.key }]"
        @click="activeTab = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <div class="kg-body">
      <KgGraphTab
        v-if="activeTab === 'graph'"
        :graph-data="graphData"
        :loading="loading"
        @edit-node="openNodeEditor"
        @delete-node="confirmDeleteNode"
        @new-node="openNodeEditor(null)"
        @new-edge="openEdgeEditor(null)"
        @delete-edge="confirmDeleteEdge"
        @edit-edge="openEdgeEditor"
      />
      <KgNodeTable
        v-if="activeTab === 'nodes'"
        :graph-data="graphData"
        @new="openNodeEditor(null)"
        @edit="openNodeEditor"
        @delete="confirmDeleteNode"
        @locate="locateInGraph"
      />
      <KgEdgeTable
        v-if="activeTab === 'edges'"
        :graph-data="graphData"
        @new="openEdgeEditor(null)"
        @edit="openEdgeEditor"
        @delete="confirmDeleteEdge"
      />
    </div>

    <KgNodeEditor
      v-if="editorNode !== undefined"
      :node="editorNode"
      :existing-names="existingNodeNames"
      @close="editorNode = undefined"
      @saved="onNodeSaved"
    />

    <KgEdgeEditor
      v-if="editorEdge !== undefined"
      :edge="editorEdge"
      :nodes="graphData.nodes"
      :existing-rel-types="existingRelTypes"
      @close="editorEdge = undefined"
      @saved="onEdgeSaved"
    />

    <div v-if="error" class="error-msg">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import KgGraphTab from './KgGraphTab.vue'
import KgNodeTable from './KgNodeTable.vue'
import KgEdgeTable from './KgEdgeTable.vue'
import KgNodeEditor from './KgNodeEditor.vue'
import KgEdgeEditor from './KgEdgeEditor.vue'
import {
  getGraph, rebuildGraph as rebuildGraphApi,
  deleteEntity, deleteRelationship, getEntityRelCount,
} from '../../api/index.js'

const tabs = [
  { key: 'graph', label: '🌐 图谱视图' },
  { key: 'nodes', label: '📦 节点管理' },
  { key: 'edges', label: '🔗 关系管理' },
]

const activeTab = ref('graph')
const graphData = ref({ nodes: [], edges: [] })
const loading = ref(false)
const rebuilding = ref(false)
const error = ref('')

// editor 用 undefined 表示关闭，null 表示新建，object 表示编辑
const editorNode = ref(undefined)
const editorEdge = ref(undefined)

// 用于切回图谱视图后聚焦节点
const pendingFocusId = ref('')

const existingNodeNames = computed(() =>
  new Set(graphData.value.nodes.map(n => n.name))
)
const existingRelTypes = computed(() => {
  const s = new Set()
  graphData.value.edges.forEach(e => e.type && s.add(e.type))
  return [...s].sort()
})

async function loadGraph() {
  error.value = ''
  loading.value = true
  try {
    const res = await getGraph()
    graphData.value = res.data
  } catch (e) {
    error.value = '加载图谱失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function handleRebuild() {
  if (!confirm('确定重建全局图谱？将重新提取所有文档的实体关系。')) return
  rebuilding.value = true
  error.value = ''
  try {
    await rebuildGraphApi()
    await loadGraph()
  } catch (e) {
    error.value = '重建失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    rebuilding.value = false
  }
}

function openNodeEditor(node) {
  editorNode.value = node  // null = 新建，object = 编辑
}

function openEdgeEditor(edge) {
  editorEdge.value = edge
}

async function onNodeSaved() {
  editorNode.value = undefined
  await loadGraph()
}

async function onEdgeSaved() {
  editorEdge.value = undefined
  await loadGraph()
}

async function confirmDeleteNode(node) {
  try {
    const res = await getEntityRelCount(node.id)
    const cnt = res.data?.count ?? 0
    const msg = cnt > 0
      ? `确定删除节点 "${node.name}"？\n\n将同时删除该节点的 ${cnt} 条关系，此操作不可撤销。`
      : `确定删除节点 "${node.name}"？此操作不可撤销。`
    if (!confirm(msg)) return
    await deleteEntity(node.id)
    await loadGraph()
  } catch (e) {
    alert('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function confirmDeleteEdge(edge) {
  const srcName = nameOf(edge.source)
  const dstName = nameOf(edge.target)
  if (!confirm(`确定删除关系 "${srcName} --(${edge.type})--> ${dstName}" ？`)) return
  try {
    await deleteRelationship({ source: srcName, target: dstName, type: edge.type })
    await loadGraph()
  } catch (e) {
    alert('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

function nameOf(idOrName) {
  // edges 里的 source/target 是 node id
  const n = graphData.value.nodes.find(x => x.id === idOrName)
  return n ? n.name : idOrName
}

function locateInGraph(node) {
  pendingFocusId.value = node.id
  activeTab.value = 'graph'
}

onMounted(loadGraph)
</script>

<style scoped>
.kg-container { display: flex; flex-direction: column; gap: 12px; min-height: 600px; }
.kg-header {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.kg-header h3 { margin: 0; font-size: 16px; }
.kg-badge {
  background: #e3f2fd; color: #1565c0;
  padding: 3px 10px; border-radius: 10px; font-size: 12px;
}
.header-actions { margin-left: auto; display: flex; gap: 8px; }
.btn-primary, .btn-rebuild {
  padding: 6px 14px; border: none; border-radius: 4px;
  cursor: pointer; font-size: 13px;
}
.btn-primary { background: #1976d2; color: #fff; }
.btn-primary:disabled { background: #b0bec5; cursor: not-allowed; }
.btn-rebuild { background: #ff9800; color: #fff; }
.btn-rebuild:disabled { background: #e0e0e0; cursor: not-allowed; }
.kg-tabs {
  display: flex; gap: 0; border-bottom: 1px solid #e0e0e0;
}
.kg-tab {
  background: none; border: none; padding: 8px 16px;
  font-size: 13px; cursor: pointer; color: #666;
  border-bottom: 2px solid transparent;
}
.kg-tab.active {
  color: #1976d2; border-bottom-color: #1976d2; font-weight: 600;
}
.kg-tab:hover:not(.active) { color: #333; }
.kg-body { flex: 1; min-height: 500px; }
.error-msg {
  padding: 8px 12px; background: #ffebee; color: #c62828;
  border-radius: 4px; font-size: 13px;
}
</style>
