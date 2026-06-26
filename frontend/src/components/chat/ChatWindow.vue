<template>
  <div class="chat-window">
    <div class="messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-state">
        您好！我是客服助手，请描述您遇到的问题。
      </div>
      <MessageBubble
        v-for="(msg, i) in messages"
        :key="i"
        :role="msg.role"
        :content="msg.content"
        :sources="msg.sources"
        :result-data="msg.resultData"
        :retrieval-detail="msg.retrievalDetail"
        :loading="msg.role === 'assistant' && i === messages.length - 1 && loading"
        :feedback="msg.feedback || ''"
        @feedback="(rating) => handleFeedback(i, rating)"
        @show-graph="showMiniGraph"
      />
    </div>
    <div class="input-area">
      <textarea
        v-model="input"
        @keydown.enter.exact="send"
        placeholder="请输入您的问题..."
        :disabled="loading"
        rows="2"
      />
      <button @click="send" :disabled="loading || !input.trim()">
        {{ loading ? '思考中...' : '发送' }}
      </button>
    </div>
    <MiniGraphModal
      :visible="graphModalVisible"
      :graphData="graphModalData"
      @close="graphModalVisible = false"
    />
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'
import MessageBubble from './MessageBubble.vue'
import MiniGraphModal from './MiniGraphModal.vue'
import { sendChatMessage, submitFeedback, getChatHistory } from '../../api/index.js'

const props = defineProps({
  sessionKey: { type: String, default: '' },
  mode: { type: String, default: 'rag' },
})

const input = ref('')
const loading = ref(false)
const messages = ref([])
const messagesRef = ref(null)
const graphModalVisible = ref(false)
const graphModalData = ref({ nodes: [], edges: [] })

function loadHistory() {
  if (!props.sessionKey) return
  localStorage.setItem(props.mode === 'kg' ? 'kg_session_id' : 'chat_session_id', props.sessionKey)
  // 先清空，再加载历史（新会话无消息时显示空对话）
  messages.value = []
  getChatHistory(props.sessionKey, props.mode)
    .then(res => {
      if (res.data?.messages?.length) {
        messages.value = res.data.messages
        nextTick().then(() => {
          messagesRef.value?.scrollTo({ top: messagesRef.value.scrollHeight })
        })
      }
    })
    .catch(() => {
      // 静默失败
    })
}

onMounted(loadHistory)
watch(() => props.sessionKey, loadHistory)

function showMiniGraph(data) {
  graphModalData.value = data
  graphModalVisible.value = true
}

async function send() {
  if (!input.value.trim() || loading.value) return
  const query = input.value
  messages.value.push({ role: 'user', content: query })
  input.value = ''
  loading.value = true
  // 用户发送后立即滚动到底部
  nextTick().then(() => {
    messagesRef.value?.scrollTo({ top: messagesRef.value.scrollHeight, behavior: 'smooth' })
  })

  messages.value.push({ role: 'assistant', content: '', sources: [] })

  try {
    const response = await sendChatMessage(props.sessionKey, query, props.mode)
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6)
        if (data === '[DONE]') continue
        try {
          const parsed = JSON.parse(data)
          if (parsed.type === 'token') {
            messages.value[messages.value.length - 1].content += parsed.content
            // 流式生成时跟随滚动
            nextTick().then(() => {
              messagesRef.value?.scrollTo({ top: messagesRef.value.scrollHeight, behavior: 'smooth' })
            })
          } else if (parsed.type === 'sources') {
            messages.value[messages.value.length - 1].sources = parsed.sources
          } else if (parsed.type === 'retrieval_detail') {
            messages.value[messages.value.length - 1].retrievalDetail = parsed.detail
          } else if (parsed.type === 'result') {
            messages.value[messages.value.length - 1].resultData = parsed.content || ''
          }
        } catch { /* skip partial lines */ }
      }
    }
  } catch (err) {
    messages.value[messages.value.length - 1].content = '抱歉，发生了错误，请稍后重试。'
  } finally {
    loading.value = false
    await nextTick()
    messagesRef.value?.scrollTo({ top: messagesRef.value.scrollHeight, behavior: 'smooth' })
  }
}

async function handleFeedback(index, rating) {
  const msg = messages.value[index]
  if (!msg || msg.feedback) return
  msg.feedback = rating
  try {
    await submitFeedback({
      session_id: props.sessionKey,
      rating,
    })
  } catch {
    // silently fail
  }
}
</script>

<style scoped>
.chat-window { flex: 1; display: flex; flex-direction: column; }
.messages { flex: 1; overflow-y: auto; padding: 16px 20px; }
.empty-state { text-align: center; color: var(--text-tertiary); margin-top: 40px; font-size: 15px; }
.input-area {
  display: flex; gap: 8px; padding: 12px 20px;
  border-top: 1px solid var(--border-default);
}
.input-area textarea {
  flex: 1; resize: none; padding: 10px; border: 1px solid var(--border-input);
  border-radius: 8px; font-size: 14px; outline: none;
}
.input-area button {
  padding: 10px 20px; background: var(--color-primary); color: var(--text-inverse);
  border: none; border-radius: 8px; cursor: pointer; font-size: 14px;
}
.input-area button:disabled { background: var(--text-muted); cursor: not-allowed; }
</style>
