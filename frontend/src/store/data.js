import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as dataApi from '../api/data'

export const useDataStore = defineStore('data', () => {
  const fileInfo = ref(null)
  const previewData = ref({ records: [], total: 0 })
  const preprocessStats = ref(null)
  const sportEnterprises = ref({ records: [], total: 0 })
  const loading = ref(false)
  const uploadFile = ref(null)
  const queryParams = ref({ fileId: null, page: 1, pageSize: 20 })

  async function upload(file) {
    loading.value = true
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await dataApi.uploadFile(formData)
      fileInfo.value = res.data
      uploadFile.value = file
      queryParams.value.fileId = res.data.file_id
      queryParams.value.page = 1
      // 重置预处理结果
      preprocessStats.value = null
      sportEnterprises.value = { records: [], total: 0 }
      return res
    } finally {
      loading.value = false
    }
  }

  async function fetchPreview(fileId, params = {}) {
    const res = await dataApi.previewData(fileId, params)
    previewData.value = res.data
    return res
  }

  async function clean(fileId, rules = {}) {
    loading.value = true
    try {
      const res = await dataApi.cleanData(fileId, rules)
      fileInfo.value = { ...fileInfo.value, ...res.data }
      return res
    } finally {
      loading.value = false
    }
  }

  async function nlpPreprocess(fileId) {
    loading.value = true
    try {
      const res = await dataApi.nlpPreprocess(fileId)
      if (res.code === 200) {
        preprocessStats.value = res.data.stats
      }
      return res
    } finally {
      loading.value = false
    }
  }

  async function fetchPreprocessStats(fileId) {
    const res = await dataApi.preprocessStats(fileId)
    if (res.code === 200) {
      preprocessStats.value = res.data.stats
    }
    return res
  }

  async function fetchSportEnterprises(fileId, params = {}) {
    const res = await dataApi.sportEnterprises(fileId, params)
    if (res.code === 200) {
      sportEnterprises.value = res.data
    }
    return res
  }

  return {
    fileInfo, previewData, preprocessStats, sportEnterprises, loading, uploadFile, queryParams,
    upload, fetchPreview, clean, nlpPreprocess, fetchPreprocessStats, fetchSportEnterprises,
  }
})
