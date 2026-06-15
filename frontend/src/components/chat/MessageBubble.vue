<template>
  <div :class="['message', role]">
    <div class="avatar">{{ role === 'user' ? 'U' : 'A' }}</div>
    <div class="bubble">
      <div class="content" v-html="renderedContent" />
      <SourceReference v-if="sources && sources.length > 0" :sources="sources" />
      <div v-if="role === 'assistant' && content && !loading" class="feedback-actions">
        <button
          :class="['fb-btn', { active: feedback === 'like' }]"
          @click="$emit('feedback', 'like')"
          title="有帮助"
        >👍</button>
        <button
          :class="['fb-btn', { active: feedback === 'dislike' }]"
          @click="$emit('feedback', 'dislike')"
          title="没帮助"
        >👎</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SourceReference from './SourceReference.vue'

const props = defineProps({
  role: { type: String, required: true },
  content: { type: String, default: '' },
  sources: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  feedback: { type: String, default: '' },
})

defineEmits(['feedback'])

const renderedContent = computed(() => {
  return props.content
    .replace(/\n/g, '<br>')
    .replace(/\[来源(\d+)\]/g, '<sup class="source-ref">[$1]</sup>')
})
</script>

<style scoped>
.message { display: flex; gap: 10px; margin-bottom: 16px; }
.message.user { flex-direction: row-reverse; }
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: bold; flex-shrink: 0;
}
.user .avatar { background: #1976d2; color: #fff; }
.assistant .avatar { background: #e0e0e0; color: #333; }
.bubble { max-width: 75%; }
.user .bubble {
  background: #1976d2; color: #fff; padding: 10px 14px;
  border-radius: 12px 4px 12px 12px; font-size: 14px;
}
.assistant .bubble {
  background: #f5f5f5; padding: 10px 14px;
  border-radius: 4px 12px 12px 12px; font-size: 14px; color: #333;
}
.content { line-height: 1.6; }
.source-ref { font-size: 11px; color: #1976d2; cursor: pointer; }
.feedback-actions { margin-top: 8px; padding-top: 8px; border-top: 1px solid #e0e0e0; display: flex; gap: 4px; }
.fb-btn { background: none; border: 1px solid #ddd; border-radius: 4px; padding: 2px 8px; cursor: pointer; font-size: 14px; }
.fb-btn:hover { background: #f0f0f0; }
.fb-btn.active { background: #e3f2fd; border-color: #1976d2; }
</style>
