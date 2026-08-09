<template>
  <div class="scale-analysis-page">
    <h2 class="page-title">产业规模测算 (Macro-Calibrated)</h2>

    <!-- Official total constraint -->
    <el-alert type="success" :closable="false" show-icon style="margin-bottom:12px">
      <template #title>
        官方总量约束：四川省 2022 年体育产业总产出 <strong>2,170.80 亿元</strong>
        &nbsp;|&nbsp; 宏观校准版本：OFFICIAL-TOTALS-2026-08
      </template>
      正式规模采用宏观结构分配法。企业营业收入 × SportShare 的旧路径已标记为 legacy，不再作为正式规模结果。
    </el-alert>

    <!-- ±15% deprecated warning -->
    <el-alert type="warning" :closable="false" show-icon style="margin-bottom:12px">
      <template #title>固定 ±15% 区间已弃用</template>
      下方估算区间来自 Phase 3 残差分位数方法或旧兼容路径。正式区间应基于模型残差分布 (q_0.90) 或 12 情景变异。
    </el-alert>

    <!-- 口径标签 -->
    <el-alert v-if="scaleStore.summary" type="info" :closable="false" show-icon style="margin-bottom:20px">
      <template #title>
        <span style="font-weight:600">
          当前测算口径：{{ scaleStore.summary.type_summary?.dominant_label || '—' }}
        </span>
        <span style="margin-left:16px;color:#909399">
          数据覆盖率：{{ scaleStore.summary.type_summary?.coverage_rate || 0 }}%（
          正式测算 {{ scaleStore.summary.type_summary?.formal_count || 0 }} 家 |
          代理估算 {{ scaleStore.summary.type_summary?.proxy_count || 0 }} 家 |
          相对指数 {{ scaleStore.summary.type_summary?.relative_count || 0 }} 家）
        </span>
      </template>
    </el-alert>

    <!-- 总览卡片 -->
    <el-row :gutter="16" style="margin-bottom:20px" v-if="scaleStore.summary">
      <el-col :span="6">
        <StatCard label="体育产业估算规模" :value="totalScaleDisplay" unit="万元"
          icon="Coin" color="#e6a23c" format="number" />
      </el-col>
      <el-col :span="6">
        <StatCard label="估计区间下限" :value="formatAmount(scaleStore.summary.lower_bound)" unit="万元"
          icon="Bottom" color="#409eff" />
      </el-col>
      <el-col :span="6">
        <StatCard label="估计区间上限" :value="formatAmount(scaleStore.summary.upper_bound)" unit="万元"
          icon="Top" color="#409eff" />
      </el-col>
      <el-col :span="6">
        <StatCard label="覆盖企业数" :value="scaleStore.summary.enterprise_count" unit="家"
          icon="OfficeBuilding" color="#67c23a" />
      </el-col>
    </el-row>

    <!-- 方法对比 -->
    <el-row :gutter="16" style="margin-bottom:20px" v-if="scaleStore.comparison">
      <el-col :span="12">
        <el-card>
          <template #header>传统代码法 vs SportFusion 融合测算</template>
          <div style="padding:8px">
            <el-row :gutter="16">
              <el-col :span="12">
                <div class="method-box traditional">
                  <div class="method-label">传统代码法</div>
                  <div class="method-value">{{ formatAmount(scaleStore.comparison.traditional?.scale) }} 万元</div>
                  <div class="method-desc">{{ scaleStore.comparison.traditional?.enterprise_count }} 家企业</div>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="method-box fusion">
                  <div class="method-label">SportFusion</div>
                  <div class="method-value">{{ formatAmount(scaleStore.comparison.fusion?.scale) }} 万元</div>
                  <div class="method-desc">{{ scaleStore.comparison.fusion?.enterprise_count }} 家企业</div>
                </div>
              </el-col>
            </el-row>
            <div style="text-align:center;margin-top:16px">
              <el-tag type="success" size="large">
                增量规模：+{{ formatAmount(scaleStore.comparison.incremental_scale) }} 万元
                （+{{ scaleStore.comparison.incremental_pct }}%）
              </el-tag>
              <div style="margin-top:8px;color:#909399">
                新增识别 {{ scaleStore.comparison.new_enterprises }} 家跨界经营企业
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>分业态规模</template>
          <PieChart title="" :data="categoryPieData" :height="300" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 分业态规模表 -->
    <el-card class="section-card" v-if="scaleStore.category.length">
      <template #header>九类业态规模明细</template>
      <el-table :data="scaleStore.category" stripe border size="small">
        <el-table-column prop="category" label="体育业态" width="120" />
        <el-table-column prop="enterprise_count" label="企业数" width="100" align="center" sortable />
        <el-table-column prop="estimated_scale" label="估算规模（万元）" sortable>
          <template #default="{ row }">
            <span style="font-weight:600">{{ formatAmount(row.estimated_scale) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="share_pct" label="占比" width="120" align="center" sortable>
          <template #default="{ row }">
            <el-progress :percentage="row.share_pct" :stroke-width="12" :show-text="true" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 区域规模 -->
    <el-card class="section-card" v-if="scaleStore.regional.length">
      <template #header>
        <div class="card-header">
          <span>区域规模分布</span>
          <el-button size="small" @click="loadRegional">刷新</el-button>
        </div>
      </template>
      <el-table :data="scaleStore.regional.slice(0, 10)" stripe border size="small" max-height="400">
        <el-table-column prop="region" label="区域" width="120" />
        <el-table-column prop="sport_enterprises" label="体育企业数" width="110" align="center" />
        <el-table-column prop="estimated_scale" label="估算规模（万元）" sortable>
          <template #default="{ row }">
            {{ formatAmount(row.estimated_scale) }}
          </template>
        </el-table-column>
        <el-table-column prop="dominant_category" label="主导业态" width="110" />
        <el-table-column prop="crossover_rate" label="跨界率" width="100" align="center">
          <template #default="{ row }">
            {{ (row.crossover_rate * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="new_candidates" label="新增候选" width="100" align="center" />
      </el-table>
    </el-card>

    <!-- 测算按钮 -->
    <div v-if="!scaleStore.summary" style="text-align:center;padding:60px">
      <el-empty description="暂未执行规模测算">
        <el-button type="primary" @click="showCalculateDialog = true" :loading="scaleStore.loading">
          开始测算
        </el-button>
      </el-empty>
    </div>
    <div v-else style="text-align:center;padding:20px">
      <el-button type="primary" @click="showCalculateDialog = true" :loading="scaleStore.loading">
        重新测算
      </el-button>
    </div>

    <!-- 测算配置对话框 -->
    <el-dialog v-model="showCalculateDialog" title="规模测算配置" width="500px">
      <el-form label-width="120px">
        <el-form-item label="规模字段">
          <el-select v-model="calcConfig.preferredField" placeholder="自动选择" style="width:100%">
            <el-option label="自动选择（推荐）" value="auto" />
            <el-option v-for="f in scaleStore.fields" :key="f.key"
              :label="`${f.label} (${f.measurement_label})`" :value="f.key"
              :disabled="f.key === 'relative_index'" />
          </el-select>
          <div style="color:#909399;font-size:12px;margin-top:4px">
            自动选择按优先级：营业收入 > 从业人数 > 资产总额 > 注册资本
          </div>
        </el-form-item>
        <el-form-item label="数据来源">
          <el-radio-group v-model="calcConfig.dataSource">
            <el-radio value="uploaded">已上传数据</el-radio>
            <el-radio value="demo">演示数据</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCalculateDialog = false">取消</el-button>
        <el-button type="primary" @click="runCalculate" :loading="scaleStore.loading">
          执行测算
        </el-button>
      </template>
    </el-dialog>

    <ProvenancePanel v-if="scaleStore.summary" :provenance="{
      macro_calibration_version: 'OFFICIAL-TOTALS-2026-08',
      scenario_version: 'SCENARIO-2026-08',
      sportshare_model_version: 'SPORTSHARE-RF-2026-08',
    }" />
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import ProvenancePanel from '../components/ProvenancePanel.vue'
import { ElMessage } from 'element-plus'
import { useScaleStore } from '../store/scale'
import { useDataStore } from '../store/data'
import { useRecognitionStore } from '../store/recognition'
import { useShareStore } from '../store/share'
import StatCard from '../components/StatCard.vue'
import PieChart from '../components/PieChart.vue'

const scaleStore = useScaleStore()
const dataStore = useDataStore()
const recognitionStore = useRecognitionStore()
const shareStore = useShareStore()

const showCalculateDialog = ref(false)
const calcConfig = reactive({
  preferredField: 'auto',
  dataSource: 'uploaded',
})

const totalScaleDisplay = computed(() => {
  if (!scaleStore.summary?.total_estimated_scale) return '—'
  return scaleStore.formatAmount(scaleStore.summary.total_estimated_scale)
})

const categoryPieData = computed(() =>
  scaleStore.category.map((c) => ({
    name: c.category,
    value: c.estimated_scale || 0,
  }))
)

function formatAmount(val) {
  return scaleStore.formatAmount(val)
}

async function runCalculate() {
  if (calcConfig.dataSource === 'demo') {
    await runDemoCalculate()
    return
  }

  const fileId = dataStore.queryParams.fileId
  if (!fileId) { ElMessage.warning('请先在数据管理中上传数据'); return }

  try {
    // 获取预处理数据
    await dataStore.fetchPreprocessResult(fileId)
    const sportRes = await dataStore.fetchSportEnterprises(fileId, { page: 1, page_size: 10000 })
    if (sportRes.code !== 200) { ElMessage.warning('获取数据失败'); return }

    const records = sportRes.data?.records || []
    if (!records.length) { ElMessage.warning('未发现体育企业'); return }

    // 构建企业数据
    const enterprises = records.map((r) => ({
      id: r.id,
      name: r['详细名称'] || r.name || '',
      credit_code: r['统一社会信用代码'] || r.credit_code || '',
      industry_code: r['行业代码'] || r.industry_code || '',
      main_business: r['主要业务活动'] || r.main_business || '',
      total_revenue: r['营业收入'] || r.total_revenue || 0,
      employee_count: r['从业人数'] || r.employee_count || 0,
      business_text: r['主要业务活动'] || r.main_business || '',
    }))

    // 批量识别
    const recRes = await recognitionStore.recognizeBatch(
      enterprises.map((e) => ({
        enterprise_id: e.id,
        enterprise_name: e.name,
        industry_code: e.industry_code,
        business_text: e.business_text,
      }))
    )

    if (!recRes?.results) { ElMessage.error('识别失败'); return }

    // 批量估计比重
    await shareStore.estimateBatch(recRes.results)

    // 规模测算
    await scaleStore.doCalculate({
      enterprises,
      share_results: shareStore.results,
      preferred_field: calcConfig.preferredField,
    })

    await scaleStore.fetchRegional(scaleStore.cacheKey)

    ElMessage.success('规模测算完成')
    showCalculateDialog.value = false
  } catch (e) {
    ElMessage.error('测算失败: ' + (e.message || '未知错误'))
  }
}

async function runDemoCalculate() {
  // 演示数据
  const demoSummary = {
    total_estimated_scale: 1285000,
    lower_bound: 1102000,
    upper_bound: 1468000,
    enterprise_count: 6452,
    type_summary: {
      dominant_type: 'formal',
      dominant_label: '正式收入测算',
      coverage_rate: 72.1,
      formal_count: 4650,
      proxy_count: 1250,
      relative_count: 552,
      total_count: 6452,
    },
    category: [
      { category: '健身休闲', enterprise_count: 2230, estimated_scale: 356000, share_pct: 27.7 },
      { category: '体育用品', enterprise_count: 1780, estimated_scale: 298000, share_pct: 23.2 },
      { category: '体育赛事', enterprise_count: 980, estimated_scale: 245000, share_pct: 19.1 },
      { category: '体育培训', enterprise_count: 720, estimated_scale: 186000, share_pct: 14.5 },
      { category: '体育场馆', enterprise_count: 380, estimated_scale: 98000, share_pct: 7.6 },
      { category: '体育管理', enterprise_count: 210, estimated_scale: 52000, share_pct: 4.0 },
      { category: '体育传媒', enterprise_count: 85, estimated_scale: 28000, share_pct: 2.2 },
      { category: '电子竞技', enterprise_count: 47, estimated_scale: 15000, share_pct: 1.2 },
      { category: '体育彩票', enterprise_count: 20, estimated_scale: 7000, share_pct: 0.5 },
    ],
    comparison: {
      traditional: { scale: 892000, enterprise_count: 4210, method: '传统代码法' },
      fusion: { scale: 1285000, enterprise_count: 6452, method: 'SportFusion 融合测算法' },
      incremental_scale: 393000,
      incremental_pct: 44.1,
      new_enterprises: 2242,
    },
  }

  scaleStore.summary = demoSummary
  scaleStore.category = demoSummary.category
  scaleStore.comparison = demoSummary.comparison
  scaleStore.regional = [
    { region: '成都市', sport_enterprises: 2230, estimated_scale: 398000, dominant_category: '赛事运营', crossover_rate: 0.128, new_candidates: 520 },
    { region: '绵阳市', sport_enterprises: 380, estimated_scale: 52000, dominant_category: '体育用品', crossover_rate: 0.095, new_candidates: 85 },
    { region: '宜宾市', sport_enterprises: 290, estimated_scale: 38000, dominant_category: '健身休闲', crossover_rate: 0.082, new_candidates: 60 },
    { region: '乐山市', sport_enterprises: 260, estimated_scale: 32000, dominant_category: '体育旅游', crossover_rate: 0.075, new_candidates: 50 },
    { region: '泸州市', sport_enterprises: 220, estimated_scale: 28000, dominant_category: '体育培训', crossover_rate: 0.068, new_candidates: 45 },
  ]

  ElMessage.success('演示数据已加载')
  showCalculateDialog.value = false
}

async function loadRegional() {
  await scaleStore.fetchRegional()
}

onMounted(async () => {
  await scaleStore.fetchFields()
})
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 20px; color: #303133; }
.section-card { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.method-box {
  text-align: center; padding: 20px; border-radius: 8px;
}
.method-box.traditional { background: #f5f7fa; border: 1px solid #e4e7ed; }
.method-box.fusion { background: #ecf5ff; border: 1px solid #d9ecff; }
.method-label { font-size: 13px; color: #909399; margin-bottom: 8px; }
.method-value { font-size: 20px; font-weight: 700; color: #303133; }
.method-desc { font-size: 12px; color: #909399; margin-top: 4px; }
</style>
