import request from './index'

// 单条企业识别
export function recognizeSingle(data) {
  return request.post('/recognition/single', data)
}

// 批量企业识别
export function recognizeBatch(enterprises) {
  return request.post('/recognition/batch', { enterprises })
}

// 获取业态分类定义
export function getCategories() {
  return request.get('/recognition/categories')
}

// 全量识别+比重测算
export function recognizeBatchFull(data) {
  return request.post('/recognition/batch-full', data)
}

// 单企业详细分析
export function enterpriseDetail(creditCode) {
  return request.get(`/recognition/enterprise/${creditCode}`)
}

// 识别统计概览
export function recognitionStats(fileId) {
  return request.get('/recognition/stats', { params: { file_id: fileId } })
}

// 业务线解析演示
export function businessLinesDemo(text) {
  return request.get('/recognition/business-lines', { params: { text } })
}
