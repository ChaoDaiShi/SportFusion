import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as scaleApi from '../api/scale'

export const useScaleStore = defineStore('scale', () => {
  const summary = ref(null)
  const category = ref([])
  const regional = ref([])
  const comparison = ref(null)
  const cacheKey = ref('')
  const fields = ref([])
  const loading = ref(false)

  async function fetchFields() {
    const res = await scaleApi.getScaleFields()
    if (res.code === 200) {
      fields.value = res.data
    }
    return res.data
  }

  async function doCalculate(data) {
    loading.value = true
    try {
      const res = await scaleApi.calculateScale(data)
      if (res.code === 200) {
        const d = res.data
        cacheKey.value = d.cache_key
        summary.value = {
          total_estimated_scale: d.total_scale,
          enterprise_count: d.enterprise_count,
          type_summary: d.type_summary,
        }
        category.value = d.category || []
        comparison.value = d.comparison || null
      }
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchSummary(key) {
    const res = await scaleApi.getScaleSummary(key || cacheKey.value)
    if (res.code === 200) {
      summary.value = res.data
      category.value = res.data.category || []
      comparison.value = res.data.comparison || null
    }
    return res.data
  }

  async function fetchRegional(key, region) {
    const res = await scaleApi.getRegionalScale(key || cacheKey.value, region)
    if (res.code === 200) {
      regional.value = res.data
    }
    return res.data
  }

  async function fetchComparison(key) {
    const res = await scaleApi.getMethodComparison(key || cacheKey.value)
    if (res.code === 200) {
      comparison.value = res.data
    }
    return res.data
  }

  function formatAmount(val) {
    if (val == null || isNaN(val)) return '—'
    if (Math.abs(val) >= 10000) return (val / 10000).toFixed(1) + ' 亿'
    return val.toFixed(0) + ' 万'
  }

  return {
    summary, category, regional, comparison, cacheKey, fields, loading,
    fetchFields, doCalculate, fetchSummary, fetchRegional, fetchComparison,
    formatAmount,
  }
})
