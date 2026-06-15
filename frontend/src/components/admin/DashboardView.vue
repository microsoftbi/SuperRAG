<template>
  <div class="dashboard">
    <h2>系统概览</h2>

    <!-- Alert Banner -->
    <div v-if="alerts.length > 0" class="alert-banner" :class="alertStatus">
      <div v-for="a in alerts" :key="a.type" class="alert-item">
        <span class="alert-level">{{ a.level === 'critical' ? '🚨' : '⚠️' }}</span>
        {{ a.message }}
      </div>
    </div>

    <!-- Overview Cards -->
    <div v-if="overview" class="cards">
      <div class="card">
        <div class="card-value">{{ overview.total_conversations }}</div>
        <div class="card-label">总对话数</div>
      </div>
      <div class="card accent">
        <div class="card-value">{{ overview.today_conversations }}</div>
        <div class="card-label">今日对话</div>
      </div>
      <div class="card">
        <div class="card-value">{{ overview.avg_latency_ms }}ms</div>
        <div class="card-label">平均延迟</div>
      </div>
      <div class="card">
        <div class="card-value">{{ overview.p95_latency_ms }}ms</div>
        <div class="card-label">P95 延迟</div>
      </div>
      <div class="card" :class="overview.empty_result_rate > 0.3 ? 'danger' : ''">
        <div class="card-value">{{ (overview.empty_result_rate * 100).toFixed(1) }}%</div>
        <div class="card-label">空结果率</div>
      </div>
      <div class="card">
        <div class="card-value">{{ overview.total_tokens.toLocaleString() }}</div>
        <div class="card-label">总 Token 数</div>
      </div>
      <div class="card" :class="overview.satisfaction < 0.5 ? 'danger' : 'success'">
        <div class="card-value">{{ (overview.satisfaction * 100).toFixed(1) }}%</div>
        <div class="card-label">满意度</div>
      </div>
      <div class="card">
        <div class="card-value">{{ overview.total_feedback }}</div>
        <div class="card-label">总反馈数</div>
      </div>
    </div>

    <!-- Daily Trends -->
    <h2>趋势（近 {{ days }} 天）</h2>
    <div v-if="trends.length > 0" class="trend-section">
      <div class="trend-chart">
        <h3>每日调用量</h3>
        <div class="bar-chart">
          <div v-for="t in trends" :key="t.date" class="bar-group" :title="t.date">
            <div class="bar" :style="{ height: barHeight(t.calls, maxCalls) + '%' }">
              <span v-if="t.calls > 0" class="bar-value">{{ t.calls }}</span>
            </div>
            <div class="bar-label">{{ t.date.slice(5) }}</div>
          </div>
        </div>
      </div>

      <div class="trend-chart">
        <h3>平均延迟 (ms)</h3>
        <div class="bar-chart">
          <div v-for="t in trends" :key="t.date" class="bar-group" :title="t.date">
            <div class="bar latency" :style="{ height: barHeight(t.avg_latency_ms, maxLatency) + '%' }">
              <span v-if="t.avg_latency_ms > 0" class="bar-value">{{ t.avg_latency_ms }}</span>
            </div>
            <div class="bar-label">{{ t.date.slice(5) }}</div>
          </div>
        </div>
      </div>

      <div class="trend-chart">
        <h3>满意度</h3>
        <div class="bar-chart">
          <div v-for="t in trends" :key="t.date" class="bar-group" :title="t.date">
            <div
              v-if="t.satisfaction !== null"
              class="bar satisfaction"
              :style="{ height: barHeight(t.satisfaction * 100, 100) + '%' }"
            >
              <span class="bar-value">{{ (t.satisfaction * 100).toFixed(0) }}%</span>
            </div>
            <div v-else class="bar no-data" style="height: 10%">
              <span class="bar-value">-</span>
            </div>
            <div class="bar-label">{{ t.date.slice(5) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getStatsOverview, getStatsTrends, getAlerts } from '../../api/index.js'

const overview = ref(null)
const trends = ref([])
const alerts = ref([])
const alertStatus = ref('ok')
const days = ref(7)

const maxCalls = computed(() => Math.max(...trends.value.map(t => t.calls), 1))
const maxLatency = computed(() => Math.max(...trends.value.map(t => t.avg_latency_ms), 1))

function barHeight(value, max) {
  return Math.max((value / max) * 100, 5)
}

async function load() {
  const [overviewRes, trendsRes, alertsRes] = await Promise.all([
    getStatsOverview(),
    getStatsTrends(days.value),
    getAlerts(),
  ])
  overview.value = overviewRes.data
  trends.value = trendsRes.data.trends
  alerts.value = alertsRes.data.alerts
  alertStatus.value = alertsRes.data.status
}

onMounted(load)
</script>

<style scoped>
.dashboard { }
.dashboard h2 { font-size: 16px; margin-bottom: 16px; margin-top: 24px; }
.dashboard h2:first-child { margin-top: 0; }

/* Alerts */
.alert-banner {
  padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;
}
.alert-banner.warning { background: #fff3e0; border: 1px solid #ffcc02; }
.alert-banner.critical { background: #ffebee; border: 1px solid #ef5350; }
.alert-item { font-size: 14px; margin-bottom: 4px; }
.alert-level { margin-right: 6px; }

/* Cards */
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 8px; }
.card {
  padding: 16px; border: 1px solid #e0e0e0; border-radius: 8px; text-align: center;
}
.card-value { font-size: 22px; font-weight: bold; color: #333; }
.card-label { font-size: 12px; color: #888; margin-top: 4px; }
.card.accent .card-value { color: #1976d2; }
.card.success .card-value { color: #2e7d32; }
.card.danger .card-value { color: #c62828; }

/* Trends */
.trend-section { display: flex; flex-direction: column; gap: 24px; }
.trend-chart { }
.trend-chart h3 { font-size: 14px; color: #555; margin-bottom: 8px; }
.bar-chart { display: flex; gap: 2px; align-items: flex-end; height: 120px; }
.bar-group {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  height: 100%; justify-content: flex-end;
}
.bar {
  width: 100%; background: #1976d2; border-radius: 3px 3px 0 0;
  min-height: 4px; position: relative; transition: height 0.3s;
}
.bar.latency { background: #7b1fa2; }
.bar.satisfaction { background: #2e7d32; }
.bar.no-data { background: #e0e0e0; }
.bar-value { position: absolute; top: -16px; font-size: 10px; color: #555; width: 100%; text-align: center; }
.bar-label { font-size: 9px; color: #999; margin-top: 4px; white-space: nowrap; }
</style>
