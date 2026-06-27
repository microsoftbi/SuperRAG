<template>
  <div class="uploader">
    <h2>上传文档</h2>
    <div class="form">
      <div class="upload-dropzone" :class="{ dragging: isDragging, selected: !!file }"
        @click="triggerFileSelect"
        @dragenter.prevent="onDragEnter"
        @dragover.prevent="onDragOver"
        @dragleave.prevent="onDragLeave"
        @drop.prevent="onDrop"
      >
        <input
          ref="fileInputRef"
          type="file"
          class="file-input-hidden"
          @change="onFileChange"
          accept=".pdf,.docx,.md,.html,.htm,.txt"
        />
        <div class="upload-icon">{{ file ? '📄' : '☁️' }}</div>
        <div class="upload-title">
          {{ file ? selectedFileName : '点击选择文件，或拖拽文件到这里' }}
        </div>
        <div class="upload-desc">
          支持 PDF / DOCX / Markdown / HTML / TXT
        </div>
        <button v-if="file" type="button" class="clear-file" @click.stop="clearFile">移除文件</button>
      </div>
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
      </div>
      <div class="kb-select" v-if="store !== 'graph'">
        <span class="form-label">知识库：</span>
        <label v-for="kb in kbs" :key="kb.id" class="kb-option">
          <input type="checkbox" :value="kb.id" v-model="selectedKbIds" />
          {{ kb.name }}
        </label>
      </div>

      <!-- 操作按钮区：根据存储目标显示不同按钮 -->
      <div class="action-buttons">
        <button v-if="store === 'vector'" @click="uploadFixed" :disabled="!file || uploading" class="btn-chunk">
          {{ uploading ? '上传中...' : '📐 固定分块上传' }}
        </button>
        <button v-if="store === 'vector'" @click="uploadLlm" :disabled="!file || uploading" class="btn-llm">
          {{ uploading ? '上传中...' : '🤖 LLM 分块上传' }}
        </button>
        <button v-else @click="uploadDirect" :disabled="!file || uploading" class="btn-primary">
          {{ uploading ? '上传中...' : '上传' }}
        </button>
      </div>

      <span v-if="message" :class="['msg', msgType]">{{ message }}</span>
    </div>

    <!-- 固定分块对话框 -->
    <DocumentChunkDialog
      :visible="chunkDialogVisible"
      :doc-id="previewDocId"
      :title="title"
      :file-name="selectedFileName"
      :text="previewText"
      :default-chunk-size="defaultChunkSize"
      :default-chunk-overlap="defaultChunkOverlap"
      @close="chunkDialogVisible = false"
      @saved="onChunksSaved"
    />

    <!-- LLM 分块对话框 -->
    <LlmChunkDialog
      :visible="llmDialogVisible"
      :file-name="selectedFileName"
      :doc-id="previewDocId"
      :text="previewText"
      @close="llmDialogVisible = false"
      @saved="onLlmChunksSaved"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { previewDocument, listKnowledgeBases } from '../../api/index.js'
import DocumentChunkDialog from './DocumentChunkDialog.vue'
import LlmChunkDialog from './LlmChunkDialog.vue'

const emit = defineEmits(['uploaded'])
const file = ref(null)
const title = ref('')
const store = ref('vector')
const kbs = ref([])
const selectedKbIds = ref([])
const uploading = ref(false)
const message = ref('')
const msgType = ref('')
const selectedFileName = ref('')
const fileInputRef = ref(null)
const isDragging = ref(false)

// 分块预览对话框
const chunkDialogVisible = ref(false)
const previewDocId = ref(0)
const previewText = ref('')
const defaultChunkSize = ref(500)
const defaultChunkOverlap = ref(50)

// LLM 分块对话框
const llmDialogVisible = ref(false)

function triggerFileSelect() {
  fileInputRef.value?.click()
}

function setFile(nextFile) {
  if (!nextFile) return
  const allowed = ['.pdf', '.docx', '.md', '.html', '.htm', '.txt']
  const lowerName = nextFile.name.toLowerCase()
  const ok = allowed.some(ext => lowerName.endsWith(ext))
  if (!ok) {
    message.value = '不支持的文件类型，请选择 PDF/DOCX/MD/HTML/TXT 文件'
    msgType.value = 'error'
    return
  }
  file.value = nextFile
  selectedFileName.value = nextFile.name
  message.value = ''
}

function onFileChange(e) {
  setFile(e.target.files[0] || null)
}

function clearFile() {
  file.value = null
  selectedFileName.value = ''
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function onDragEnter() {
  isDragging.value = true
}

function onDragOver() {
  isDragging.value = true
}

function onDragLeave(e) {
  if (!e.currentTarget.contains(e.relatedTarget)) {
    isDragging.value = false
  }
}

function onDrop(e) {
  isDragging.value = false
  const dropped = e.dataTransfer?.files?.[0]
  setFile(dropped)
}

async function doPreview() {
  if (!file.value) return
  uploading.value = true
  message.value = ''
  try {
    const res = await previewDocument(
      file.value, title.value, 'default', selectedKbIds.value, store.value,
    )
    const data = res.data
    previewDocId.value = data.doc_id
    previewText.value = data.text
    defaultChunkSize.value = 500
    defaultChunkOverlap.value = 50
    file.value = null
    selectedFileName.value = data.file_name || ''
    return true
  } catch (err) {
    message.value = err.response?.data?.detail || '上传失败'
    msgType.value = 'error'
    return false
  } finally {
    uploading.value = false
  }
}

async function uploadFixed() {
  const ok = await doPreview()
  if (ok) chunkDialogVisible.value = true
}

async function uploadLlm() {
  const ok = await doPreview()
  if (ok) llmDialogVisible.value = true
}

async function uploadDirect() {
  const { uploadDocument } = await import('../../api/index.js')
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

function onChunksSaved() {
  chunkDialogVisible.value = false
  message.value = '分块入库成功！'
  msgType.value = 'success'
  title.value = ''
  store.value = 'vector'
  selectedKbIds.value = []
  clearFile()
  emit('uploaded')
}

function onLlmChunksSaved() {
  llmDialogVisible.value = false
  message.value = 'LLM 分块入库成功！'
  msgType.value = 'success'
  title.value = ''
  store.value = 'vector'
  selectedKbIds.value = []
  clearFile()
  emit('uploaded')
}

onMounted(async () => {
  try {
    const res = await listKnowledgeBases()
    kbs.value = res.data
    const { getRuntimeConfig } = await import('../../api/index.js')
    try {
      const cfgRes = await getRuntimeConfig()
      if (cfgRes.data?.chunk_size) defaultChunkSize.value = cfgRes.data.chunk_size
      if (cfgRes.data?.chunk_overlap) defaultChunkOverlap.value = cfgRes.data.chunk_overlap
    } catch { /* ignore */ }
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
.upload-dropzone {
  border: 2px dashed var(--border-input);
  border-radius: 10px;
  background: var(--bg-surface);
  padding: 24px 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.18s ease;
  min-height: 130px;
}
.upload-dropzone:hover,
.upload-dropzone.dragging {
  border-color: var(--color-primary);
  background: var(--bg-active);
}
.upload-dropzone.selected {
  border-color: var(--color-success);
  background: var(--color-success-light);
}
.file-input-hidden { display: none; }
.upload-icon { font-size: 34px; line-height: 1; }
.upload-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  word-break: break-all;
  text-align: center;
}
.upload-desc { font-size: 12px; color: var(--text-tertiary); }
.clear-file {
  margin-top: 6px;
  padding: 4px 10px;
  border: 1px solid var(--border-input);
  background: var(--bg-card);
  color: var(--text-secondary);
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.clear-file:hover { background: var(--bg-hover); }
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

.action-buttons { display: flex; gap: 10px; flex-wrap: wrap; }
.btn-primary, .btn-chunk, .btn-llm {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  align-self: flex-start;
}
.btn-primary { background: var(--color-primary); color: var(--text-inverse); }
.btn-chunk { background: var(--color-success); color: var(--text-inverse); }
.btn-llm { background: var(--color-primary); color: var(--text-inverse); }
.btn-primary:disabled, .btn-chunk:disabled, .btn-llm:disabled { background: var(--text-muted); cursor: not-allowed; }
</style>