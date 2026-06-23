<template>
  <div :class="['message', role]">
    <div class="avatar">{{ role === 'user' ? 'U' : 'A' }}</div>
    <div class="bubble">
      <div class="content" v-html="renderedContent" />
      <div v-if="resultTable" class="result-table">
        <div class="result-table-toolbar">
          <span class="result-count">共 {{ resultTable.totalRows }} 行</span>
          <button class="copy-csv-btn" @click="copyCsv" title="复制为CSV">📋 复制CSV</button>
        </div>
        <div class="result-table-scroll">
          <table>
            <thead>
              <tr>
                <th class="row-num">#</th>
                <th v-for="col in resultTable.columns" :key="col.name" :class="col.type">{{ col.name }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in resultTable.rows" :key="ri">
                <td class="row-num">{{ ri + 1 }}</td>
                <td v-for="col in resultTable.columns" :key="col.name" :class="col.type" :title="String(row[col.name] ?? '')">
                  {{ formatCellValue(row[col.name]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <SourceReference v-if="sources && sources.length > 0" :sources="sources" @show-graph="$emit('show-graph', $event)" />
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
import { ref, computed } from 'vue'
import SourceReference from './SourceReference.vue'

const props = defineProps({
  role: { type: String, required: true },
  content: { type: String, default: '' },
  sources: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  feedback: { type: String, default: '' },
  resultData: { type: String, default: '' },
})

const emit = defineEmits(['feedback', 'show-graph'])

const renderedContent = computed(() => {
  return props.content
    .replace(/\n/g, '<br>')
    .replace(/\[来源(\d+)\]/g, '<sup class="source-ref">[$1]</sup>')
})

const resultTable = computed(() => {
  if (!props.resultData) return null
  try {
    const parsed = JSON.parse(props.resultData)
    let data, meta
    if (parsed && parsed._meta) {
      // 新格式：{ data: [...], _meta: { columns, total_rows } }
      data = parsed.data
      meta = parsed._meta
    } else if (Array.isArray(parsed)) {
      // 兼容旧格式：纯数组
      data = parsed
      meta = {
        columns: data.length ? Object.keys(data[0]).map(n => ({ name: n, type: 'text' })) : [],
        total_rows: data.length,
      }
    } else {
      return null
    }
    if (!data || !data.length) return null
    return { columns: meta.columns, rows: data, totalRows: meta.total_rows || data.length }
  } catch { return null }
})

function formatCellValue(val) {
  if (val === null || val === undefined || val === '') return '—'
  const str = String(val)
  // 数字加千分位
  if (/^-?\d+(\.\d+)?$/.test(str)) {
    const parts = str.split('.')
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    return parts.join('.')
  }
  return str
}

function copyCsv() {
  if (!resultTable.value) return
  const cols = resultTable.value.columns
  const rows = resultTable.value.rows
  const csv = [
    cols.map(c => `"${c.name}"`).join(','),
    ...rows.map(r =>
      cols.map(c => `"${String(r[c.name] || '').replace(/"/g, '""')}"`).join(',')
    ),
  ].join('\n')
  navigator.clipboard.writeText(csv).catch(() => {})
}
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
.result-table { margin-top: 12px; }
.result-table-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 6px; padding: 0 2px;
}
.result-count { font-size: 12px; color: #999; }
.copy-csv-btn {
  font-size: 11px; color: #1976d2; background: none;
  border: 1px solid #1976d2; border-radius: 4px; padding: 2px 8px;
  cursor: pointer; line-height: 1.4;
}
.copy-csv-btn:hover { background: #e3f2fd; }
.result-table-scroll {
  max-height: 420px; overflow: auto;
  border: 1px solid #dde0e4; border-radius: 8px;
}
.result-table table {
  width: 100%; border-collapse: collapse; font-size: 13px;
  table-layout: auto; white-space: nowrap;
}
.result-table thead { position: sticky; top: 0; z-index: 1; }
.result-table th {
  background: #eef1f5; font-weight: 600; color: #333;
  padding: 10px 10px; border-bottom: 2px solid #d0d4db;
  font-size: 12px; letter-spacing: 0.3px;
}
.result-table th.row-num,
.result-table td.row-num {
  width: 32px; min-width: 32px; max-width: 32px;
  text-align: center; color: #aaa; font-size: 11px;
  background: #f6f8fa; padding: 8px 2px;
}
.result-table td {
  padding: 8px 10px; border-bottom: 1px solid #eef0f3;
  color: #444; max-width: 30vw;
  overflow: hidden; text-overflow: ellipsis;
}
.result-table th.numeric,
.result-table td.numeric {
  text-align: right; font-variant-numeric: tabular-nums;
}
.result-table td.numeric { font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace; font-size: 12px; }
.result-table tbody tr:nth-child(even) td { background: #f8f9fb; }
.result-table tbody tr:hover td { background: #e3f0fa; }
.result-table tbody tr:last-child td { border-bottom: none; }
</style>
