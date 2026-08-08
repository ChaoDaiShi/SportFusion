<template>
  <div ref="chartRef" class="pie-chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { initChart, getPieOption, resizeChart, disposeChart } from '../utils/echarts'

const props = defineProps({
  title: { type: String, default: '饼图' },
  data: { type: Array, default: () => [] },
  name: { type: String, default: '产值（万元）' },
  height: { type: Number, default: 350 },
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  chart = initChart(chartRef.value, getPieOption({
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
.pie-chart { width: 100%; }
</style>
