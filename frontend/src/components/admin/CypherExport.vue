<template>
  <div class="cypher-export">
    <div class="export-header">
      <h4>导出 Cypher 语句</h4>
      <div class="header-actions">
        <button class="btn-export" :disabled="loading" @click="loadExport">
          {{ loading ? '加载中...' : '🔄 刷新' }}
        </button>
        <button v-if="cypherText" class="btn-download" @click="downloadFile">⬇️ 下载 .cypher</button>
        <button v-if="cypherText" class="btn-copy" @click="copyText">
          {{ copied ? '✅ 已复制' : '📋 复制' }}
        </button>
      </div>
    </div>

    <div v-if="!cypherText && !loading" class="empty">
      点击「刷新」按钮，导出当前知识图谱中所有节点和关系的 Cypher 语句。
    </div>

    <div v-if="loading" class="loading">正在生成导出...</div>

    <div v-if="error" class="error-msg">❌ {{ error }}</div>

    <div v-if="cypherText" class="export-info">
      共 {{ nodeCount }} 个节点，{{ edgeCount }} 条关系
    </div>

    <textarea
      v-if="cypherText"
      :value="cypherText"
      class="cypher-output"
      readonly
      rows="18"
      spellcheck="false"
    ></textarea>

    <div class="hints">
      <div class="hint-title">说明：</div>
      <ul>
        <li>导出的 Cypher 语句可直接在「Cypher 导入」中执行，用于图谱迁移或备份</li>
        <li>节点使用 <code>:Entity</code> 标签，包含 name、type、internal_id 等属性</li>
        <li>关系使用无向匹配（<code>MATCH (a)-[r]-(b)</code>），已自动去重</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { api } from '../../api/index.js'

const cypherText = ref('')
const loading = ref(false)
const error = ref('')
const copied = ref(false)

const nodeCount = computed(() => {
  const m = cypherText.value.match(/CREATE \(/g)
  return m ? m.length : 0
})

const edgeCount = computed(() => {
  const afterNodes = cypherText.value.split('\n\n// 关系')[1]
  if (!afterNodes) return 0
  const m = afterNodes.match(/CREATE \(/g)
  return m ? m.length : 0
})

async function loadExport() {
  loading.value = true
  error.value = ''
  copied.value = false
  try {
    const res = await api.get('/knowledge-graph/cypher-export', {
      responseType: 'text',
    })
    cypherText.value = typeof res.data === 'string' ? res.data : res.request?.responseText || ''
    if (!cypherText.value) {
      error.value = '返回内容为空'
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
    cypherText.value = ''
  } finally {
    loading.value = false
  }
}

function downloadFile() {
  const blob = new Blob([cypherText.value], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'graph_export.cypher'
  a.click()
  URL.revokeObjectURL(url)
}

async function copyText() {
  try {
    await navigator.clipboard.writeText(cypherText.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch { /* ignore */ }
}
</script>

<style scoped>
.cypher-export { display: flex; flex-direction: column; gap: 12px; }
.export-header {
  display: flex; align-items: center; gap: 10px;
}
.export-header h4 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text-primary); }
.header-actions { margin-left: auto; display: flex; gap: 6px; }
.btn-export, .btn-download, .btn-copy {
  padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;
}
.btn-export { background: var(--color-primary); color: var(--text-inverse); }
.btn-export:disabled { background: var(--text-muted); cursor: not-allowed; }
.btn-download { background: var(--color-success); color: var(--text-inverse); }
.btn-copy { background: var(--bg-hover); color: var(--text-secondary); }
.btn-copy:hover { background: var(--border-default); }
.empty {
  text-align: center; padding: 40px; font-size: 14px; color: var(--text-tertiary);
}
.loading { text-align: center; padding: 20px; color: var(--text-secondary); }
.error-msg {
  padding: 8px 12px; background: var(--color-danger-light); color: var(--color-danger);
  border-radius: 4px; font-size: 13px;
}
.export-info {
  font-size: 13px; color: var(--color-success); font-weight: 500;
}
.cypher-output {
  width: 100%; padding: 12px; font-size: 12px;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  border: 1px solid var(--border-input); border-radius: 6px;
  resize: vertical; outline: none; line-height: 1.6;
  background: var(--code-bg); color: var(--code-text);
}
.hints {
  background: var(--bg-surface); border: 1px solid var(--border-default);
  border-radius: 6px; padding: 12px; font-size: 12px; line-height: 1.8;
}
.hint-title { font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.hints ul { margin: 0; padding-left: 16px; }
.hints li { color: var(--text-secondary); margin-bottom: 2px; }
.hints code {
  background: var(--code-bg); padding: 1px 5px; border-radius: 3px;
  font-size: 11px; color: var(--code-text);
}
</style>