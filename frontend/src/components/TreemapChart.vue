<template>
  <div ref="chartRef" class="treemap-chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { initChart, getTreemapOption, resizeChart, disposeChart } from '../utils/echarts'

const props = defineProps({
  title: { type: String, default: '矩形树图' },
  data: { type: Array, default: () => [] },
  name: { type: String, default: '产出指数' },
  height: { type: Number, default: 380 },
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  chart = initChart(chartRef.value, getTreemapOption({
    title: props.title,
    data: props.data,
    name: props.name,
  }))
  resizeChart(chart)
}

onMounted(render)

watch(
  () => [props.data, props.title],
  () => { disposeChart(chart); render() },
  { deep: true }
)

onUnmounted(() => disposeChart(chart))
</script>

<style scoped>
.treemap-chart { width: 100%; }
</style>
