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
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: #fff;
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
  border-bottom: 1px solid #e0e0e0;
}
.modal-header h3 {
  font-size: 15px;
  color: #333;
  margin: 0;
}
.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #999;
  padding: 2px 6px;
  border-radius: 4px;
}
.close-btn:hover { background: #f0f0f0; color: #555; }
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}
.loading, .error {
  text-align: center;
  padding: 40px;
  color: #999;
  font-size: 14px;
}
.error { color: #c62828; }
.chunk-list { display: flex; flex-direction: column; gap: 12px; }
.chunk-item {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}
.chunk-header {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  font-size: 12px;
  color: #666;
}
.chunk-index { font-weight: 600; color: #333; }
.chunk-content {
  padding: 12px;
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #444;
  max-height: 300px;
  overflow-y: auto;
  background: #fafafa;
}
</style>