import request from './index'

const BASE = '/review'

export function generateTasks(data) {
  return request.post(`${BASE}/tasks/generate`, data)
}

export function listTasks(params) {
  return request.get(`${BASE}/tasks`, { params })
}

export function getTaskDetail(taskId) {
  return request.get(`${BASE}/tasks/${taskId}`)
}

export function assignTask(taskId, data) {
  return request.post(`${BASE}/tasks/${taskId}/assign`, data)
}

export function submitReviewRecord(data) {
  return request.post(`${BASE}/records`, data)
}

export function getConsensus(taskId) {
  return request.get(`${BASE}/tasks/${taskId}/consensus`)
}

export function doArbitrate(data) {
  return request.post(`${BASE}/arbitrate`, data)
}

export function getReviewStats(batchId) {
  return request.get(`${BASE}/stats`, { params: { batch_id: batchId } })
}
