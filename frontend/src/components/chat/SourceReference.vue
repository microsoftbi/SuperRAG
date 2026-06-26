<template>
  <div class="source-references">
    <div class="label">来源引用：</div>
    <div class="items">
      <div
        v-for="(src, i) in sources"
        :key="i"
        class="source-item"
        @click="expanded[i] = !expanded[i]"
      >
        <span class="badge">{{ i + 1 }}</span>
        <span class="title">{{ src.document_title }}</span>
        <span class="score">{{ (src.score * 100).toFixed(0) }}%</span>
        <button
          v-if="src.type === 'kg' && src.graph"
          class="graph-btn"
          @click.stop="emit('show-graph', src.graph)"
          title="查看知识图谱"
        >
          ⛓ 图谱
        </button>
        <button
          v-if="src.type === 'kg' && src.cypher"
          class="cypher-btn"
          @click.stop="showCypher(src.cypher)"
          title="查看 Cypher 查询"
        >
          🔍 Cypher
        </button>
        <div v-if="expanded[i]" class="preview">{{ src.content }}</div>
      </div>
    </div>

    <CypherQueryModal
      v-if="cypherText"
      :cypher-text="cypherText"
      @close="cypherText = ''"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import CypherQueryModal from './CypherQueryModal.vue'

const props = defineProps({ sources: { type: Array, required: true } })
const emit = defineEmits(['show-graph'])
const expanded = ref({})
const cypherText = ref('')

function showCypher(text) {
  cypherText.value = text
}
</script>

<style scoped>
.source-references { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-default); }
.label { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
.items { display: flex; flex-wrap: wrap; gap: 6px; }
.source-item {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 8px; background: var(--bg-active); border-radius: 4px;
  font-size: 12px; cursor: pointer;
}
.badge { font-weight: bold; color: var(--color-primary); }
.title { color: var(--text-secondary); }
.score { color: var(--text-tertiary); font-size: 11px; }
.graph-btn {
  padding: 1px 6px; border: 1px solid var(--color-warning); background: var(--color-warning-light);
  color: var(--color-warning); border-radius: 3px; cursor: pointer; font-size: 11px;
  line-height: 1.4;
}
.graph-btn:hover { background: #ffe0b2; }
.cypher-btn {
  padding: 1px 6px; border: 1px solid var(--color-success); background: var(--color-success-light);
  color: var(--color-success); border-radius: 3px; cursor: pointer; font-size: 11px;
  line-height: 1.4;
}
.cypher-btn:hover { background: #c8e6c9; }
.preview { margin-top: 4px; padding: 4px; background: var(--bg-card); border-radius: 4px; font-size: 12px; color: var(--text-secondary); width: 100%; white-space: pre-wrap; }
</style>