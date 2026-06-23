<template>
  <div class="kg-viewer">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="title-row">
        <h3>全局知识图谱</h3>
        <span class="badge" v-if="nodeCount">{{ nodeCount }} 实体</span>
      </div>
      <div class="actions">
        <input
          v-model="searchText"
          @input="debouncedSearch"
          placeholder="搜索实体..."
          class="search-input"
        />
        <button @click="loadGraph" class="btn-primary" :disabled="loading">
          {{ loading ? '加载中...' : '刷新' }}
        </button>
        <button @click="handleRebuild" class="btn-rebuild" :disabled="rebuilding">
          {{ rebuilding ? '重建中...' : '重建图谱' }}
        </button>
      </div>
    </div>

    <!-- 主体 -->
    <div class="main-area">
      <div ref="container" class="graph-canvas" :class="{ empty: !hasGraph }">
        <div v-if="!hasGraph && loaded" class="placeholder">
          图谱暂无数据，请上传文档或点击「重建图谱」
        </div>
      </div>

      <!-- 详情面板 -->
      <div v-if="selectedNode" class="detail-panel">
        <button class="close-detail" @click="deselectNode">✕</button>
        <h4>{{ selectedNode.name }}</h4>
        <span :class="['type-tag', selectedNode.type]">
          {{ typeLabel(selectedNode.type) }}
        </span>
        <p class="stat">关联文档片段: {{ selectedNode.chunk_count || 0 }}</p>
        <div v-if="selectedNode.relations?.length" class="relations">
          <h5>关系</h5>
          <div v-for="rel in selectedNode.relations" :key="rel.target + rel.type" class="rel-item">
            <span class="rel-type">{{ rel.type }}</span>
            <span class="rel-arrow">→</span>
            <span class="rel-target">{{ rel.target }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 图例 -->
    <div class="legend" v-if="hasGraph">
      <span v-for="t in typeLegend" :key="t.type" class="legend-item">
        <span class="dot" :style="{ background: t.color }"></span>
        {{ t.label }}
      </span>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { getGraph, rebuildGraph as rebuildGraphApi } from '../../api/index.js'

const container = ref(null)
const searchText = ref('')
const graphData = ref({ nodes: [], edges: [] })
const selectedNode = ref(null)
const loaded = ref(false)
const loading = ref(false)
const rebuilding = ref(false)
const error = ref('')
let network = null
let visNodes = null
let visEdges = null

const typeColors = {
  person: '#e91e63',
  org: '#2196f3',
  product: '#4caf50',
  concept: '#ff9800',
  location: '#9c27b0',
}

const typeLabels = {
  person: '人物', org: '组织', product: '产品/项目',
  concept: '概念', location: '地点',
}

const typeLegend = Object.entries(typeColors).map(([t, color]) => ({
  type: t, color, label: typeLabels[t] || t,
}))

function typeLabel(t) { return typeLabels[t] || t }

const hasGraph = computed(() => graphData.value.nodes?.length > 0)
const nodeCount = computed(() => graphData.value.nodes?.length)

// ── 加载 ──

async function loadGraph() {
  error.value = ''
  loading.value = true
  selectedNode.value = null

  try {
    const res = await getGraph()
    graphData.value = res.data
    loaded.value = true
    await nextTick()
    renderGraph()
  } catch (e) {
    error.value = '加载图谱失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

let searchTimer = null
function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (searchText.value.trim()) {
      highlightEntities(searchText.value.trim())
    } else {
      resetHighlight()
    }
  }, 300)
}

// ── 渲染 ──

function renderGraph() {
  if (!container.value) return
  if (network) { network.destroy(); network = null }

  const { nodes, edges } = graphData.value
  if (!nodes?.length) return

  visNodes = new DataSet(nodes.map(n => ({
    id: n.id,
    label: n.name,
    color: typeColors[n.type] || '#409EFF',
    title: `类型: ${typeLabels[n.type] || n.type}`,
    shape: 'dot',
    size: 22,
    font: { size: 12, color: '#444' },
    borderWidth: 2,
    borderColor: '#fff',
  })))

  visEdges = new DataSet(edges.map((e, i) => ({
    id: i,
    from: e.source,
    to: e.target,
    label: e.type,
    arrows: { to: { enabled: true, scaleFactor: 0.7 } },
    smooth: { type: 'continuous' },
    font: { size: 10, color: '#888', strokeWidth: 0 },
    color: { color: '#ccc', highlight: '#1976d2' },
    width: 1.5,
  })))

  network = new Network(container.value, { nodes: visNodes, edges: visEdges }, {
    nodes: {
      shape: 'dot',
      size: 22,
      font: { size: 12 },
      borderWidth: 2,
      shadow: true,
    },
    edges: {
      font: { size: 10 },
      smooth: { type: 'continuous' },
      arrows: { to: { enabled: true, scaleFactor: 0.7 } },
      width: 1.5,
    },
    physics: {
      enabled: true,
      barnesHut: {
        gravitationalConstant: -4000,
        centralGravity: 0.3,
        springLength: 180,
        springConstant: 0.04,
        damping: 0.09,
        avoidOverlap: 0.1,
      },
      stabilization: { enabled: true, iterations: 800 },
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      hideEdgesOnDrag: false,
    },
  })

  network.on('click', params => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0]
      const nodeData = nodes.find(n => n.id === nodeId)
      if (!nodeData) return

      const relations = edges
        .filter(e => e.source === nodeId || e.target === nodeId)
        .map(e => ({
          type: e.type,
          target: e.source === nodeId
            ? (nodes.find(n => n.id === e.target)?.name || e.target)
            : (nodes.find(n => n.id === e.source)?.name || e.source),
        }))

      selectedNode.value = { ...nodeData, relations }

      // 高亮选中节点和邻居
      visNodes.forEach(n => {
        visNodes.update({ id: n.id, color: n.id === nodeId ? '#FF6B6B' : (typeColors[n.type] || '#409EFF'), opacity: 1 })
      })
    } else {
      deselectNode()
    }
  })
}

function deselectNode() {
  selectedNode.value = null
  if (visNodes) {
    visNodes.forEach(n => {
      visNodes.update({ id: n.id, color: typeColors[n.type] || '#409EFF', opacity: 1 })
    })
  }
  if (visEdges) {
    visEdges.forEach(e => {
      visEdges.update({ id: e.id, color: { color: '#ccc', highlight: '#1976d2' }, opacity: 1 })
    })
  }
}

function highlightEntities(text) {
  if (!visNodes) return
  visNodes.forEach(n => {
    const name = n.label || ''
    if (name.includes(text)) {
      visNodes.update({ id: n.id, color: '#f44336', opacity: 1, size: 28 })
    } else {
      visNodes.update({ id: n.id, color: typeColors[n.type] || '#409EFF', opacity: 0.25, size: 18 })
    }
  })
}

function resetHighlight() {
  if (!visNodes) return
  visNodes.forEach(n => {
    visNodes.update({ id: n.id, color: typeColors[n.type] || '#409EFF', opacity: 1, size: 22 })
  })
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

onMounted(loadGraph)

onUnmounted(() => {
  if (network) { network.destroy(); network = null }
})
</script>

<style scoped>
.kg-viewer { display: flex; flex-direction: column; gap: 12px; min-height: 500px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.title-row { display: flex; align-items: center; gap: 8px; }
.title-row h3 { margin: 0; font-size: 16px; }
.badge { background: #e3f2fd; color: #1565c0; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.actions { display: flex; gap: 8px; align-items: center; }
.search-input { padding: 6px 10px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 13px; min-width: 180px; }
.btn-primary, .btn-rebuild { padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-primary { background: #1976d2; color: #fff; }
.btn-primary:disabled { background: #b0bec5; cursor: not-allowed; }
.btn-rebuild { background: #ff9800; color: #fff; }
.btn-rebuild:disabled { background: #e0e0e0; cursor: not-allowed; }
.main-area { display: flex; gap: 12px; flex: 1; min-height: 0; }
.graph-canvas { flex: 1; border: 1px solid #e0e0e0; border-radius: 6px; height: 600px; background: #fafafa; position: relative; }
.graph-canvas.empty { display: flex; align-items: center; justify-content: center; }
.placeholder { color: #999; font-size: 14px; }
.detail-panel { width: 240px; background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 14px; position: relative; align-self: flex-start; max-height: 400px; overflow-y: auto; }
.close-detail { position: absolute; top: 6px; right: 6px; border: none; background: none; cursor: pointer; color: #999; font-size: 14px; }
.detail-panel h4 { margin: 0 0 6px; font-size: 15px; }
.type-tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; color: #fff; margin-bottom: 8px; }
.type-tag.person { background: #e91e63; }
.type-tag.org { background: #2196f3; }
.type-tag.product { background: #4caf50; }
.type-tag.concept { background: #ff9800; }
.type-tag.location { background: #9c27b0; }
.stat { font-size: 13px; color: #666; margin: 4px 0; }
.relations h5 { margin: 10px 0 6px; font-size: 13px; color: #555; }
.rel-item { font-size: 12px; padding: 3px 0; display: flex; gap: 4px; align-items: center; }
.rel-type { color: #a0a0a0; font-style: italic; }
.rel-arrow { color: #ccc; }
.rel-target { color: #333; }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: #666; }
.legend-item { display: flex; align-items: center; gap: 4px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.error-msg { padding: 8px 12px; background: #ffebee; color: #c62828; border-radius: 4px; font-size: 13px; }
</style>