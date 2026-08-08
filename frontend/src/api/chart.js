import request from './index'

// 饼图数据
export function getPieData(dimension, fileId) {
  const params = { dimension }
  if (fileId) params.file_id = fileId
  return request.get('/chart/pie', { params })
}

// 柱状图数据
export function getBarData(dimension, fileId) {
  const params = { dimension }
  if (fileId) params.file_id = fileId
  return request.get('/chart/bar', { params })
}

// 地图热力图数据
export function getMapData(fileId) {
  const params = {}
  if (fileId) params.file_id = fileId
  return request.get('/chart/map', { params })
}

// 折线趋势图数据
export function getLineData(fileId) {
  const params = {}
  if (fileId) params.file_id = fileId
  return request.get('/chart/line', { params })
}

// 全景大屏综合数据
export function getDashboardData(fileId) {
  const params = {}
  if (fileId) params.file_id = fileId
  return request.get('/chart/dashboard', { params })
}

// 产业分析报告
export function getAnalysisReport(fileId) {
  const params = {}
  if (fileId) params.file_id = fileId
  return request.get('/chart/analysis-report', { params })
}
