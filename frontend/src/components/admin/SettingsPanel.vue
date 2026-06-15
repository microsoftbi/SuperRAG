<template>
  <div class="settings-panel">
    <h2>检索参数配置</h2>
    <div class="settings-form">
      <div class="field">
        <label>检索策略</label>
        <select v-model.number="config.enable_hybrid_retrieval">
          <option :value="true">混合检索（向量 + BM25）</option>
          <option :value="false">纯向量检索</option>
        </select>
      </div>
      <div class="field">
        <label>Query 重写</label>
        <select v-model.number="config.enable_query_rewriting">
          <option :value="true">开启</option>
          <option :value="false">关闭</option>
        </select>
      </div>
      <div class="field">
        <label>重排序</label>
        <select v-model.number="config.enable_reranker">
          <option :value="true">开启</option>
          <option :value="false">关闭</option>
        </select>
      </div>
      <div class="field">
        <label>向量检索数量 (Top-K)</label>
        <input type="number" v-model.number="config.retriever_top_k" min="3" max="50" />
      </div>
      <div class="field">
        <label>BM25 检索数量</label>
        <input type="number" v-model.number="config.bm25_top_k" min="3" max="50" />
      </div>
      <div class="field">
        <label>重排序后保留数量</label>
        <input type="number" v-model.number="config.reranker_top_k" min="1" max="20" />
      </div>
      <div class="field">
        <label>LLM 温度 (Temperature)</label>
        <input type="number" v-model.number="config.llm_temperature" min="0" max="2" step="0.1" />
      </div>
      <div class="field">
        <label>Chunk 大小</label>
        <input type="number" v-model.number="config.chunk_size" min="100" max="2000" step="100" />
      </div>
      <button @click="save" :disabled="saving" class="save-btn">
        {{ saving ? '保存中...' : '保存配置' }}
      </button>
      <span v-if="message" :class="['msg', msgType]">{{ message }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getRuntimeConfig, updateRuntimeConfig } from '../../api/index.js'

const config = ref({})
const saving = ref(false)
const message = ref('')
const msgType = ref('')

async function load() {
  const res = await getRuntimeConfig()
  config.value = { ...res.data }
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    await updateRuntimeConfig(config.value)
    message.value = '配置已保存'
    msgType.value = 'success'
  } catch {
    message.value = '保存失败'
    msgType.value = 'error'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.settings-panel { max-width: 500px; }
.settings-panel h2 { font-size: 16px; margin-bottom: 16px; }
.settings-form { display: flex; flex-direction: column; gap: 14px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: 13px; color: #555; font-weight: 500; }
.field select, .field input {
  padding: 8px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 14px;
}
.save-btn {
  padding: 10px 20px; background: #1976d2; color: #fff; border: none;
  border-radius: 4px; cursor: pointer; font-size: 14px; align-self: flex-start;
}
.save-btn:disabled { background: #ccc; }
.msg { font-size: 13px; }
.msg.success { color: #2e7d32; }
.msg.error { color: #c62828; }
</style>
