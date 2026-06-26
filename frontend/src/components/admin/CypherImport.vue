<template>
  <div class="cypher-import">
    <div class="cypher-header">
      <h4>执行 Cypher 语句</h4>
      <button class="btn-execute" :disabled="!cypher.trim() || executing" @click="execute">
        {{ executing ? '执行中...' : '▶ 执行' }}
      </button>
      <button class="btn-clear" @click="cypher = ''; result = null">清除</button>
    </div>

    <textarea
      v-model="cypher"
      class="cypher-input"
      rows="8"
      placeholder="CREATE (n:Entity {name: '张三', type: 'person'})
CREATE (m:Entity {name: '李四', type: 'person'})
CREATE (n)-[:朋友]->(m)"
      spellcheck="false"
    />

    <div v-if="result" :class="['result-box', { success: result.success, error: !result.success }]">
      <div class="result-icon">{{ result.success ? '✅' : '❌' }}</div>
      <div class="result-body">
        <div v-if="result.success" class="result-summary">{{ result.summary }}</div>
        <div v-else class="result-error">{{ result.error }}</div>
        <div v-if="result.warnings?.length" class="result-warnings">
          <div v-for="(w, wi) in result.warnings" :key="wi" class="result-warn-item">⚠️ {{ w }}</div>
        </div>
      </div>
    </div>

    <div class="hints">
      <div class="hint-title">注意事项：</div>
      <ul>
        <li>创建的 <code>type</code> 应先在「类型管理」中注册，否则图谱中该节点不显示颜色</li>
        <li>关系类型同样建议先在「类型管理」中注册，以获得正确的颜色和标签</li>
      </ul>
      <div class="hint-title" style="margin-top:6px">常见用法：</div>
      <div class="hint-item" @click="insertExample(1)">创建节点：<code>CREATE (n:Entity {name: '...', type: '...'})</code></div>
      <div class="hint-item" @click="insertExample(2)">创建关系：<code>MATCH (a:Entity {name: 'A'}), (b:Entity {name: 'B'}) CREATE (a)-[:关系名]->(b)</code></div>
      <div class="hint-item" @click="insertExample(3)">批量创建：<code>UNWIND [...] AS row CREATE (n:Entity {name: row.name, type: row.type})</code></div>
      <div class="hint-item" @click="insertExample(4)">查询全部：<code>MATCH (n) RETURN n.name, n.type LIMIT 100</code></div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { executeCypher } from '../../api/index.js'

const cypher = ref('')
const executing = ref(false)
const result = ref(null)

async function execute() {
  if (!cypher.value.trim()) return
  executing.value = true
  result.value = null
  try {
    const res = await executeCypher(cypher.value.trim())
    result.value = res.data
  } catch (e) {
    result.value = {
      success: false,
      summary: '',
      count: 0,
      error: e.response?.data?.detail || e.message,
    }
  } finally {
    executing.value = false
  }
}

const examples = [
  `CREATE (n:Entity {name: '新节点', type: 'concept'})`,
  `MATCH (a:Entity {name: '节点A'}), (b:Entity {name: '节点B'})
CREATE (a)-[:关联]->(b)`,
  `UNWIND [
  {name: '实体1', type: 'concept'},
  {name: '实体2', type: 'person'}
] AS row
CREATE (n:Entity {name: row.name, type: row.type, internal_id: randomUUID()})`,
  `MATCH (n) RETURN n.name, n.type, labels(n) AS labels LIMIT 100`,
]

function insertExample(index) {
  cypher.value = examples[index - 1]
  result.value = null
}
</script>

<style scoped>
.cypher-import { display: flex; flex-direction: column; gap: 12px; }
.cypher-header {
  display: flex; align-items: center; gap: 10px;
}
.cypher-header h4 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text-primary); }
.btn-execute, .btn-clear {
  padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;
}
.btn-execute { background: var(--color-primary); color: var(--text-inverse); margin-left: auto; }
.btn-execute:disabled { background: var(--text-muted); cursor: not-allowed; }
.btn-clear { background: var(--bg-hover); color: var(--text-secondary); }
.btn-clear:hover { background: var(--border-default); }
.cypher-input {
  width: 100%; padding: 12px; font-size: 13px;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  border: 1px solid var(--border-input); border-radius: 6px;
  resize: vertical; outline: none; line-height: 1.6;
  background: var(--code-bg); color: var(--code-text);
}
.cypher-input:focus { border-color: var(--color-primary); }
.result-box {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 12px; border-radius: 6px; font-size: 13px;
}
.result-box.success { background: var(--color-success-light); border: 1px solid var(--color-success); }
.result-box.error { background: var(--color-danger-light); border: 1px solid var(--color-danger); }
.result-icon { font-size: 18px; flex-shrink: 0; }
.result-body { flex: 1; }
.result-summary { color: var(--color-success); }
.result-error { color: var(--color-danger); white-space: pre-wrap; word-break: break-word; }
.result-warnings { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
.result-warn-item { color: var(--color-warning); font-size: 12px; background: var(--color-warning-light); padding: 4px 8px; border-radius: 4px; }
.hints {
  background: var(--bg-surface); border: 1px solid var(--border-default);
  border-radius: 6px; padding: 12px; font-size: 12px; line-height: 1.8;
}
.hint-title { font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.hints ul { margin: 0; padding-left: 16px; }
.hints li { color: var(--text-secondary); margin-bottom: 2px; }
.hint-item {
  color: var(--text-secondary); cursor: pointer; padding: 2px 0;
  transition: color 0.15s;
}
.hint-item:hover { color: var(--color-primary); }
.hint-item code {
  background: var(--code-bg); padding: 1px 5px; border-radius: 3px;
  font-size: 11px; color: var(--code-text);
}
</style>