<template>
  <div ref="chartRef" class="scatter-chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { initChart, getScatterOption, resizeChart, disposeChart } from '../utils/echarts'

const props = defineProps({
  title: { type: String, default: '散点图' },
  data: { type: Array, default: () => [] },
  xName: { type: String, default: 'X轴' },
  yName: { type: String, default: 'Y轴' },
  symbolSize: { type: Number, default: 8 },
  height: { type: Number, default: 400 },
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  chart = initChart(chartRef.value, getScatterOption({
    title: props.title,
    data: props.data,
    xName: props.xName,
    yName: props.yName,
    symbolSize: props.symbolSize,
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
.scatter-chart { width: 100%; }
</style>
