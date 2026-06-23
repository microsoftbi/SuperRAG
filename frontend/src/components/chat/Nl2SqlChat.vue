<template>
  <div class="chat-window">
    <div class="messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-state">
        您好！请输入业务数据查询问题。
      </div>
      <MessageBubble
        v-for="(msg, i) in messages"
        :key="i"
        :role="msg.role"
        :content="msg.content"
        :result-data="msg.resultData"
        :loading="msg.role === 'assistant' && i === messages.length - 1 && loading"
        :feedback="msg.feedback || ''"
        @feedback="(rating) => handleFeedback(i, rating)"
      />
    </div>
    <div class="input-area">
      <textarea
        v-model="input"
        @keydown.enter.exact="send"
        placeholder="请输入业务数据查询问题..."
        :disabled="loading"
        rows="2"
      />
      <button @click="send" :disabled="loading || !input.trim()">
        {{ loading ? '查询中...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'
import MessageBubble from './MessageBubble.vue'
import { sendChatMessage, submitFeedback, getChatHistory } from '../../api/index.js'

const props = defineProps({
  sessionKey: { type: String, default: '' },
})

const input = ref('')
const loading = ref(false)
const messages = ref([])
const messagesRef = ref(null)

function loadHistory() {
  if (!props.sessionKey) return
  localStorage.setItem('nl2sql_session_id', props.sessionKey)
  messages.value = []
  getChatHistory(props.sessionKey, 'nl2sql')
    .then(res => {
      if (res.data?.messages?.length) {
        messages.value = res.data.messages
        nextTick().then(() => {
          messagesRef.value?.scrollTo({ top: messagesRef.value.scrollHeight })
        })
      }
    })
    .catch(() => {})
}

onMounted(loadHistory)
watch(() => props.sessionKey, loadHistory)

async function send() {
  if (!input.value.trim() || loading.value) return
  const query = input.value
  messages.value.push({ role: 'user', content: query })
  input.value = ''
  loading.value = true
  messages.value.push({ role: 'assistant', content: '', sources: [] })

  try {
    const response = await sendChatMessage(props.sessionKey, query, 'nl2sql')
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
          } else if (parsed.type === 'sources') {
            messages.value[messages.value.length - 1].sources = parsed.sources
            // 提取 sources 中的 resultData
            for (const s of (parsed.sources || [])) {
              if (s.resultData) {
                messages.value[messages.value.length - 1].resultData = s.resultData
              }
            }
          } else if (parsed.type === 'result') {
            messages.value[messages.value.length - 1].resultData = parsed.content || ''
          }
        } catch { /* skip */ }
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
    await submitFeedback({ session_id: props.sessionKey, rating })
  } catch { /* ignore */ }
}
</script>

<style scoped>
.chat-window { flex: 1; display: flex; flex-direction: column; }
.messages { flex: 1; overflow-y: auto; padding: 16px 20px; }
.empty-state { text-align: center; color: #999; margin-top: 40px; font-size: 15px; }
.input-area {
  display: flex; gap: 8px; padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
}
.input-area textarea {
  flex: 1; resize: none; padding: 10px; border: 1px solid #d0d0d0;
  border-radius: 8px; font-size: 14px; outline: none;
}
.input-area button {
  padding: 10px 20px; background: #1976d2; color: #fff;
  border: none; border-radius: 8px; cursor: pointer; font-size: 14px;
}
.input-area button:disabled { background: #ccc; cursor: not-allowed; }
</style>