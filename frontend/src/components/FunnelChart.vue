<template>
  <div ref="chartRef" class="funnel-chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { initChart, getFunnelOption, resizeChart, disposeChart } from '../utils/echarts'

const props = defineProps({
  title: { type: String, default: '漏斗图' },
  data: { type: Array, default: () => [] },
  height: { type: Number, default: 400 },
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  chart = initChart(chartRef.value, getFunnelOption({
    title: props.title,
    data: props.data,
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
.funnel-chart { width: 100%; }
</style>
