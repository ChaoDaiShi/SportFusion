import request from './index'

export const getMonitoringOverview = (fileId) => request.get(
  '/monitoring/overview',
  { params: fileId ? { file_id: fileId } : {} },
)

export const getRisks = (params = {}) => request.get('/monitoring/risks', { params })

export const getRiskDetail = (riskId, fileId) => request.get(
  `/monitoring/risks/${riskId}`,
  { params: fileId ? { file_id: fileId } : {} },
)
