<template>
  <div class="uploader">
    <h2>上传文档</h2>
    <div class="form">
      <input type="file" @change="onFileChange" accept=".pdf,.docx,.md,.html,.htm,.txt" />
      <input v-model="title" placeholder="文档标题（可选）" />
      <div class="store-select">
        <span class="form-label">存储目标：</span>
        <label class="radio-option" :class="{ active: store === 'vector' }">
          <input type="radio" value="vector" v-model="store" />
          <span class="radio-label">向量数据库</span>
          <span class="radio-desc">全文检索、语义搜索</span>
        </label>
        <label class="radio-option" :class="{ active: store === 'graph' }">
          <input type="radio" value="graph" v-model="store" />
          <span class="radio-label">图数据库</span>
          <span class="radio-desc">实体关系提取、多跳推理</span>
        </label>
        <label class="radio-option" :class="{ active: store === 'both' }">
          <input type="radio" value="both" v-model="store" />
          <span class="radio-label">全部</span>
          <span class="radio-desc">两个数据库都存储</span>
        </label>
      </div>
      <div class="kb-select" v-if="store !== 'graph'">
        <span class="form-label">知识库：</span>
        <label v-for="kb in kbs" :key="kb.id" class="kb-option">
          <input type="checkbox" :value="kb.id" v-model="selectedKbIds" />
          {{ kb.name }}
        </label>
      </div>
      <button @click="upload" :disabled="!file || uploading">
        {{ uploading ? '上传中...' : '上传' }}
      </button>
      <span v-if="message" :class="['msg', msgType]">{{ message }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { uploadDocument, listKnowledgeBases } from '../../api/index.js'

const emit = defineEmits(['uploaded'])
const file = ref(null)
const title = ref('')
const store = ref('vector')
const kbs = ref([])
const selectedKbIds = ref([])
const uploading = ref(false)
const message = ref('')
const msgType = ref('')

function onFileChange(e) {
  file.value = e.target.files[0] || null
}

async function upload() {
  if (!file.value) return
  uploading.value = true
  message.value = ''
  try {
    await uploadDocument(file.value, title.value, 'default', selectedKbIds.value, store.value)
    message.value = '上传成功！'
    msgType.value = 'success'
    file.value = null
    title.value = ''
    store.value = 'vector'
    selectedKbIds.value = []
    emit('uploaded')
  } catch (err) {
    message.value = err.response?.data?.detail || '上传失败'
    msgType.value = 'error'
  } finally {
    uploading.value = false
  }
}

onMounted(async () => {
  try {
    const res = await listKnowledgeBases()
    kbs.value = res.data
  } catch { /* ignore */ }
})
</script>

<style scoped>
.uploader {
  padding: 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
}
.uploader h2 { font-size: 16px; margin-bottom: 12px; }
.form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.form input[type="file"] { font-size: 14px; }
.form input[type="text"] {
  padding: 8px;
  border: 1px solid var(--border-input);
  border-radius: 4px;
  font-size: 14px;
}
.form > button {
  padding: 8px 16px;
  background: var(--color-primary);
  color: var(--text-inverse);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  align-self: flex-start;
}
.form > button:disabled { background: #ccc; }
.msg { font-size: 13px; }
.msg.success { color: var(--color-success); }
.msg.error { color: var(--color-danger); }

.store-select {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.form-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  min-width: 70px;
}
.radio-option {
  display: flex;
  flex-direction: column;
  padding: 8px 12px;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  min-width: 120px;
}
.radio-option.active {
  border-color: var(--color-primary);
  background: var(--bg-active);
}
.radio-option input { display: none; }
.radio-label { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.radio-desc { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }

.kb-select {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.kb-option { font-size: 13px; display: flex; align-items: center; gap: 3px; }
</style>