<template>
  <div class="kg-graph-tab">
    <div class="toolbar">
      <input
        v-model="searchText"
        @input="debouncedSearch"
        placeholder="搜索实体..."
        class="search-input"
      />
      <div class="spacer" />
      <button @click="$emit('new-node')" class="btn-create">+ 新建节点</button>
      <button @click="$emit('new-edge')" class="btn-create">+ 新建关系</button>
    </div>

    <div class="main-area">
      <div ref="container" class="graph-canvas" :class="{ empty: !hasGraph }">
        <div v-if="!hasGraph && !loading" class="placeholder">
          图谱暂无数据
        </div>
      </div>

      <div v-if="selectedNode" class="detail-panel">
        <button class="close-detail" @click="deselectNode">✕</button>
        <h4>{{ selectedNode.name }}</h4>
        <span class="type-tag">{{ selectedNode.type }}</span>
        <p class="stat">关联文档片段: {{ selectedNode.chunk_count || 0 }}</p>
        <p class="stat">关系数: {{ selectedNode.relations?.length || 0 }}</p>
        <div class="detail-actions">
          <button class="btn-edit" @click="$emit('edit-node', selectedNode)">✏️ 编辑</button>
          <button class="btn-delete" @click="$emit('delete-node', selectedNode)">🗑️ 删除</button>
        </div>
        <div v-if="selectedNode.relations?.length" class="relations">
          <h5>关系 ({{ selectedNode.relations.length }})</h5>
          <div v-for="(rel, ri) in selectedNode.relations" :key="ri" class="rel-item">
            <span class="rel-dir">{{ rel.dir }}</span>
            <span class="rel-type">{{ rel.type }}</span>
            <span class="rel-target" :title="rel.target">{{ rel.target }}</span>
            <button class="rel-del" @click="$emit('delete-edge', rel.edge)" title="删除该关系">🗑</button>
          </div>
        </div>
      </div>
    </div>

    <div class="legend" v-if="hasGraph">
      <span v-for="t in typeLegend" :key="t.type" class="legend-item">
        <span class="dot" :style="{ background: t.color }"></span>
        {{ t.label }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'

const props = defineProps({
  graphData: { type: Object, required: true },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits([
  'edit-node', 'delete-node', 'new-node',
  'new-edge', 'edit-edge', 'delete-edge',
])

const container = ref(null)
const searchText = ref('')
const selectedNode = ref(null)
let network = null
let visNodes = null
let visEdges = null

const typeColors = {
  person: '#e91e63', org: '#2196f3', product: '#4caf50',
  concept: '#ff9800', location: '#9c27b0',
}
const typeLabels = {
  person: '人物', org: '组织', product: '产品/项目',
  concept: '概念', location: '地点',
}
const typeLegend = Object.entries(typeColors).map(([t, color]) => ({
  type: t, color, label: typeLabels[t] || t,
}))

const hasGraph = computed(() => props.graphData.nodes?.length > 0)

function colorForType(t) { return typeColors[t] || '#90a4ae' }

function renderGraph() {
  if (!container.value) return
  if (network) { network.destroy(); network = null }

  const { nodes, edges } = props.graphData
  if (!nodes?.length) return

  visNodes = new DataSet(nodes.map(n => ({
    id: n.id,
    label: n.name,
    color: colorForType(n.type),
    title: `${n.name} · ${typeLabels[n.type] || n.type}`,
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
    nodes: { shape: 'dot', size: 22, font: { size: 12 }, borderWidth: 2, shadow: true },
    edges: { font: { size: 10 }, smooth: { type: 'continuous' }, width: 1.5 },
    physics: {
      enabled: true,
      barnesHut: {
        gravitationalConstant: -4000, centralGravity: 0.3,
        springLength: 180, springConstant: 0.04,
        damping: 0.09, avoidOverlap: 0.1,
      },
      stabilization: { enabled: true, iterations: 800 },
    },
    interaction: { hover: true, tooltipDelay: 200, hideEdgesOnDrag: false },
  })

  network.on('click', params => {
    if (params.nodes.length > 0) {
      selectNodeById(params.nodes[0])
    } else if (params.edges.length > 0) {
      // 单击边时只高亮，不弹菜单（按设计暂不需要右键菜单）
    } else {
      deselectNode()
    }
  })
}

function selectNodeById(nodeId) {
  const { nodes, edges } = props.graphData
  const nodeData = nodes.find(n => n.id === nodeId)
  if (!nodeData) return

  const relations = edges
    .filter(e => e.source === nodeId || e.target === nodeId)
    .map(e => ({
      type: e.type,
      dir: e.source === nodeId ? '→' : '←',
      target: e.source === nodeId
        ? (nodes.find(n => n.id === e.target)?.name || e.target)
        : (nodes.find(n => n.id === e.source)?.name || e.source),
      edge: e,
    }))

  selectedNode.value = { ...nodeData, relations }

  if (visNodes) {
    visNodes.forEach(n => {
      visNodes.update({
        id: n.id,
        color: n.id === nodeId ? '#FF6B6B' : colorForType(nodeData.type === undefined ? '' : props.graphData.nodes.find(x => x.id === n.id)?.type),
      })
    })
  }
  if (network) network.focus(nodeId, { animation: { duration: 400 } })
}

function deselectNode() {
  selectedNode.value = null
  if (visNodes) {
    visNodes.forEach(n => {
      const orig = props.graphData.nodes.find(x => x.id === n.id)
      visNodes.update({ id: n.id, color: colorForType(orig?.type) })
    })
  }
}

let searchTimer = null
function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    const t = searchText.value.trim()
    if (t) highlightEntities(t)
    else resetHighlight()
  }, 300)
}

function highlightEntities(text) {
  if (!visNodes) return
  visNodes.forEach(n => {
    const orig = props.graphData.nodes.find(x => x.id === n.id)
    const matched = (n.label || '').includes(text)
    visNodes.update({
      id: n.id,
      color: matched ? '#f44336' : colorForType(orig?.type),
      opacity: matched ? 1 : 0.25,
      size: matched ? 28 : 18,
    })
  })
}

function resetHighlight() {
  if (!visNodes) return
  visNodes.forEach(n => {
    const orig = props.graphData.nodes.find(x => x.id === n.id)
    visNodes.update({ id: n.id, color: colorForType(orig?.type), opacity: 1, size: 22 })
  })
}

watch(() => props.graphData, async () => {
  selectedNode.value = null
  await nextTick()
  renderGraph()
}, { deep: false })

onMounted(() => {
  nextTick(renderGraph)
})

onUnmounted(() => {
  if (network) { network.destroy(); network = null }
})
</script>

<style scoped>
.kg-graph-tab { display: flex; flex-direction: column; gap: 10px; }
.toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.search-input {
  padding: 6px 10px; border: 1px solid #d0d0d0; border-radius: 4px;
  font-size: 13px; min-width: 200px;
}
.spacer { flex: 1; }
.btn-create {
  padding: 6px 12px; background: #1976d2; color: #fff;
  border: none; border-radius: 4px; cursor: pointer; font-size: 13px;
}
.btn-create:hover { background: #1565c0; }
.main-area { display: flex; gap: 12px; min-height: 0; }
.graph-canvas {
  flex: 1; border: 1px solid #e0e0e0; border-radius: 6px;
  height: 600px; background: #fafafa; position: relative;
}
.graph-canvas.empty { display: flex; align-items: center; justify-content: center; }
.placeholder { color: #999; font-size: 14px; }
.detail-panel {
  width: 280px; background: #fff; border: 1px solid #e0e0e0;
  border-radius: 6px; padding: 14px; position: relative;
  align-self: flex-start; max-height: 600px; overflow-y: auto;
}
.close-detail {
  position: absolute; top: 6px; right: 6px;
  border: none; background: none; cursor: pointer; color: #999; font-size: 14px;
}
.detail-panel h4 { margin: 0 0 6px; font-size: 15px; word-break: break-all; }
.type-tag {
  display: inline-block; padding: 2px 8px; border-radius: 3px;
  font-size: 11px; color: #fff; background: #607d8b; margin-bottom: 8px;
}
.stat { font-size: 13px; color: #666; margin: 4px 0; }
.detail-actions { display: flex; gap: 6px; margin: 10px 0; }
.btn-edit, .btn-delete {
  flex: 1; padding: 5px 0; font-size: 12px;
  border: 1px solid; border-radius: 4px; cursor: pointer;
}
.btn-edit { color: #1976d2; border-color: #1976d2; background: #fff; }
.btn-edit:hover { background: #e3f2fd; }
.btn-delete { color: #c62828; border-color: #c62828; background: #fff; }
.btn-delete:hover { background: #ffebee; }
.relations h5 { margin: 10px 0 6px; font-size: 13px; color: #555; }
.rel-item {
  font-size: 12px; padding: 4px 0;
  display: flex; gap: 6px; align-items: center;
  border-bottom: 1px dashed #eee;
}
.rel-dir { color: #1976d2; font-weight: bold; }
.rel-type { color: #a0a0a0; font-style: italic; flex-shrink: 0; }
.rel-target {
  color: #333; flex: 1; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.rel-del {
  background: none; border: none; cursor: pointer;
  color: #999; font-size: 12px; padding: 0 4px;
}
.rel-del:hover { color: #c62828; }
.legend {
  display: flex; gap: 16px; flex-wrap: wrap;
  font-size: 12px; color: #666;
}
.legend-item { display: flex; align-items: center; gap: 4px; }
.dot { width: 10px; height: 10px; border-radius: 50%; }
</style>
