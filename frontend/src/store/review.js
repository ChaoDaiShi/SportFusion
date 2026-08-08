import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as reviewApi from '../api/review'

export const useReviewStore = defineStore('review', () => {
  const tasks = ref([])
  const stats = ref(null)
  const currentTask = ref(null)
  const loading = ref(false)

  async function doGenerateTasks(data) {
    loading.value = true
    try {
      const res = await reviewApi.generateTasks(data)
      if (res.code === 200) {
        tasks.value = res.data.tasks
        stats.value = res.data.stats
      }
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchTasks(params = {}) {
    loading.value = true
    try {
      const res = await reviewApi.listTasks(params)
      if (res.code === 200) {
        tasks.value = res.data.tasks
        stats.value = res.data.stats
      }
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchTaskDetail(taskId) {
    const res = await reviewApi.getTaskDetail(taskId)
    if (res.code === 200) {
      currentTask.value = res.data
    }
    return res.data
  }

  async function doAssignTask(taskId, data) {
    const res = await reviewApi.assignTask(taskId, data)
    return res
  }

  async function doSubmitRecord(data) {
    const res = await reviewApi.submitReviewRecord(data)
    return res
  }

  async function fetchConsensus(taskId) {
    const res = await reviewApi.getConsensus(taskId)
    return res.data
  }

  async function doSubmitArbitration(data) {
    const res = await reviewApi.doArbitrate(data)
    return res
  }

  async function fetchStats(batchId) {
    const res = await reviewApi.getReviewStats(batchId)
    if (res.code === 200) {
      stats.value = res.data
    }
    return res.data
  }

  return {
    tasks, stats, currentTask, loading,
    doGenerateTasks, fetchTasks, fetchTaskDetail,
    doAssignTask, doSubmitRecord,
    fetchConsensus, doSubmitArbitration,
    fetchStats,
  }
})
