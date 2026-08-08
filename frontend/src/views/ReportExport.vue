<template>
  <div class="page-shell report-export">
    <header class="page-heading">
      <div><h1>报告与成果中心</h1><p>核对数据来源后生成研究报告、政策建议和标准化数据集</p></div>
      <DataModeBadge :provenance="snapshot.provenance" />
    </header>

    <!-- 数据集导出 -->
    <el-card class="section-card">
      <template #header><span>标准化数据集导出</span></template>
      <p class="section-desc">导出经过清洗、分词、体育标签标注的标准化企业数据集（76,687家企业）。</p>
      <el-row :gutter="16">
        <el-col :span="8">
          <el-card shadow="hover" class="download-card">
            <div class="card-icon"><el-icon :size="36" color="#409eff"><Document /></el-icon></div>
            <h4>完整数据集 (CSV)</h4>
            <p>含全部76,687家企业及NLP预处理结果</p>
            <el-button type="primary" plain @click="requestDownload('enterprise_dataset')">下载 CSV</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="download-card">
            <div class="card-icon"><el-icon :size="36" color="#67c23a"><DataAnalysis /></el-icon></div>
            <h4>体育企业子集 (CSV)</h4>
            <p>8,950家体育企业业务边界+比重明细</p>
            <el-button type="success" plain @click="requestDownload('sport_enterprises')">下载 CSV</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="download-card">
            <div class="card-icon"><el-icon :size="36" color="#e6a23c"><FolderOpened /></el-icon></div>
            <h4>特征数据集 (CSV)</h4>
            <p>体育业务特征指标：占比、置信度、词命中数等</p>
            <el-button type="warning" plain @click="requestDownload('features')">下载 CSV</el-button>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 分析报告导出 -->
    <el-card class="section-card">
      <template #header><span>分析报告导出</span></template>
      <p class="section-desc">基于全量数据分析生成的研究报告和统计文档。</p>
      <el-row :gutter="16">
        <el-col :span="8">
          <el-card shadow="hover" class="download-card">
            <div class="card-icon"><el-icon :size="36" color="#409eff"><Notebook /></el-icon></div>
            <h4>完整研究报告</h4>
            <p>含背景、方法、实证、政策建议全章节</p>
            <el-button type="primary" plain @click="requestDownload('final_report')">下载 MD</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="download-card">
            <div class="card-icon"><el-icon :size="36" color="#e6a23c"><Setting /></el-icon></div>
            <h4>统计方法优化方案</h4>
            <p>三层融合统计体系 + 技术路径</p>
            <el-button type="warning" plain @click="requestDownload('optimization')">下载 MD</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="download-card">
            <div class="card-icon"><el-icon :size="36" color="#67c23a"><Guide /></el-icon></div>
            <h4>结构化政策建议</h4>
            <p>5大建议 + 实施路线图 (JSON)</p>
            <el-button type="success" plain @click="requestDownload('policy')">下载 JSON</el-button>
          </el-card>
        </el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:16px">
        <el-col :span="8">
          <el-card shadow="hover" class="download-card">
            <div class="card-icon"><el-icon :size="36" color="#909399"><InfoFilled /></el-icon></div>
            <h4>数据文档说明</h4>
            <p>字段含义、清洗规则、统计口径</p>
            <el-button plain @click="requestDownload('data_doc')">下载 MD</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="download-card">
            <div class="card-icon"><el-icon :size="36" color="#409eff"><TrendCharts /></el-icon></div>
            <h4>产业分析报告 (JSON)</h4>
            <p>区域/业态/结构全维度分析数据</p>
            <el-button type="primary" plain @click="requestDownload('industry_analysis')">下载 JSON</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="download-card">
            <div class="card-icon"><el-icon :size="36" color="#67c23a"><Checked /></el-icon></div>
            <h4>模型验证报告</h4>
            <p>传统法 vs 模型法对比验证</p>
            <el-button type="success" plain @click="requestDownload('model_validation')">下载 JSON</el-button>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 在线预览摘要（含仪表盘） -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>分析摘要预览</span>
          <el-button size="small" @click="loadSummary">刷新数据</el-button>
        </div>
      </template>

      <!-- 3个迷你仪表盘 -->
      <el-row :gutter="16" style="margin-bottom:16px">
        <el-col :span="8">
          <GaugeChart title="体育企业占比" :value="summary.sport_ratio_pct || 0" :max="100" unit="%" color="#409eff" :height="180" />
        </el-col>
        <el-col :span="8">
          <GaugeChart title="CR3市场集中度" :value="concentration.cr3_pct || 0" :max="100" unit="%" color="#e6a23c" :height="180" />
        </el-col>
        <el-col :span="8">
          <GaugeChart title="产业多样性" :value="(structure.diversity_index || 0) * 100" :max="100" unit="" color="#67c23a" :height="180" />
        </el-col>
      </el-row>

      <!-- 详细统计 -->
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="summary-block">
            <h4>产业概况</h4>
            <div class="summary-item"><span>企业总数</span><b>{{ summary.total_enterprises?.toLocaleString() || '—' }}</b></div>
            <div class="summary-item"><span>体育企业</span><b>{{ summary.sport_enterprises?.toLocaleString() || '—' }} ({{ summary.sport_ratio_pct }}%)</b></div>
            <div class="summary-item"><span>跨界经营</span><b>{{ summary.crossover_count?.toLocaleString() || '—' }}</b></div>
            <div class="summary-item"><span>总产出指数</span><b>{{ summary.total_output_index?.toLocaleString() || '—' }}</b></div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="summary-block">
            <h4>空间分布</h4>
            <div class="summary-item"><span>CR3集中度</span><b>{{ concentration.cr3_pct || '—' }}%</b></div>
            <div class="summary-item"><span>HHI指数</span><b>{{ concentration.hhi || '—' }}</b></div>
            <div class="summary-item"><span>基尼系数</span><b>{{ concentration.gini || '—' }}</b></div>
            <div class="summary-item"><span>覆盖区域</span><b>{{ concentration.total_regions || '—' }}</b></div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="summary-block">
            <h4>产业结构</h4>
            <div class="summary-item"><span>多样性指数</span><b>{{ structure.diversity_index || '—' }}</b></div>
            <div class="summary-item"><span>主导业态</span><b>{{ structure.dominant_category?.name || '—' }}</b></div>
            <div class="summary-item"><span>跨界经营率</span><b>{{ structure.crossover_rate_pct || '—' }}%</b></div>
            <div class="summary-item"><span>均衡度</span><b>{{ structure.balance_assessment || '—' }}</b></div>
          </div>
        </el-col>
      </el-row>
      <el-divider />
      <div class="conclusion-text">{{ concentration.conclusion || '加载中...' }}</div>
    </el-card>

    <el-dialog v-model="confirmVisible" title="确认生成并下载" width="480px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="成果类型">{{ reportLabels[pendingType] || pendingType }}</el-descriptions-item>
        <el-descriptions-item label="数据文件">{{ dataStore.queryParams.fileId || '未选择' }}</el-descriptions-item>
        <el-descriptions-item label="数据状态"><DataModeBadge :provenance="snapshot.provenance" /></el-descriptions-item>
        <el-descriptions-item label="数据版本">{{ snapshot.provenance.data_version }}</el-descriptions-item>
      </el-descriptions>
      <template #footer><el-button @click="confirmVisible = false">取消</el-button><el-button type="warning" @click="confirmDownload">确认下载</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import GaugeChart from '../components/GaugeChart.vue'
import DataModeBadge from '../components/common/DataModeBadge.vue'
import { getDashboardData, getAnalysisReport } from '../api/chart'
import { useDataStore } from '../store/data'
import { useMonitoringStore } from '../store/monitoring'

const summary = ref({})
const concentration = ref({})
const structure = ref({})
const confirmVisible = ref(false)
const pendingType = ref('')

const dataStore = useDataStore()
const monitoring = useMonitoringStore()
const { snapshot } = storeToRefs(monitoring)
const reportLabels = {
  enterprise_dataset: '完整企业数据集',
  sport_enterprises: '体育企业子集',
  features: '特征数据集',
  final_report: '完整研究报告',
  optimization: '统计方法优化方案',
  policy: '结构化政策建议',
  data_doc: '数据文档说明',
  industry_analysis: '产业分析报告',
  model_validation: '模型验证报告',
}

onMounted(async () => {
  await Promise.all([
    loadSummary(),
    monitoring.refresh(dataStore.queryParams.fileId),
  ])
})

async function loadSummary() {
  try {
    const [dashRes, reportRes] = await Promise.all([
      getDashboardData(dataStore.queryParams.fileId),
      getAnalysisReport(dataStore.queryParams.fileId),
    ])
    if (dashRes?.data?.overview) {
      const ov = dashRes.data.overview
      summary.value = {
        total_enterprises: ov.total_enterprises,
        sport_enterprises: ov.sport_enterprises,
        sport_ratio_pct: ov.avg_sport_ratio_pct,
        crossover_count: ov.crossover_count,
        total_output_index: ov.total_output_index,
      }
      concentration.value = dashRes.data.concentration || {}
      structure.value = dashRes.data.structure || {}
    }
    if (reportRes?.data) {
      const r = reportRes.data
      if (r.spatial_concentration) concentration.value = r.spatial_concentration
      if (r.structure) structure.value = r.structure
    }
  } catch {
    // Demo data
    summary.value = {
      total_enterprises: 76687, sport_enterprises: 8950,
      sport_ratio_pct: 64.71, crossover_count: 977, total_output_index: 579125,
    }
    concentration.value = {
      cr3_pct: 67.9, hhi: 2132.5, gini: 0.9005, total_regions: 50,
      conclusion: '高度集中：前3名区域占据67.9%的体育产出，呈现明显的中心-外围结构',
    }
    structure.value = {
      diversity_index: 0.76, crossover_rate_pct: 10.92,
      dominant_category: { name: '体育用品', share_pct: 29.69 },
      balance_assessment: '业态较为多元，存在主导业态',
    }
  }
}

function requestDownload(type) {
  if (!dataStore.queryParams.fileId) {
    ElMessage.warning('请先在数据管理页面上传并处理数据')
    return
  }
  pendingType.value = type
  confirmVisible.value = true
}

function confirmDownload() {
  const type = pendingType.value
  confirmVisible.value = false
  pendingType.value = ''
  downloadFile(type)
}

function downloadFile(type) {
  const fileId = dataStore.queryParams.fileId
  if (!fileId) {
    ElMessage.warning('请先在数据管理页面上传并处理数据')
    return
  }
  const fileMap = {
    enterprise_dataset: `/api/data/export/${fileId}?format=csv`,
    sport_enterprises: `/api/data/export-sport/${fileId}?format=csv`,
    features: `/api/data/export-features/${fileId}?format=csv`,
    final_report: `/api/chart/export/report/final_report?file_id=${fileId}`,
    optimization: `/api/chart/export/report/optimization?file_id=${fileId}`,
    policy: `/api/chart/export/report/policy?file_id=${fileId}`,
    data_doc: `/api/chart/export/report/data_doc?file_id=${fileId}`,
    industry_analysis: `/api/chart/export/report/industry_analysis?file_id=${fileId}`,
    model_validation: `/api/chart/export/report/model_validation?file_id=${fileId}`,
  }
  const url = fileMap[type]
  if (!url) {
    ElMessage.error('不支持的下载类型')
    return
  }
  const link = document.createElement('a')
  link.href = url
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success('下载已开始')
}
</script>

<style scoped>
.section-card { margin-bottom: 16px; border-color: var(--sf-line); background: var(--sf-surface); }
.section-desc { color: #909399; font-size: 13px; margin-bottom: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.download-card { text-align: center; padding: 12px 0; }
.card-icon { margin-bottom: 10px; }
.download-card h4 { font-size: 15px; margin-bottom: 6px; }
.download-card p { color: #909399; font-size: 12px; margin-bottom: 14px; }
.summary-block { background: var(--sf-surface-muted); border-radius: 8px; padding: 16px; }
.summary-block h4 { font-size: 14px; color: #303133; margin-bottom: 10px; border-bottom: 1px solid #e4e7ed; padding-bottom: 6px; }
.summary-item { display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; }
.summary-item span { color: #909399; }
.summary-item b { color: #303133; }
.conclusion-text { font-size: 13px; color: var(--sf-text); background: #e8ecfa; padding: 10px 14px; border-radius: 6px; }
</style>
