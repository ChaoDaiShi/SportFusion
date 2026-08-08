<template>
  <div ref="chartRef" class="bar-chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { initChart, getBarOption, getStackedBarOption, resizeChart, disposeChart } from '../utils/echarts'

const props = defineProps({
  title: { type: String, default: '柱状图' },
  labels: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  xName: { type: String, default: '' },
  yName: { type: String, default: '产值（万元）' },
  height: { type: Number, default: 350 },
  stacked: { type: Boolean, default: false },
  horizontal: { type: Boolean, default: false },
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  const fn = props.stacked ? getStackedBarOption : getBarOption
  chart = initChart(chartRef.value, fn({
    title: props.title,
    labels: props.labels,
    series: props.series,
    xName: props.xName,
    yName: props.yName,
    orient: props.horizontal ? 'horizontal' : 'vertical',
  }))
  resizeChart(chart)
}

onMounted(render)

watch(
  () => [props.labels, props.series, props.title, props.stacked],
  () => { disposeChart(chart); render() },
  { deep: true }
)

onUnmounted(() => disposeChart(chart))
</script>

<style scoped>
.bar-chart { width: 100%; }
</style>
