import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as recognitionApi from '../api/recognition'

export const useRecognitionStore = defineStore('recognition', () => {
  const results = ref([])
  const categories = ref({})
  const loading = ref(false)

  async function recognizeSingle(data) {
    loading.value = true
    try {
      const res = await recognitionApi.recognizeSingle(data)
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function recognizeBatch(enterprises) {
    loading.value = true
    try {
      const res = await recognitionApi.recognizeBatch(enterprises)
      results.value = res.data.results
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchCategories() {
    const res = await recognitionApi.getCategories()
    categories.value = res.data
    return res.data
  }

  return { results, categories, loading, recognizeSingle, recognizeBatch, fetchCategories }
})
