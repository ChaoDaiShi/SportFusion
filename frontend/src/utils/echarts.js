import * as echarts from 'echarts'

// 注册中国地图（需要echarts地图组件，此处使用中国地图JSON或在线加载）
// 线上可通过 http://geo.datav.aliyun.com/areas_v3/bound/100000_full.json 获取

/**
 * 初始化ECharts图表
 */
export function initChart(dom, option) {
  const chart = echarts.init(dom)
  chart.setOption(option)
  return chart
}

/**
 * 饼图配置
 */
export function getPieOption({ title, data, name = '产值（万元）' }) {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c}万元 ({d}%)' },
    legend: { bottom: 10, type: 'scroll' },
    series: [{
      name,
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '50%'],
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%' },
      emphasis: { label: { fontSize: 18, fontWeight: 'bold' } },
      data,
    }],
  }
}

/**
 * 柱状图配置
 */
export function getBarOption({ title, labels, series, xName, yName = '产值（万元）' }) {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: labels, name: xName, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: yName },
    series: series.map((s) => ({
      ...s,
      type: 'bar',
      itemStyle: { borderRadius: [4, 4, 0, 0] },
    })),
  }
}

/**
 * 折线图配置
 */
export function getLineOption({ title, labels, series }) {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'axis' },
    legend: { bottom: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: labels, boundaryGap: false },
    yAxis: { type: 'value', name: '产值（万元）' },
    series: series.map((s) => ({
      ...s,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
    })),
  }
}

/**
 * 地图热力图配置（需要加载中国地图GeoJSON）
 */
export function getMapOption({ title, data }) {
  const validData = data || []
  const maxValue = validData.length > 0 
    ? Math.max(...validData.map((d) => d.value || 0), 10000)
    : 10000
  
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'item', formatter: '{b}<br/>体育产值: {c}万元' },
    visualMap: {
      min: 0,
      max: maxValue,
      left: 'left',
      bottom: 20,
      text: ['高', '低'],
      inRange: { color: ['#e0f3ff', '#409eff', '#1a3a5c'] },
      calculable: true,
    },
    geo: {
      map: 'china',
      roam: true,
      label: { show: true, fontSize: 10, color: '#666' },
      itemStyle: { areaColor: '#f3f3f3', borderColor: '#ddd' },
      emphasis: { itemStyle: { areaColor: '#a6c8ff' } },
    },
    series: [{
      type: 'map',
      map: 'china',
      geoIndex: 0,
      data,
    }],
  }
}

/**
 * 雷达图配置
 */
export function getRadarOption({ title, indicators, series, shape = 'polygon' }) {
  const validSeries = series || []
  const validIndicators = indicators || []
  
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'item' },
    legend: { bottom: 10, type: 'scroll', data: validSeries.map(s => s.name) },
    radar: {
      shape,
      indicator: validIndicators,
      center: ['50%', '55%'],
      radius: '60%',
    },
    series: [{
      type: 'radar',
      data: validSeries.map(s => ({
        name: s.name,
        value: s.data || [],
        areaStyle: s.areaStyle || { opacity: 0.15 },
        lineStyle: s.lineStyle || { width: 2 },
        itemStyle: s.itemStyle || {},
      })),
    }],
  }
}

/**
 * 仪表盘配置
 */
export function getGaugeOption({ title, value, max = 100, color, unit = '%' }) {
  const colors = color
    ? [[1, color]]
    : [[0.4, '#67c23a'], [0.7, '#e6a23c'], [1, '#f56c6c']]
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 13 } },
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      center: ['50%', '60%'],
      radius: '85%',
      min: 0,
      max,
      splitNumber: 10,
      axisLine: { show: true, lineStyle: { width: 16, color: colors } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: true, fontSize: 9, distance: 5 },
      pointer: { length: '65%', width: 5, itemStyle: { color: '#303133' } },
      detail: {
        valueAnimation: true,
        formatter: `{value}${unit}`,
        fontSize: 18,
        offsetCenter: [0, '70%'],
      },
      data: [{ value }],
    }],
  }
}

/**
 * 散点图配置
 */
export function getScatterOption({ title, data, xName, yName, symbolSize = 8 }) {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.seriesName}<br/>${xName}: ${p.value[0]}<br/>${yName}: ${p.value[1]}`,
    },
    grid: { left: '8%', right: '4%', bottom: '8%', top: '15%', containLabel: true },
    xAxis: { type: 'value', name: xName, splitLine: { lineStyle: { type: 'dashed' } } },
    yAxis: { type: 'value', name: yName, splitLine: { lineStyle: { type: 'dashed' } } },
    series: data.map((s) => ({
      type: 'scatter',
      name: s.name,
      data: s.data,
      symbolSize: s.symbolSize || symbolSize,
      itemStyle: s.itemStyle || { opacity: 0.7 },
    })),
  }
}

/**
 * 漏斗图配置
 */
export function getFunnelOption({ title, data, sort = 'descending' }) {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 10 },
    series: [{
      type: 'funnel',
      left: '10%',
      top: 40,
      bottom: 40,
      width: '80%',
      sort,
      gap: 2,
      label: { show: true, position: 'inside', formatter: '{b}\n{c}' },
      emphasis: { label: { fontSize: 16 } },
      itemStyle: { borderColor: '#fff', borderWidth: 1 },
      data,
    }],
  }
}

/**
 * 堆叠柱状图配置
 */
export function getStackedBarOption({ title, labels, series, xName, yName = '产值（万元）', orient = 'vertical' }) {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { bottom: 10, type: 'scroll' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: orient === 'vertical' ? 'category' : 'value',
      data: orient === 'vertical' ? labels : undefined,
      name: orient === 'vertical' ? xName : undefined,
      axisLabel: orient === 'vertical' ? { rotate: 30 } : undefined,
    },
    yAxis: {
      type: orient === 'vertical' ? 'value' : 'category',
      data: orient === 'vertical' ? undefined : labels,
      name: orient === 'vertical' ? yName : undefined,
    },
    series: series.map((s) => ({
      ...s,
      type: 'bar',
      stack: 'total',
      itemStyle: { borderRadius: s.last ? [4, 4, 0, 0] : 0 },
      emphasis: { focus: 'series' },
    })),
  }
}

/**
 * 矩形树图配置
 */
export function getTreemapOption({ title, data, name = '产出指数' }) {
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [{
      type: 'treemap',
      width: '90%',
      height: '75%',
      left: 'center',
      top: 40,
      roam: false,
      breadcrumb: { show: true, top: 'bottom' },
      label: { show: true, formatter: '{b}' },
      itemStyle: { borderColor: '#fff' },
      levels: [
        { itemStyle: { borderWidth: 3, gapWidth: 2 } },
        { colorSaturation: [0.3, 0.6], itemStyle: { gapWidth: 1 } },
      ],
      data,
    }],
  }
}

// 保存各图表实例的清理函数映射
const _resizeCleaners = new WeakMap()

/**
 * 响应式调整图表大小
 * 自动记录 cleanup 函数到 WeakMap，dispose 时自动移除
 */
export function resizeChart(chart) {
  if (!chart) return
  // 如果已有绑定的 handler，先移除旧的
  const oldCleanup = _resizeCleaners.get(chart)
  if (oldCleanup) oldCleanup()

  const handler = () => {
    try { chart.resize() } catch { /* 图表可能已销毁 */ }
  }
  window.addEventListener('resize', handler)
  _resizeCleaners.set(chart, () => window.removeEventListener('resize', handler))
}

/**
 * 销毁图表（同时移除 resize 监听）
 */
export function disposeChart(chart) {
  if (!chart) return
  // 先移除 resize 监听
  const cleanup = _resizeCleaners.get(chart)
  if (cleanup) {
    cleanup()
    _resizeCleaners.delete(chart)
  }
  try { chart.dispose() } catch { /* 已销毁 */ }
}
