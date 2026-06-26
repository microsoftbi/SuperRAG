<template>
  <div class="config-panel">
    <div class="panel-header">
      <span>生成图表</span>
      <button class="close-btn" @click="$emit('close')" title="关闭">✕</button>
    </div>
    <div class="panel-body">
      <div class="form-row">
        <label>图表类型</label>
        <div class="type-grid">
          <button
            v-for="t in types"
            :key="t.value"
            :class="['type-btn', { active: chartType === t.value }]"
            @click="chartType = t.value"
          >
            <span class="type-icon">{{ t.icon }}</span>
            <span>{{ t.label }}</span>
          </button>
        </div>
      </div>
      <div class="form-row">
        <label>X 轴(分类)</label>
        <select v-model="xField">
          <option v-for="c in columns" :key="c.name" :value="c.name">{{ c.name }}</option>
        </select>
      </div>
      <div class="form-row">
        <label>Y 轴(数值){{ chartType === 'pie' ? ' · 单选' : ' · 可多选' }}</label>
        <div class="y-list">
          <label v-for="c in numericColumns" :key="c.name" class="y-item">
            <input
              :type="chartType === 'pie' ? 'radio' : 'checkbox'"
              :value="c.name"
              :checked="yFields.includes(c.name)"
              @change="toggleY(c.name)"
            />
            <span>{{ c.name }}</span>
          </label>
          <div v-if="!numericColumns.length" class="empty-hint">未检测到数值列</div>
        </div>
      </div>
      <div class="form-row">
        <label>标题</label>
        <input v-model="title" type="text" placeholder="可选" />
      </div>
    </div>
    <div class="panel-footer">
      <button class="btn-secondary" @click="$emit('close')">取消</button>
      <button class="btn-primary" :disabled="!canApply" @click="apply">应用</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  columns: { type: Array, required: true },
  data: { type: Array, required: true },
})

const emit = defineEmits(['apply', 'close'])

const types = [
  { value: 'bar', label: '柱图', icon: '📊' },
  { value: 'stacked_bar', label: '堆叠柱图', icon: '📚' },
  { value: 'line', label: '折线图', icon: '📈' },
  { value: 'area', label: '面积图', icon: '🏔️' },
  { value: 'pie', label: '饼图', icon: '🥧' },
  { value: 'scatter', label: '散点图', icon: '✨' },
]

const numericColumns = computed(() => props.columns.filter(c => c.type === 'numeric'))
const textColumns = computed(() => props.columns.filter(c => c.type !== 'numeric'))

const chartType = ref('bar')
const xField = ref(textColumns.value[0]?.name || props.columns[0]?.name || '')
const yFields = ref(numericColumns.value.slice(0, 1).map(c => c.name))
const title = ref('')

const canApply = computed(() => xField.value && yFields.value.length > 0)

watch(chartType, (t) => {
  // 饼图只保留 1 个 Y
  if (t === 'pie' && yFields.value.length > 1) {
    yFields.value = yFields.value.slice(0, 1)
  }
})

function toggleY(name) {
  if (chartType.value === 'pie') {
    yFields.value = [name]
    return
  }
  const i = yFields.value.indexOf(name)
  if (i >= 0) yFields.value.splice(i, 1)
  else yFields.value.push(name)
}

function apply() {
  emit('apply', {
    type: chartType.value,
    title: title.value || `${yFields.value.join(', ')} 按 ${xField.value}`,
    x: xField.value,
    y: [...yFields.value],
    data: props.data,
  })
  emit('close')
}
</script>

<style scoped>
.config-panel {
  margin-top: 8px; border: 1px solid var(--color-primary); border-radius: 8px;
  background: var(--bg-card); overflow: hidden;
}
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: var(--bg-active);
  font-size: 13px; font-weight: 600; color: var(--color-primary);
}
.close-btn {
  background: none; border: none; cursor: pointer;
  font-size: 14px; color: var(--color-primary); padding: 0 4px;
}
.panel-body { padding: 12px; }
.form-row { margin-bottom: 12px; }
.form-row label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; font-weight: 500; }
.form-row select,
.form-row input[type="text"] {
  width: 100%; padding: 6px 8px; font-size: 13px;
  border: 1px solid var(--border-input); border-radius: 4px; outline: none;
}
.type-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
}
.type-btn {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 8px 4px; background: var(--bg-card);
  border: 1px solid var(--border-input); border-radius: 6px; cursor: pointer;
  font-size: 12px; color: var(--text-secondary);
}
.type-btn:hover { border-color: var(--color-primary); background: var(--bg-surface); }
.type-btn.active {
  background: var(--bg-active); border-color: var(--color-primary); color: var(--color-primary); font-weight: 600;
}
.type-icon { font-size: 18px; }
.y-list {
  display: flex; flex-wrap: wrap; gap: 6px 12px;
  max-height: 120px; overflow-y: auto;
  padding: 6px; border: 1px solid var(--border-light); border-radius: 4px; background: var(--bg-surface);
}
.y-item {
  display: flex; align-items: center; gap: 4px;
  font-size: 13px; color: var(--text-primary); cursor: pointer; margin: 0;
}
.empty-hint { font-size: 12px; color: var(--text-tertiary); padding: 4px; }
.panel-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 8px 12px; border-top: 1px solid var(--border-light); background: var(--code-bg);
}
.btn-primary, .btn-secondary {
  padding: 5px 14px; font-size: 13px; border-radius: 4px;
  cursor: pointer; border: 1px solid;
}
.btn-primary { background: var(--color-primary); color: var(--text-inverse); border-color: var(--color-primary); }
.btn-primary:disabled { background: var(--text-muted); border-color: var(--text-muted); cursor: not-allowed; }
.btn-secondary { background: var(--bg-card); color: var(--text-secondary); border-color: var(--border-input); }
.btn-secondary:hover { background: var(--bg-hover); }
</style>
