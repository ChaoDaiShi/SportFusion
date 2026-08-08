import request from './index'

const BASE = '/system'

export function listBatches(params) {
  return request.get(`${BASE}/batches`, { params })
}

export function getBatchDetail(batchId) {
  return request.get(`${BASE}/batches/${batchId}`)
}

export function createBatch(data) {
  return request.post(`${BASE}/batches`, data)
}

export function lockBatch(batchId) {
  return request.post(`${BASE}/batches/${batchId}/lock`)
}

export function compareBatches(batchA, batchB) {
  return request.get(`${BASE}/batches/compare`, { params: { batch_a: batchA, batch_b: batchB } })
}

export function listLogs(params) {
  return request.get(`${BASE}/logs`, { params })
}
