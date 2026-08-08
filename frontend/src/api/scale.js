import request from './index'

const BASE = '/scale'

export function getScaleFields() {
  return request.get(`${BASE}/fields`)
}

export function calculateScale(data) {
  return request.post(`${BASE}/calculate`, data)
}

export function getScaleSummary(cacheKey) {
  return request.get(`${BASE}/summary`, { params: { cache_key: cacheKey } })
}

export function getCategoryScale(cacheKey) {
  return request.get(`${BASE}/category`, { params: { cache_key: cacheKey } })
}

export function getRegionalScale(cacheKey, region) {
  return request.get(`${BASE}/regional`, { params: { cache_key: cacheKey, region } })
}

export function getMethodComparison(cacheKey) {
  return request.get(`${BASE}/comparison`, { params: { cache_key: cacheKey } })
}
