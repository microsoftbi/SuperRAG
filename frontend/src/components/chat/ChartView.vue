<template>
  <div class="chart-view">
    <div class="chart-toolbar">
      <span class="chart-title">{{ spec.title || '图表' }}</span>
      <div class="chart-actions">
        <select v-model="currentType" class="type-select" title="切换图表类型">
          <option value="bar">柱图</option>
          <option value="stacked_bar">堆叠柱图</option>
          <option value="line">折线图</option>
          <option value="area">面积图</option>
          <option value="pie">饼图</option>
          <option value="scatter">散点图</option>
        </select>
        <button class="icon-btn" @click="exportPng" title="导出 PNG">⬇️ PNG</button>
        <button class="icon-btn" @click="toggleFullscreen" title="全屏">{{ isFullscreen ? '⛶' : '⛶' }}</button>
      </div>
    </div>
    <div ref="chartRef" :class="['chart-canvas', { fullscreen: isFullscreen }]"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, ScatterChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, ToolboxComponent, DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart, LineChart, PieChart, ScatterChart,
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, ToolboxComponent, DataZoomComponent,
  CanvasRenderer,
])

const props = defineProps({
  spec: { type: Object, required: true },
})

const chartRef = ref(null)
const currentType = ref(props.spec.type || 'bar')
const isFullscreen = ref(false)
let chartInstance = null

function getChartColors() {
  const val = getComputedStyle(document.documentElement)
    .getPropertyValue('--chart-colors').trim()
  if (val) return val.split(',').map(c => c.trim())
  return ['#1976d2', '#26a69a', '#ef6c00', '#ab47bc', '#5e35b1', '#00897b', '#d81b60', '#43a047']
}

function buildOption(type) {
  const { x, y, data, title } = props.spec
  const xData = data.map(r => String(r[x] ?? ''))
  const colors = getChartColors()

  if (type === 'pie') {
    const yField = y[0]
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { type: 'scroll', orient: 'vertical', right: 10, top: 30, bottom: 10 },
      color: colors,
      series: [{
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['40%', '55%'],
        data: data.map(r => ({ name: String(r[x] ?? ''), value: Number(r[yField]) || 0 })),
        label: { formatter: '{b}\n{d}%' },
      }],
    }
  }

  const isStacked = type === 'stacked_bar'
  const isArea = type === 'area'
  const baseType = (type === 'bar' || type === 'stacked_bar') ? 'bar'
                  : (type === 'line' || type === 'area') ? 'line'
                  : type

  const series = y.map((yField, i) => ({
    name: yField,
    type: baseType,
    data: data.map(r => Number(r[yField]) || 0),
    ...(isStacked ? { stack: 'total' } : {}),
    ...(isArea ? { areaStyle: { opacity: 0.3 } } : {}),
    ...(baseType === 'line' ? { smooth: true, symbol: 'circle', symbolSize: 6 } : {}),
    itemStyle: { color: colors[i % colors.length] },
  }))

  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: baseType === 'bar' ? 'shadow' : 'line' },
    },
    legend: { top: 28, type: 'scroll' },
    grid: { left: 50, right: 20, top: 70, bottom: 50 },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { rotate: xData.some(s => s.length > 6) ? 30 : 0, interval: 0 },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: v => {
          if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(1) + '亿'
          if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '万'
          return v.toLocaleString()
        },
      },
    },
    color: colors,
    series,
    ...(xData.length > 15 ? {
      dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    } : {}),
  }
}

function render() {
  if (!chartInstance) return
  chartInstance.setOption(buildOption(currentType.value), true)
}

function exportPng() {
  if (!chartInstance) return
  const bg = getComputedStyle(document.documentElement)
    .getPropertyValue('--bg-card').trim() || '#fff'
  const url = chartInstance.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: bg })
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.spec.title || 'chart'}.png`
  a.click()
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  nextTick(() => chartInstance?.resize())
}

function onResize() {
  chartInstance?.resize()
}

onMounted(() => {
  chartInstance = echarts.init(chartRef.value)
  render()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartInstance?.dispose()
  chartInstance = null
})

watch(currentType, render)
watch(() => props.spec, () => {
  currentType.value = props.spec.type || 'bar'
  nextTick(render)
}, { deep: true })

// Re-render on theme change
import { useTheme } from '../../composables/useTheme.js'
const { isDark } = useTheme()
watch(isDark, () => nextTick(render))
</script>

<style scoped>
.chart-view {
  margin-top: 12px;
  border: 1px solid var(--code-border);
  border-radius: 8px;
  background: var(--bg-card);
  overflow: hidden;
}
.chart-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px;
  background: var(--code-bg);
  border-bottom: 1px solid var(--border-light);
}
.chart-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.chart-actions { display: flex; gap: 6px; align-items: center; }
.type-select {
  font-size: 12px; padding: 3px 6px;
  border: 1px solid var(--border-input); border-radius: 4px;
  background: var(--bg-card); cursor: pointer;
}
.icon-btn {
  font-size: 11px; color: var(--color-primary); background: var(--bg-card);
  border: 1px solid var(--color-primary); border-radius: 4px;
  padding: 3px 8px; cursor: pointer; line-height: 1.4;
}
.icon-btn:hover { background: var(--bg-active); }
.chart-canvas { width: 100%; height: 340px; padding: 4px; }
.chart-canvas.fullscreen {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  width: 100vw; height: 100vh; z-index: 9999;
  background: var(--bg-card); padding: 20px;
}
</style>
