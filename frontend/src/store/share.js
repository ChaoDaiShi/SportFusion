import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as shareApi from '../api/share'

export const useShareStore = defineStore('share', () => {
  const results = ref([])
  const stats = ref(null)
  const cacheKey = ref('')
  const bands = ref({})
  const loading = ref(false)

  async function estimateSingle(data) {
    loading.value = true
    try {
      const res = await shareApi.estimateShare(data)
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function estimateBatch(items) {
    loading.value = true
    try {
      const res = await shareApi.batchEstimate(items)
      if (res.code === 200) {
        results.value = res.data.results
        stats.value = res.data.stats
        cacheKey.value = res.data.cache_key
      }
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchStats(key) {
    const res = await shareApi.getShareStats(key || cacheKey.value)
    if (res.code === 200) {
      stats.value = res.data
    }
    return res.data
  }

  async function fetchBands() {
    const res = await shareApi.getBands()
    if (res.code === 200) {
      bands.value = res.data
    }
    return res.data
  }

  async function doManualAdjust(data) {
    const res = await shareApi.manualAdjust(data)
    if (res.code === 200 && res.data) {
      // 更新内存中的结果
      const idx = results.value.findIndex(
        (r) => r.enterprise_id === res.data.enterprise_id
      )
      if (idx >= 0) {
        results.value[idx] = { ...results.value[idx], ...res.data }
      }
    }
    return res.data
  }

  return {
    results, stats, cacheKey, bands, loading,
    estimateSingle, estimateBatch, fetchStats, fetchBands, doManualAdjust,
  }
})
