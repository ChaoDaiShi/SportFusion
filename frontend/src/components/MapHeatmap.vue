<template>
  <div class="map-wrap">
    <div v-if="!mapLoaded" class="map-loading">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>地图数据加载中...</span>
    </div>
    <div ref="chartRef" class="map-chart" :style="{ height: height + 'px' }" v-show="mapLoaded"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { resizeChart, disposeChart } from '../utils/echarts'

const props = defineProps({
  title: { type: String, default: '热力图' },
  valueLabel: { type: String, default: '体育产出指数' },
  unit: { type: String, default: '' },
  data: { type: Array, default: () => [] },
  height: { type: Number, default: 450 },
})

const emit = defineEmits(['region-click'])

const chartRef = ref(null)
const mapLoaded = ref(false)
let chart = null

async function loadSichuanMap() {
  try {
    const response = await fetch('https://geo.datav.aliyun.com/areas_v3/bound/510000_full.json')
    const geoJson = await response.json()
    echarts.registerMap('sichuan', geoJson)
    mapLoaded.value = true
  } catch {
    // 降级：使用简单散点图
    mapLoaded.value = true
  }
}

function render() {
  if (!chartRef.value || !props.data.length) return
  disposeChart(chart)
  chart = echarts.init(chartRef.value)
  const maxVal = Math.max(...props.data.map((d) => d.value), 10000)

  const option = {
    title: { text: props.title, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'item', formatter: (item) => `${item.name}<br/>${props.valueLabel}: ${item.value}${props.unit}` },
    visualMap: {
      min: 0,
      max: maxVal,
      left: 'left',
      bottom: 20,
      text: ['高', '低'],
      inRange: { color: ['#f4efe4', '#efb63a', '#e75b43'] },
      calculable: true,
    },
    series: [],
  }

  // 尝试加载地图，否则使用柱状图替代
  if (echarts.getMap('sichuan')) {
    option.geo = {
      map: 'sichuan',
      roam: true,
      label: { show: true, fontSize: 10, color: '#666' },
      itemStyle: { areaColor: '#f4efe4', borderColor: '#d8cfbf' },
      emphasis: { itemStyle: { areaColor: '#efb63a' } },
    }
    option.series = [{ type: 'map', map: 'sichuan', geoIndex: 0, data: props.data }]
  } else {
    // 降级为柱状图
    option.xAxis = { type: 'category', data: props.data.map((d) => d.name), axisLabel: { rotate: 30 } }
    option.yAxis = { type: 'value', name: props.valueLabel }
    option.series = [{
      type: 'bar',
      data: props.data.map((d) => d.value),
      itemStyle: { borderRadius: [4, 4, 0, 0], color: '#3157d6' },
    }]
  }

  chart.setOption(option, { notMerge: true })

  // 地图点击事件 — 下钻到市州详情
  chart.off('click')
  chart.on('click', (params) => {
    if (params.componentType === 'series' || params.componentSubType === 'map') {
      emit('region-click', { name: params.name, value: params.value })
    }
  })

  resizeChart(chart)
}

onMounted(async () => {
  await loadSichuanMap()
  render()
})

watch(() => props.data, render, { deep: true })

onUnmounted(() => disposeChart(chart))
</script>

<style scoped>
.map-wrap { position: relative; }
.map-loading { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 60px 0; color: #909399; }
.map-chart { width: 100%; }
</style>
