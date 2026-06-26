<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h3>{{ docTitle }} — 分块详情</h3>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>
      <div class="modal-body">
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else class="chunk-list">
          <div v-for="(chunk, i) in chunks" :key="chunk.chunk_id" class="chunk-item">
            <div class="chunk-header">
              <span class="chunk-index">分块 #{{ i + 1 }}</span>
              <span class="chunk-meta">
                {{ chunk.content.length }} 字
              </span>
            </div>
            <pre class="chunk-content">{{ chunk.content }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDocumentChunks } from '../../api/index.js'

const props = defineProps({
  documentId: { type: Number, required: true },
  docTitle: { type: String, default: '' },
})
defineEmits(['close'])

const chunks = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const res = await getDocumentChunks(props.documentId)
    chunks.value = res.data.chunks || []
  } catch (e) {
    error.value = e.response?.data?.detail || '加载分块失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: var(--bg-card);
  border-radius: 10px;
  width: 700px;
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-default);
}
.modal-header h3 {
  font-size: 15px;
  color: var(--text-primary);
  margin: 0;
}
.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--text-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
}
.close-btn:hover { background: var(--bg-hover); color: var(--text-secondary); }
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}
.loading, .error {
  text-align: center;
  padding: 40px;
  color: var(--text-tertiary);
  font-size: 14px;
}
.error { color: var(--color-danger); }
.chunk-list { display: flex; flex-direction: column; gap: 12px; }
.chunk-item {
  border: 1px solid var(--border-default);
  border-radius: 6px;
  overflow: hidden;
}
.chunk-header {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-page);
  border-bottom: 1px solid var(--border-default);
  font-size: 12px;
  color: var(--text-secondary);
}
.chunk-index { font-weight: 600; color: var(--text-primary); }
.chunk-content {
  padding: 12px;
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: var(--text-primary);
  max-height: 300px;
  overflow-y: auto;
  background: var(--bg-surface);
}
</style>