<template>
  <div ref="chartRef" class="line-chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { initChart, getLineOption, resizeChart, disposeChart } from '../utils/echarts'

const props = defineProps({
  title: { type: String, default: '折线图' },
  labels: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  height: { type: Number, default: 350 },
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  chart = initChart(chartRef.value, getLineOption({
    title: props.title,
    labels: props.labels,
    series: props.series,
  }))
  resizeChart(chart)
}

onMounted(render)

watch(
  () => [props.labels, props.series],
  () => { disposeChart(chart); render() },
  { deep: true }
)

onUnmounted(() => disposeChart(chart))
</script>

<style scoped>
.line-chart { width: 100%; }
</style>
