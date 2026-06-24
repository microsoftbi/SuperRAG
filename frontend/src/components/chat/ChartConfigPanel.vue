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
  margin-top: 8px; border: 1px solid #1976d2; border-radius: 8px;
  background: #fff; overflow: hidden;
}
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: #e3f2fd;
  font-size: 13px; font-weight: 600; color: #1976d2;
}
.close-btn {
  background: none; border: none; cursor: pointer;
  font-size: 14px; color: #1976d2; padding: 0 4px;
}
.panel-body { padding: 12px; }
.form-row { margin-bottom: 12px; }
.form-row label { display: block; font-size: 12px; color: #555; margin-bottom: 6px; font-weight: 500; }
.form-row select,
.form-row input[type="text"] {
  width: 100%; padding: 6px 8px; font-size: 13px;
  border: 1px solid #d0d4db; border-radius: 4px; outline: none;
}
.type-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
}
.type-btn {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 8px 4px; background: #fff;
  border: 1px solid #d0d4db; border-radius: 6px; cursor: pointer;
  font-size: 12px; color: #555;
}
.type-btn:hover { border-color: #1976d2; background: #f5faff; }
.type-btn.active {
  background: #e3f2fd; border-color: #1976d2; color: #1976d2; font-weight: 600;
}
.type-icon { font-size: 18px; }
.y-list {
  display: flex; flex-wrap: wrap; gap: 6px 12px;
  max-height: 120px; overflow-y: auto;
  padding: 6px; border: 1px solid #eef0f3; border-radius: 4px; background: #fafbfc;
}
.y-item {
  display: flex; align-items: center; gap: 4px;
  font-size: 13px; color: #333; cursor: pointer; margin: 0;
}
.empty-hint { font-size: 12px; color: #999; padding: 4px; }
.panel-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 8px 12px; border-top: 1px solid #eef0f3; background: #f6f8fa;
}
.btn-primary, .btn-secondary {
  padding: 5px 14px; font-size: 13px; border-radius: 4px;
  cursor: pointer; border: 1px solid;
}
.btn-primary { background: #1976d2; color: #fff; border-color: #1976d2; }
.btn-primary:disabled { background: #ccc; border-color: #ccc; cursor: not-allowed; }
.btn-secondary { background: #fff; color: #555; border-color: #d0d4db; }
.btn-secondary:hover { background: #f0f0f0; }
</style>
