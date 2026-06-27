<template>
  <Teleport to="body">
    <div v-if="visible" class="dialog-overlay" @click.self="handleClose">
      <div class="dialog">
        <!-- Header -->
        <div class="dialog-header">
          <div class="header-left">
            <span class="header-icon">🤖</span>
            <span class="header-title">LLM 智能切分</span>
            <span class="header-file">{{ fileName }}</span>
          </div>
          <button class="close-btn" @click="handleClose">✕</button>
        </div>

        <!-- 提示区（替代参数区） -->
        <div class="info-row">
          <span class="info-icon">💡</span>
          <span class="info-text">将使用 AI 大模型自动分析文档内容并进行语义切分，无需设置参数</span>
        </div>

        <!-- 左右对比区 -->
        <div class="split-pane">
          <!-- 左侧：原文 -->
          <div class="pane-original">
            <div class="pane-header">原文 <span class="pane-hint">({{ text.length }} 字符)</span></div>
            <div class="pane-content">
              <pre>{{ text }}</pre>
            </div>
          </div>
          <!-- 右侧：切分结果 -->
          <div class="pane-chunks">
            <div class="pane-header">
              切分结果
              <span v-if="chunks.length" class="pane-hint">(共 {{ chunks.length }} 块)</span>
            </div>
            <div class="pane-content chunks-list">
              <div v-if="chunks.length === 0 && !chunking && !committed" class="chunks-placeholder">
                点击「LLM 切分」由大模型自动分块
              </div>
              <div v-if="chunkError" class="chunk-error">❌ {{ chunkError }}</div>
              <div
                v-for="(chunk, i) in chunks"
                :key="i"
                class="chunk-card"
              >
                <div class="chunk-header">
                  <span class="chunk-num">#{{ i + 1 }}</span>
                  <span class="chunk-chars">{{ chunk.length }} 字符</span>
                </div>
                <div class="chunk-text" v-text="chunk"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部操作栏 -->
        <div class="footer-bar">
          <span class="footer-hint" v-if="!committed">
            {{ chunks.length > 0 ? `确认分块无误后，点击下方按钮入库` : '' }}
          </span>
          <span class="footer-success" v-if="committed">✅ 已入库 {{ chunks.length }} 个分块</span>
          <div class="footer-actions">
            <button class="btn-cancel" @click="handleClose">取消</button>
            <button class="btn-chunk" :disabled="chunking" @click="doChunk">
              {{ chunking ? '切分中...' : '🤖 LLM 切分' }}
            </button>
            <button
              class="btn-commit"
              :disabled="chunks.length === 0 || committing || committed"
              @click="doCommit"
            >
              {{ committing ? '入库中...' : committed ? '✅ 已入库' : '📥 切分入库' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { createLlmChunks, commitLlmChunks } from '../../api/index.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
  docId: { type: Number, default: 0 },
  fileName: { type: String, default: '' },
  text: { type: String, default: '' },
})

const emit = defineEmits(['close', 'saved'])

const chunks = ref([])
const chunking = ref(false)
const chunkError = ref('')
const committing = ref(false)
const committed = ref(false)

function doChunk() {
  if (!props.docId) return
  chunkError.value = ''
  chunking.value = true
  createLlmChunks(props.docId)
    .then(res => {
      chunks.value = res.data?.chunks || []
      chunking.value = false
    })
    .catch(e => {
      chunkError.value = 'LLM 切分失败: ' + (e.response?.data?.detail || e.message)
      chunks.value = []
      chunking.value = false
    })
}

async function doCommit() {
  if (!props.docId || chunks.value.length === 0) return
  committing.value = true
  try {
    await commitLlmChunks(props.docId)
    committed.value = true
    // 入库成功后自动关闭
    emit('saved')
    emit('close')
  } catch (e) {
    chunkError.value = '入库失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    committing.value = false
  }
}

function handleClose() {
  if (committing.value) return
  if (committed.value) {
    emit('saved')
  }
  emit('close')
}

// 重置状态
watch(() => props.visible, (val) => {
  if (val) {
    chunks.value = []
    chunkError.value = ''
    chunking.value = false
    committing.value = false
    committed.value = false
  }
})
</script>

<style scoped>
.dialog-overlay {
  position: fixed; inset: 0; background: var(--overlay);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.dialog {
  background: var(--bg-card); border-radius: 10px;
  width: 95vw; max-width: 1400px; height: 90vh;
  display: flex; flex-direction: column;
  box-shadow: var(--shadow-lg);
}

/* ── Header ── */
.dialog-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 18px; border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 8px; }
.header-icon { font-size: 18px; }
.header-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.header-file { font-size: 12px; color: var(--text-tertiary); background: var(--bg-surface); padding: 2px 8px; border-radius: 4px; }
.close-btn {
  background: none; border: none; font-size: 18px; cursor: pointer;
  color: var(--text-tertiary); padding: 4px 8px; border-radius: 4px;
}
.close-btn:hover { background: var(--bg-hover); color: var(--text-primary); }

/* ── 提示区 ── */
.info-row {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; background: var(--bg-surface);
  border-radius: 6px; margin: 12px 12px 10px; flex-shrink: 0;
}
.info-icon { font-size: 16px; }
.info-text { font-size: 13px; color: var(--text-secondary); }

/* ── 左右对比区 ── */
.split-pane {
  flex: 1; display: flex; gap: 10px; margin: 0 12px; min-height: 0;
}
.pane-original, .pane-chunks {
  flex: 1; display: flex; flex-direction: column;
  border: 1px solid var(--border-default); border-radius: 6px;
  overflow: hidden;
}
.pane-header {
  padding: 8px 12px; font-size: 12px; font-weight: 600;
  color: var(--text-secondary); background: var(--bg-surface);
  border-bottom: 1px solid var(--border-light); flex-shrink: 0;
}
.pane-hint { font-weight: 400; color: var(--text-tertiary); font-size: 11px; }
.pane-content {
  flex: 1; overflow-y: auto; padding: 10px;
  font-size: 12px; line-height: 1.7;
}
.pane-content pre {
  white-space: pre-wrap; word-break: break-word;
  font-family: inherit; margin: 0; color: var(--text-primary);
}

/* ── 切分结果 ── */
.chunks-list { display: block; }
.chunks-placeholder, .chunk-error {
  text-align: center; padding: 40px 0; color: var(--text-tertiary); font-size: 13px;
}
.chunk-error { color: var(--color-danger); }
.chunk-card {
  border: 1px solid var(--border-light); border-radius: 4px;
  background: var(--bg-surface); overflow: hidden;
  margin-bottom: 6px;
}
.chunk-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 8px; background: var(--color-primary-light);
  font-size: 11px;
}
.chunk-num { font-weight: 600; color: var(--color-primary); }
.chunk-chars { color: var(--text-tertiary); }
.chunk-text {
  padding: 12px; font-size: 13px; line-height: 1.7;
  color: #333; background: #fafafa;
  white-space: pre-wrap; word-break: break-word;
  max-height: 240px; overflow-y: auto;
}

/* ── 底部 ── */
.footer-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px; border-top: 1px solid var(--border-light);
  flex-shrink: 0;
}
.footer-hint { font-size: 12px; color: var(--text-tertiary); flex: 1; }
.footer-success { font-size: 13px; color: var(--color-success); font-weight: 500; flex: 1; }
.footer-actions { display: flex; gap: 8px; }
.btn-cancel, .btn-chunk, .btn-commit {
  padding: 8px 20px; font-size: 13px; border-radius: 4px; cursor: pointer; border: 1px solid;
}
.btn-cancel { background: var(--bg-card); color: var(--text-secondary); border-color: var(--border-input); }
.btn-cancel:hover { background: var(--bg-hover); }
.btn-chunk { background: var(--color-primary); color: var(--text-inverse); border-color: var(--color-primary); }
.btn-chunk:disabled { background: var(--text-muted); border-color: var(--text-muted); cursor: not-allowed; }
.btn-chunk:hover:not(:disabled) { opacity: 0.9; }
.btn-commit { background: var(--color-success); color: var(--text-inverse); border-color: var(--color-success); }
.btn-commit:disabled { background: var(--text-muted); border-color: var(--text-muted); cursor: not-allowed; }
.btn-commit:hover:not(:disabled) { opacity: 0.9; }
</style>
