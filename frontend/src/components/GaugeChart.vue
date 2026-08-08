<template>
  <div ref="chartRef" class="gauge-chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { initChart, getGaugeOption, resizeChart, disposeChart } from '../utils/echarts'

const props = defineProps({
  title: { type: String, default: '仪表盘' },
  value: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  color: { type: String, default: '' },
  unit: { type: String, default: '%' },
  height: { type: Number, default: 220 },
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  chart = initChart(chartRef.value, getGaugeOption({
    title: props.title,
    value: props.value,
    max: props.max,
    color: props.color || undefined,
    unit: props.unit,
  }))
  resizeChart(chart)
}

onMounted(render)

watch(
  () => [props.value, props.max, props.title],
  () => { disposeChart(chart); render() },
  { deep: true }
)

onUnmounted(() => disposeChart(chart))
</script>

<style scoped>
.gauge-chart { width: 100%; }
</style>
