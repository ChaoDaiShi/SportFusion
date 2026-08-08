<template>
  <div class="sport-share-page">
    <h2 class="page-title">经营比重测算</h2>

    <!-- 概览卡片 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="6">
        <StatCard label="企业总数" :value="stats?.total_enterprises || 0" unit="家" icon="OfficeBuilding" color="#409eff" />
      </el-col>
      <el-col :span="6">
        <StatCard label="已测算数" :value="stats?.estimated_count || 0" unit="家" icon="TrophyBase" color="#67c23a" />
      </el-col>
      <el-col :span="6">
        <StatCard label="平均比重" :value="avgSharePct" unit="%" icon="TrendCharts" color="#e6a23c" />
      </el-col>
      <el-col :span="6">
        <StatCard label="待复核数" :value="pendingReviewCount" unit="家" icon="Warning" color="#f56c6c" />
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <el-card class="section-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="4">
          <el-select v-model="filters.shareBand" placeholder="比重档位" clearable style="width:100%">
            <el-option v-for="(info, key) in bands" :key="key" :label="info.label" :value="key" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filters.category" placeholder="体育业态" clearable style="width:100%">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-input-number v-model="filters.confidenceMin" :min="0" :max="1" :step="0.1" :precision="2" placeholder="最低置信度" style="width:100%" controls-position="right" />
        </el-col>
        <el-col :span="4">
          <el-switch v-model="filters.manualAdjustedOnly" active-text="仅看已校准" style="margin-top:6px" />
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="triggerBatchEstimate" :loading="shareStore.loading">
            批量测算
          </el-button>
        </el-col>
        <el-col :span="4">
          <el-button @click="exportResults" :disabled="!filteredResults.length">
            导出结果
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 主表格 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>SportShare 测算结果</span>
          <el-tag type="info">{{ filteredResults.length }} 条</el-tag>
        </div>
      </template>

      <el-table :data="pagedResults" stripe border style="width:100%" max-height="500"
        @sort-change="handleSortChange">
        <el-table-column prop="enterprise_name" label="企业名称" min-width="180" fixed sortable="custom" />
        <el-table-column prop="industry_code" label="行业代码" width="110" />
        <el-table-column prop="sport_category" label="体育业态" width="110" />
        <el-table-column prop="model_share" label="模型比重" width="100" sortable="custom"
          align="center">
          <template #default="{ row }">
            <span :style="{ color: getShareColor(row.model_share), fontWeight: 'bold' }">
              {{ formatShare(row.model_share) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="share_band_label" label="比重档位" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="getBandTagType(row.share_band)" size="small">
              {{ row.share_band_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预测区间" width="140" align="center">
          <template #default="{ row }">
            <span class="interval-text">
              {{ formatShare(row.lower_bound) }} — {{ formatShare(row.upper_bound) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="model_confidence" label="置信度" width="90" align="center" sortable="custom">
          <template #default="{ row }">
            <el-progress :percentage="Math.round(row.model_confidence * 100)" :stroke-width="6"
              :status="row.model_confidence > 0.8 ? 'success' : row.model_confidence > 0.6 ? '' : 'warning'"
              :show-text="false" style="width:60px;display:inline-block" />
          </template>
        </el-table-column>
        <el-table-column label="人工核定" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.is_manual_adjusted" style="color:#67c23a;font-weight:bold">
              {{ formatShare(row.manual_share) }}
            </span>
            <span v-else style="color:#c0c4cc">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination v-if="filteredResults.length > 0" style="margin-top:16px;justify-content:flex-end"
        v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize"
        :page-sizes="[20, 50, 100]" :total="filteredResults.length" layout="total, sizes, prev, pager, next"
        @current-change="onPageChange" @size-change="onSizeChange" />
    </el-card>

    <!-- 档位分布图 -->
    <el-row :gutter="16" style="margin-bottom:20px" v-if="stats">
      <el-col :span="12">
        <el-card>
          <template #header>比重档位分布</template>
          <PieChart title="" :data="bandPieData" :height="300" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>分业态平均比重</template>
          <BarChart title="" :labels="categoryLabels" :series="categorySeries" yName="平均比重" :height="300" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 企业详情抽屉 -->
    <el-drawer v-model="detailVisible" title="企业 SportShare 详情" size="550px" direction="rtl">
      <template v-if="detailRow">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="企业名称">{{ detailRow.enterprise_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="行业代码">{{ detailRow.industry_code || '—' }}</el-descriptions-item>
          <el-descriptions-item label="体育业态">{{ detailRow.sport_category || '—' }}</el-descriptions-item>
          <el-descriptions-item label="模型比重">
            <span :style="{ color: getShareColor(detailRow.model_share), fontWeight: 'bold', fontSize: '20px' }">
              {{ formatShare(detailRow.model_share) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="比重档位">
            <el-tag :type="getBandTagType(detailRow.share_band)">
              {{ detailRow.share_band_label }}（{{ detailRow.share_band_description }}）
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预测区间">
            {{ formatShare(detailRow.lower_bound) }} — {{ formatShare(detailRow.upper_bound) }}
          </el-descriptions-item>
          <el-descriptions-item label="模型置信度">
            {{ formatShare(detailRow.model_confidence) }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 主要依据 -->
        <div style="margin-top:16px" v-if="detailRow.main_factors?.length">
          <h4 style="margin-bottom:8px">主要依据</h4>
          <el-timeline>
            <el-timeline-item v-for="(factor, idx) in detailRow.main_factors" :key="idx"
              :timestamp="`依据 ${idx + 1}`" placement="top">
              {{ factor }}
            </el-timeline-item>
          </el-timeline>
        </div>

        <!-- 人工校准表单 -->
        <el-divider />
        <h4 style="margin-bottom:12px">人工校准</h4>
        <el-form :model="adjustForm" label-width="100px" size="small">
          <el-form-item label="核定比重">
            <el-slider v-model="adjustForm.manualShare" :min="0" :max="1" :step="0.01"
              show-input :format-tooltip="(v) => formatShare(v)" style="width:100%" />
          </el-form-item>
          <el-form-item label="校准人员">
            <el-input v-model="adjustForm.adjustedBy" placeholder="复核人员姓名" />
          </el-form-item>
          <el-form-item label="校准理由">
            <el-input v-model="adjustForm.reason" type="textarea" :rows="3" placeholder="请说明校准依据..." />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="submitAdjust" :loading="adjusting">提交校准</el-button>
            <el-button @click="adjustForm = getDefaultAdjustForm()">重置</el-button>
          </el-form-item>
        </el-form>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useShareStore } from '../store/share'
import { useDataStore } from '../store/data'
import { useRecognitionStore } from '../store/recognition'
import StatCard from '../components/StatCard.vue'
import PieChart from '../components/PieChart.vue'
import BarChart from '../components/BarChart.vue'

const shareStore = useShareStore()
const dataStore = useDataStore()
const recognitionStore = useRecognitionStore()

// 筛选
const filters = reactive({
  shareBand: '',
  category: '',
  confidenceMin: 0,
  manualAdjustedOnly: false,
})

// 分页
const pagination = reactive({ page: 1, pageSize: 20 })
const sortInfo = ref({ prop: '', order: '' })

// 详情抽屉
const detailVisible = ref(false)
const detailRow = ref(null)
const adjusting = ref(false)
const adjustForm = ref(getDefaultAdjustForm())

function getDefaultAdjustForm() {
  return { manualShare: 0.5, adjustedBy: '', reason: '' }
}

// 业态列表
const categories = computed(() => {
  const cats = new Set()
  shareStore.results.forEach((r) => { if (r.sport_category) cats.add(r.sport_category) })
  return [...cats].sort()
})

// 统计
const stats = computed(() => shareStore.stats)
const avgSharePct = computed(() => {
  if (!stats.value?.avg_share) return 0
  return (stats.value.avg_share * 100).toFixed(1)
})
const pendingReviewCount = computed(() => {
  // 估算：置信度 < 0.7 或比重在边界的企业需要复核
  return shareStore.results.filter(
    (r) => r.model_confidence < 0.7 || r.model_share > 0.05 && r.model_share < 0.15
  ).length
})

// 比重档位
const bands = computed(() => shareStore.bands)

// 筛选结果
const filteredResults = computed(() => {
  let list = shareStore.results
  if (filters.shareBand) list = list.filter((r) => r.share_band === filters.shareBand)
  if (filters.category) list = list.filter((r) => r.sport_category === filters.category)
  if (filters.confidenceMin > 0) list = list.filter((r) => r.model_confidence >= filters.confidenceMin)
  if (filters.manualAdjustedOnly) list = list.filter((r) => r.is_manual_adjusted)
  return list
})

const pagedResults = computed(() => {
  let list = [...filteredResults.value]
  if (sortInfo.value.prop) {
    const dir = sortInfo.value.order === 'ascending' ? 1 : -1
    list.sort((a, b) => (a[sortInfo.value.prop] - b[sortInfo.value.prop]) * dir)
  }
  const start = (pagination.page - 1) * pagination.pageSize
  return list.slice(start, start + pagination.pageSize)
})

// 图表数据
const bandPieData = computed(() => {
  if (!stats.value?.band_distribution) return []
  return Object.entries(stats.value.band_distribution).map(([key, count]) => {
    const bandInfo = bands.value[key] || {}
    return { name: bandInfo.label || key, value: count }
  })
})

const categoryLabels = computed(() => {
  if (!stats.value?.category_avg_share) return []
  return Object.keys(stats.value.category_avg_share)
})
const categorySeries = computed(() => [{
  name: '平均比重',
  data: categoryLabels.value.map((cat) => {
    const v = stats.value.category_avg_share[cat] || 0
    return Math.round(v * 10000) / 100
  }),
  itemStyle: { color: '#409eff' },
}])

// 方法
function formatShare(val) {
  if (val == null || isNaN(val)) return '0%'
  return (val * 100).toFixed(1) + '%'
}

function getShareColor(share) {
  if (share >= 0.75) return '#67c23a'
  if (share >= 0.50) return '#409eff'
  if (share >= 0.30) return '#e6a23c'
  if (share >= 0.10) return '#f56c6c'
  return '#909399'
}

function getBandTagType(band) {
  const map = {
    high: 'success', medium_high: 'primary',
    medium: 'warning', low: 'danger', very_low: 'info',
  }
  return map[band] || 'info'
}

function handleSortChange({ prop, order }) {
  sortInfo.value = { prop, order }
}

function onPageChange(p) { pagination.page = p }
function onSizeChange(s) { pagination.pageSize = s; pagination.page = 1 }

async function triggerBatchEstimate() {
  const fileId = dataStore.queryParams.fileId
  if (!fileId) { ElMessage.warning('请先在数据管理中上传数据'); return }

  try {
    // 先获取预处理数据，再识别，再估计比重
    const res = await dataStore.fetchPreprocessResult(fileId)
    if (!res || !res.data) { ElMessage.warning('请先执行NLP预处理'); return }

    // 获取体育企业数据
    const sportRes = await dataStore.fetchSportEnterprises(fileId,
      { page: 1, page_size: 10000 })
    if (sportRes.code !== 200) { ElMessage.warning('获取体育企业数据失败'); return }

    const records = sportRes.data?.records || []
    if (!records.length) { ElMessage.warning('未发现体育企业'); return }

    // 构建识别请求
    const enterprises = records.map((r) => ({
      enterprise_id: r.id,
      enterprise_name: r['详细名称'] || r.name || '',
      credit_code: r['统一社会信用代码'] || r.credit_code || '',
      industry_code: r['行业代码'] || r.industry_code || '',
      business_text: r['主要业务活动'] || r.main_business || '',
    }))

    // 先批量识别
    const recRes = await recognitionStore.recognizeBatch(enterprises)
    if (!recRes || !recRes.results) { ElMessage.error('识别失败'); return }

    // 再批量估计比重
    await shareStore.estimateBatch(recRes.results)
    ElMessage.success(`SportShare 测算完成，共 ${shareStore.results.length} 家企业`)
  } catch (e) {
    ElMessage.error('测算失败: ' + (e.message || '未知错误'))
  }
}

function openDetail(row) {
  detailRow.value = row
  adjustForm.value = getDefaultAdjustForm()
  adjustForm.value.manualShare = row.manual_share || row.model_share || 0.5
  detailVisible.value = true
}

async function submitAdjust() {
  if (!adjustForm.value.adjustedBy) { ElMessage.warning('请输入校准人员'); return }
  adjusting.value = true
  try {
    await shareStore.doManualAdjust({
      share_result_id: detailRow.value.enterprise_id || 0,
      manual_share: adjustForm.value.manualShare,
      adjusted_by: adjustForm.value.adjustedBy,
      reason: adjustForm.value.reason,
    })
    ElMessage.success('人工校准已提交')
    detailVisible.value = false
  } catch (e) {
    ElMessage.error('校准提交失败')
  } finally {
    adjusting.value = false
  }
}

function exportResults() {
  const { exportCSV } = require('../utils/format')
  const data = filteredResults.value.map((r) => ({
    企业名称: r.enterprise_name,
    行业代码: r.industry_code,
    体育业态: r.sport_category,
    模型比重: r.model_share,
    比重档位: r.share_band_label,
    预测下限: r.lower_bound,
    预测上限: r.upper_bound,
    置信度: r.model_confidence,
    人工核定: r.manual_share || '',
  }))
  exportCSV(data, `SportShare_测算结果_${new Date().toISOString().slice(0, 10)}.csv`)
}

onMounted(async () => {
  await shareStore.fetchBands()
})
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 20px; color: #303133; }
.section-card { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.interval-text { color: #909399; font-size: 13px; font-family: monospace; }
</style>
