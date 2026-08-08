import { defineStore } from 'pinia'
import { reactive } from 'vue'

export const useAnalysisContextStore = defineStore('analysis-context', () => {
  const context = reactive({
    fileId: null,
    region: '四川省',
    year: '2025',
    category: '',
    riskType: '',
    riskLevel: '',
    selectedEnterpriseIds: [],
    selectedRiskId: '',
    dataVersion: '',
    modelVersion: '',
  })

  const patch = (value) => Object.assign(context, value)
  const clearSelection = () => Object.assign(context, {
    category: '',
    riskType: '',
    riskLevel: '',
    selectedEnterpriseIds: [],
    selectedRiskId: '',
  })

  return { context, patch, clearSelection }
})
