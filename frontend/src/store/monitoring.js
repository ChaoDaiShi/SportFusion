import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getMonitoringOverview } from '../api/monitoring'
import {
  readCachedSnapshot,
  resolveSnapshot,
  writeCachedSnapshot,
} from '../features/monitoring/data-policy'
import { useAnalysisContextStore } from './analysis-context'

const demoSnapshot = {
  pipeline: [
    { id: 'data', label: '企业数据治理', description: '清洗、分词、标签' },
    { id: 'recognition', label: '业务边界识别', description: '类型与置信度' },
    { id: 'ratio', label: '经营比重测算', description: '多维加权模型' },
    { id: 'scale', label: '产业规模估算', description: '区域与分业态产出' },
    { id: 'decision', label: '验证与决策', description: '性能、风险、建议' },
  ],
  metrics: [
    { id: 'sport_enterprises', label: '识别体育企业', value: 8950, unit: '家', tone: 'teal', note: '其中跨界经营 977 家' },
    { id: 'output_index', label: '体育产业总产出指数', value: 579124.95, unit: '', tone: 'red', note: '按企业体育业务比重加权' },
    { id: 'method_gap', label: '传统方法低估差异', value: 18.7, unit: '%', tone: 'yellow', note: '演示对比口径' },
    { id: 'model_accuracy', label: '模型综合一致率', value: 91.6, unit: '%', tone: 'blue', note: '异常输入通过率 96.2%' },
  ],
  method_comparison: { traditional: 486900, model: 579124.95, gap_percent: 18.7 },
  regions: [
    { name: '成都市', value: 237694.59 },
    { name: '绵阳市', value: 13636 },
    { name: '宜宾市', value: 11993.47 },
    { name: '泸州市', value: 11251.82 },
  ],
  trend: { labels: [], series: [] },
  risks: [
    {
      id: 'R-2025-071', title: '成都健身服务市场集中度异常', type: 'industry_structure', level: 'high', status: 'analyzing', score: 89, confidence: 0.93, region: '成都市', category: '健身休闲', deviation_score: 91, impact_score: 84, evidence_score: 93, enterprise_ids: [], evidence: ['CR3 升至 77.3%，超过 60% 预警阈值', '头部区域产出占比继续上升'],
    },
    {
      id: 'R-2025-062', title: '企业业务边界识别置信度偏低', type: 'enterprise_boundary', level: 'medium', status: 'pending_verification', score: 76, confidence: 0.81, region: '绵阳市', category: '健身休闲', deviation_score: 74, impact_score: 69, evidence_score: 81, enterprise_ids: ['DEMO-001', 'DEMO-002'], evidence: ['18 家企业置信度低于 0.60'],
    },
    {
      id: 'R-2025-055', title: '区域样本缺失率连续升高', type: 'data_quality', level: 'medium', status: 'pending_action', score: 69, confidence: 0.88, region: '宜宾市', category: '', deviation_score: 70, impact_score: 58, evidence_score: 88, enterprise_ids: [], evidence: ['主要业务活动缺失率连续两期升高'],
    },
    {
      id: 'R-2025-043', title: '模型结果较基线发生轻微漂移', type: 'model_performance', level: 'watch', status: 'monitoring', score: 54, confidence: 0.90, region: '德阳市', category: '', deviation_score: 48, impact_score: 42, evidence_score: 90, enterprise_ids: [], evidence: ['低置信度样本占比上升 2.1 个百分点'],
    },
  ],
  model_metrics: {
    accuracy: 0.916,
    precision: 0.928,
    recall: 0.904,
    mae: 0.083,
    normal_input_pass_rate: 0.916,
    missing_text_pass_rate: 0.962,
    noise_input_pass_rate: 0.947,
    runtime_seconds_per_10k: 8.7,
    peak_memory_mb: 486,
  },
  provenance: {
    mode: 'demo',
    dataset_id: 'sichuan-enterprises-2025',
    data_version: '2025.07',
    model_version: 'V3.2',
    updated_at: '2026-08-01T18:20:00+08:00',
    is_complete: true,
    missing_fields: [],
  },
}

export const useMonitoringStore = defineStore('monitoring', () => {
  const snapshot = ref(demoSnapshot)
  const loading = ref(false)
  const error = ref('')
  const selectedRisk = ref(null)

  async function refresh(fileId) {
    loading.value = true
    error.value = ''
    let remote = null
    try {
      const response = await getMonitoringOverview(fileId)
      remote = response.code === 200 ? response.data : null
      writeCachedSnapshot(remote)
    } catch (requestError) {
      error.value = requestError.message || '监测接口暂不可用，已切换到可用快照'
    } finally {
      snapshot.value = resolveSnapshot({
        remote,
        cached: readCachedSnapshot(),
        demo: demoSnapshot,
      })
      const contextStore = useAnalysisContextStore()
      contextStore.patch({
        fileId: fileId || null,
        dataVersion: snapshot.value.provenance.data_version,
        modelVersion: snapshot.value.provenance.model_version,
      })
      loading.value = false
    }
  }

  const selectRisk = (risk) => { selectedRisk.value = risk }
  const clearRisk = () => { selectedRisk.value = null }

  return {
    snapshot,
    loading,
    error,
    selectedRisk,
    refresh,
    selectRisk,
    clearRisk,
  }
})
