<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal">
        <div class="modal-header">
          <h3>知识图谱</h3>
          <button class="close-btn" @click="$emit('close')">✕</button>
        </div>
        <div class="modal-body">
          <div class="depth-control">
            <label>显示深度: {{ depthLevel }} 层</label>
            <div class="depth-hint">{{ depthHint }}</div>
            <input
              type="range"
              v-model.number="depthLevel"
              min="1" max="5" step="1"
              @input="updateSubGraph"
              class="depth-slider"
            />
            <div class="depth-labels">
              <span>1-回答相关</span>
              <span>2-1跳</span>
              <span>3-2跳</span>
              <span>4</span>
              <span>5</span>
            </div>
          </div>
          <div ref="container" class="graph-canvas"></div>
          <div class="stats">
            <span>节点: {{ stats.nodes }}</span>
            <span>关系: {{ stats.edges }}</span>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { getGraph } from '../../api/index.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
  graphData: { type: Object, default: () => ({ nodes: [], edges: [] }) },
})

defineEmits(['close'])

const container = ref(null)
const depthLevel = ref(1)
const stats = ref({ nodes: 0, edges: 0 })
const fullData = ref({ nodes: [], edges: [] })
let network = null
const seedNodeNames = ref([])

const depthHint = computed(() => {
  if (depthLevel.value === 1) return '仅显示回答直接涉及的实体和关系'
  return `从回答实体出发，展开 ${depthLevel.value - 1} 跳关联`
})

const typeColors = {
  person: '#e91e63', org: '#2196f3', product: '#4caf50',
  concept: '#ff9800', location: '#9c27b0',
}

// 从 graphData 提取种子实体名
function extractSeeds(gd) {
  if (!gd?.nodes) return []
  return gd.nodes.map(n => n.name).filter(Boolean)
}

// 加载全量图谱（按需）
async function ensureFullGraph() {
  if (fullData.value.nodes.length > 0) return
  try {
    const res = await getGraph()
    fullData.value = res.data
  } catch (e) {
    console.warn('Failed to load full graph:', e)
    fullData.value = { nodes: [], edges: [] }
  }
}

// depth=1：直接用 SSE 传来的子图
function renderDirectGraph() {
  const gd = props.graphData
  if (!gd?.nodes?.length) return
  renderGraph(gd.nodes, gd.edges || [])
}

// depth>=2：从全量图 BFS 展开
function computeBFS(depth) {
  const seedNames = seedNodeNames.value
  if (!seedNames.length) return { nodes: [], edges: [] }

  const fn = fullData.value
  if (!fn.nodes?.length) return { nodes: [], edges: [] }

  // name → id 映射
  const nameToId = {}
  for (const n of fn.nodes) nameToId[n.name] = n.id

  const seedIds = new Set()
  for (const name of seedNames) {
    if (nameToId[name]) seedIds.add(nameToId[name])
  }

  const includedIds = new Set(seedIds)
  const includedEdges = []
  let frontier = new Set(seedIds)

  // 先加入 SSE graph 已有的边（确保回答路径保留）
  for (const e of (props.graphData.edges || [])) {
    if (includedIds.has(e.source) && includedIds.has(e.target)) {
      const key = `${e.source}-${e.target}-${e.type}`
      if (!includedEdges.find(x => `${x.source}-${x.target}-${x.type}` === key)) {
        includedEdges.push(e)
      }
    }
  }

  // BFS 展开 (depth-1) 跳
  for (let d = 0; d < depth - 1; d++) {
    const nextFrontier = new Set()
    for (const nodeId of frontier) {
      for (const edge of fn.edges) {
        if (edge.source === nodeId && !includedIds.has(edge.target)) {
          nextFrontier.add(edge.target)
          includedIds.add(edge.target)
          includedEdges.push(edge)
        }
        if (edge.target === nodeId && !includedIds.has(edge.source)) {
          nextFrontier.add(edge.source)
          includedIds.add(edge.source)
          includedEdges.push(edge)
        }
      }
    }
    // 补全 frontier 内节点之间的边
    for (const edge of fn.edges) {
      if (includedIds.has(edge.source) && includedIds.has(edge.target)) {
        const key = `${edge.source}-${edge.target}-${edge.type}`
        if (!includedEdges.find(x => `${x.source}-${x.target}-${x.type}` === key)) {
          includedEdges.push(edge)
        }
      }
    }
    frontier = nextFrontier
  }

  const nodes = fn.nodes.filter(n => includedIds.has(n.id))
  return { nodes, edges: includedEdges }
}

function renderGraph(nodes, edges) {
  if (!container.value) return
  if (network) { network.destroy(); network = null }

  if (!nodes.length) {
    stats.value = { nodes: 0, edges: 0 }
    return
  }

  const seedNames = seedNodeNames.value
  const seedIdSet = new Set()
  for (const n of nodes) {
    if (seedNames.includes(n.name)) seedIdSet.add(n.id)
  }

  const visNodes = new DataSet(nodes.map(n => ({
    id: n.id,
    label: n.name,
    color: seedIdSet.has(n.id) ? '#FF6B6B' : (typeColors[n.type] || '#409EFF'),
    title: `类型: ${n.type}`,
    shape: 'dot',
    size: seedIdSet.has(n.id) ? 26 : 22,
    font: { size: 13 },
    borderWidth: 2,
    shadow: true,
  })))

  const visEdges = new DataSet(edges.map((e, i) => ({
    id: i,
    from: e.source,
    to: e.target,
    label: e.type,
    arrows: { to: { enabled: true, scaleFactor: 0.7 } },
    smooth: { type: 'continuous' },
    font: { size: 11, color: '#888' },
    color: { color: '#ccc', highlight: '#409EFF' },
    width: 1.5,
  })))

  stats.value = { nodes: nodes.length, edges: edges.length }

  network = new Network(container.value, { nodes: visNodes, edges: visEdges }, {
    nodes: { size: 22, font: { size: 13 }, borderWidth: 2, shadow: true },
    edges: { font: { size: 11 }, smooth: { type: 'continuous' }, width: 1.5 },
    physics: {
      enabled: true,
      barnesHut: {
        gravitationalConstant: -3000, centralGravity: 0.3,
        springLength: 150, springConstant: 0.04,
        damping: 0.09, avoidOverlap: 0.1,
      },
      stabilization: { enabled: true, iterations: 500 },
    },
    interaction: { hover: true, tooltipDelay: 200 },
  })
}

async function updateSubGraph() {
  const depth = depthLevel.value
  if (depth === 1) {
    renderDirectGraph()
  } else {
    await ensureFullGraph()
    const { nodes, edges } = computeBFS(depth)
    renderGraph(nodes, edges)
  }
}

watch(() => props.visible, async (val) => {
  if (val) {
    seedNodeNames.value = extractSeeds(props.graphData)
    depthLevel.value = 1
    await nextTick()
    renderDirectGraph()
  } else if (network) {
    network.destroy()
    network = null
  }
})

onUnmounted(() => {
  if (network) { network.destroy(); network = null }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: #fff;
  border-radius: 10px;
  width: 800px;
  max-width: 92vw;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid #e0e0e0;
  background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%);
  color: #fff;
  border-radius: 10px 10px 0 0;
}
.modal-header h3 { margin: 0; font-size: 16px; }
.close-btn {
  background: rgba(255,255,255,0.2);
  border: none; color: #fff; font-size: 20px; cursor: pointer;
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.2s;
}
.close-btn:hover { background: rgba(255,255,255,0.35); }
.modal-body { padding: 16px 18px; }
.depth-control {
  display: flex; flex-direction: column; gap: 4px;
  background: #f5f5f5; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px;
}
.depth-control label { font-weight: 500; font-size: 13px; color: #555; }
.depth-hint { font-size: 11px; color: #999; }
.depth-slider {
  width: 100%; height: 5px;
  -webkit-appearance: none; appearance: none;
  background: linear-gradient(90deg, #1976d2, #42a5f5);
  border-radius: 3px; cursor: pointer; outline: none;
}
.depth-slider::-webkit-slider-thumb {
  -webkit-appearance: none; width: 18px; height: 18px;
  background: #fff; border: 2px solid #1976d2; border-radius: 50%; cursor: pointer;
}
.depth-labels { display: flex; justify-content: space-between; font-size: 10px; color: #999; padding: 0 2px; }
.graph-canvas { width: 100%; height: 480px; border: 1px solid #eee; border-radius: 6px; }
.stats {
  display: flex; justify-content: flex-end; gap: 16px; margin-top: 8px;
  font-size: 13px; color: #888;
}
.stats span { background: #f5f5f5; padding: 3px 10px; border-radius: 10px; }
</style>