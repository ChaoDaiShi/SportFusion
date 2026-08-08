import request from './index'

// 获取模型评估汇总
export function getValidateSummary(fileId) {
  return request.get('/validate/summary', { params: { file_id: fileId } })
}

// 运行模型校验
export function runValidation(data) {
  return request.post('/validate/run', data)
}

// 混淆矩阵
export function getConfusionMatrix() {
  return request.get('/validate/confusion')
}
