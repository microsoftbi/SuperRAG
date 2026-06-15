<template>
  <div class="feedback-panel">
    <h2>用户反馈</h2>
    <div v-if="stats" class="stats-cards">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">总反馈</div>
      </div>
      <div class="stat-card like">
        <div class="stat-value">{{ stats.likes }}</div>
        <div class="stat-label">点赞</div>
      </div>
      <div class="stat-card dislike">
        <div class="stat-value">{{ stats.dislikes }}</div>
        <div class="stat-label">点踩</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ (stats.like_ratio * 100).toFixed(1) }}%</div>
        <div class="stat-label">满意度</div>
      </div>
    </div>
    <div v-if="items.length === 0" class="empty">暂无反馈</div>
    <div v-for="item in items" :key="item.id" class="feedback-item">
      <div class="fb-meta">
        <span :class="['fb-rating', item.rating]">
          {{ item.rating === 'like' ? '👍' : '👎' }}
        </span>
        <span class="fb-time">{{ new Date(item.created_at).toLocaleString() }}</span>
        <span class="fb-session">{{ item.session_id.slice(0, 16) }}...</span>
      </div>
      <div v-if="item.suggestion" class="fb-suggestion">{{ item.suggestion }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getFeedbackStats, listFeedback } from '../../api/index.js'

const stats = ref(null)
const items = ref([])

async function load() {
  const [statsRes, listRes] = await Promise.all([
    getFeedbackStats(),
    listFeedback(),
  ])
  stats.value = statsRes.data
  items.value = listRes.data
}

onMounted(load)
</script>

<style scoped>
.feedback-panel { }
.feedback-panel h2 { font-size: 16px; margin-bottom: 16px; }
.stats-cards { display: flex; gap: 12px; margin-bottom: 20px; }
.stat-card {
  flex: 1; padding: 16px; border: 1px solid #e0e0e0; border-radius: 8px; text-align: center;
}
.stat-value { font-size: 24px; font-weight: bold; color: #333; }
.stat-label { font-size: 12px; color: #888; margin-top: 4px; }
.stat-card.like .stat-value { color: #2e7d32; }
.stat-card.dislike .stat-value { color: #c62828; }
.empty { text-align: center; color: #999; padding: 40px; }
.feedback-item {
  padding: 12px; border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 8px;
}
.fb-meta { display: flex; gap: 12px; align-items: center; margin-bottom: 4px; }
.fb-rating { font-size: 18px; }
.fb-time { font-size: 12px; color: #888; }
.fb-session { font-size: 12px; color: #aaa; font-family: monospace; }
.fb-suggestion { font-size: 13px; color: #555; padding: 8px; background: #f9f9f9; border-radius: 4px; margin-top: 4px; }
</style>
