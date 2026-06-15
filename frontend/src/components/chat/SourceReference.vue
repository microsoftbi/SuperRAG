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
        <div v-if="expanded[i]" class="preview">{{ src.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ sources: { type: Array, required: true } })
const expanded = ref({})
</script>

<style scoped>
.source-references { margin-top: 8px; padding-top: 8px; border-top: 1px solid #e0e0e0; }
.label { font-size: 12px; color: #666; margin-bottom: 4px; }
.items { display: flex; flex-wrap: wrap; gap: 6px; }
.source-item {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; background: #e3f2fd; border-radius: 4px;
  font-size: 12px; cursor: pointer;
}
.badge { font-weight: bold; color: #1976d2; }
.title { color: #555; }
.score { color: #999; font-size: 11px; }
.preview { margin-top: 4px; padding: 4px; background: #fff; border-radius: 4px; font-size: 12px; color: #666; width: 100%; }
</style>
