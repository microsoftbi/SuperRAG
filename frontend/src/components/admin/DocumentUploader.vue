<template>
  <div class="uploader">
    <h2>上传文档</h2>
    <div class="form">
      <input type="file" @change="onFileChange" accept=".pdf,.docx,.md,.html,.htm,.txt" />
      <input v-model="title" placeholder="文档标题（可选）" />
      <div class="kb-select">
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
    await uploadDocument(file.value, title.value, 'default', selectedKbIds.value)
    message.value = '上传成功！'
    msgType.value = 'success'
    file.value = null
    title.value = ''
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
.uploader { padding: 16px; border: 1px solid #e0e0e0; border-radius: 8px; }
.uploader h2 { font-size: 16px; margin-bottom: 12px; }
.form { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.form input[type="file"] { font-size: 14px; }
.form input[type="text"] { padding: 8px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 14px; }
.form button { padding: 8px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.form button:disabled { background: #ccc; }
.msg { font-size: 13px; }
.msg.success { color: #2e7d32; }
.msg.error { color: #c62828; }
.kb-select { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; width: 100%; padding: 4px 0; }
.form-label { font-size: 13px; color: #555; font-weight: 500; }
.kb-option { font-size: 13px; display: flex; align-items: center; gap: 3px; }
</style>

<style scoped>
.uploader { padding: 16px; border: 1px solid #e0e0e0; border-radius: 8px; }
.uploader h2 { font-size: 16px; margin-bottom: 12px; }
.form { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.form input[type="file"] { font-size: 14px; }
.form input[type="text"] { padding: 8px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 14px; }
.form button { padding: 8px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.form button:disabled { background: #ccc; }
.msg { font-size: 13px; }
.msg.success { color: #2e7d32; }
.msg.error { color: #c62828; }
</style>
