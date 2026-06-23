<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h3>Cypher 查询语句</h3>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>
      <div class="modal-body">
        <pre class="cypher-code">{{ cypherText }}</pre>
        <div class="copy-hint">↑ 可复制到 Neo4j 浏览器中运行</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  cypherText: { type: String, default: '' },
})
defineEmits(['close'])
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: #fff;
  border-radius: 10px;
  width: 680px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}
.modal-header h3 {
  font-size: 15px;
  color: #333;
  margin: 0;
}
.close-btn {
  background: none; border: none; font-size: 18px;
  cursor: pointer; color: #999; padding: 2px 6px; border-radius: 4px;
}
.close-btn:hover { background: #f0f0f0; color: #555; }
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.cypher-code {
  margin: 0;
  padding: 16px;
  background: #1e1e2e;
  color: #a6e3a1;
  border-radius: 8px;
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: auto;
}
.copy-hint {
  text-align: center;
  margin-top: 12px;
  font-size: 12px;
  color: #999;
}
</style>