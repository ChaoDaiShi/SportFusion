import request from './index'

// 文件上传
export function uploadFile(formData) {
  return request.post('/data/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 数据预览
export function previewData(fileId, params = {}) {
  return request.get(`/data/preview/${fileId}`, { params })
}

// 数据清洗
export function cleanData(fileId, cleanRules = {}) {
  return request.post(`/data/clean/${fileId}`, { clean_rules: cleanRules })
}

// 导出数据
export function exportData(fileId, format = 'csv') {
  return request.get(`/data/export/${fileId}`, { params: { format }, responseType: 'blob' })
}

// NLP预处理
export function nlpPreprocess(fileId) {
  return request.post(`/data/preprocess/${fileId}`)
}

// 预处理统计
export function preprocessStats(fileId) {
  return request.get(`/data/preprocess-result/${fileId}`)
}

// 体育企业明细
export function sportEnterprises(fileId, params = {}) {
  return request.get(`/data/preprocess-sport/${fileId}`, { params })
}
