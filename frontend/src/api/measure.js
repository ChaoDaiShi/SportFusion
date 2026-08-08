import request from './index'

// 单企业测算
export function measureSingle(data) {
  return request.post('/measure/single', data)
}

// 批量测算
export function measureBatch(items) {
  return request.post('/measure/batch', { items })
}

// 计算精度指标
export function calcMetrics(predicted, actual) {
  return request.post('/measure/metrics', { predicted, actual })
}
