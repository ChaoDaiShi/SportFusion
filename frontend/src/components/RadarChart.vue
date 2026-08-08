<template>
  <div ref="chartRef" class="radar-chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { initChart, getRadarOption, resizeChart, disposeChart } from '../utils/echarts'

const props = defineProps({
  title: { type: String, default: '雷达图' },
  indicators: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  height: { type: Number, default: 380 },
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  chart = initChart(chartRef.value, getRadarOption({
    title: props.title,
    indicators: props.indicators,
    series: props.series,
  }))
  resizeChart(chart)
}

onMounted(render)

watch(
  () => [props.indicators, props.series, props.title],
  () => { disposeChart(chart); render() },
  { deep: true }
)

onUnmounted(() => disposeChart(chart))
</script>

<style scoped>
.radar-chart { width: 100%; }
</style>
