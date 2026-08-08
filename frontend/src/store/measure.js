import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as measureApi from '../api/measure'

export const useMeasureStore = defineStore('measure', () => {
  const results = ref([])
  const summary = ref(null)
  const loading = ref(false)

  async function measureSingle(data) {
    loading.value = true
    try {
      const res = await measureApi.measureSingle(data)
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function measureBatch(items) {
    loading.value = true
    try {
      const res = await measureApi.measureBatch(items)
      results.value = res.data.results
      summary.value = {
        total_sport_revenue: res.data.total_sport_revenue,
        region_summary: res.data.region_summary,
        category_summary: res.data.category_summary,
      }
      return res.data
    } finally {
      loading.value = false
    }
  }

  return { results, summary, loading, measureSingle, measureBatch }
})
