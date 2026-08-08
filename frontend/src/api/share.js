import request from './index'

const BASE = '/share'

export function estimateShare(data) {
  return request.post(`${BASE}/estimate`, data)
}

export function batchEstimate(data) {
  return request.post(`${BASE}/batch-estimate`, data)
}

export function getShareResult(enterpriseId) {
  return request.get(`${BASE}/result/${enterpriseId}`)
}

export function getShareStats(cacheKey) {
  return request.get(`${BASE}/stats`, { params: { cache_key: cacheKey } })
}

export function manualAdjust(data) {
  return request.post(`${BASE}/manual-adjust`, data)
}

export function getBands() {
  return request.get(`${BASE}/bands`)
}
