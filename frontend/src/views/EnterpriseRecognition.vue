<template>
  <div class="enterprise-recognition">
    <h2 class="page-title">企业业务识别</h2>

    <!-- 单条识别 -->
    <el-card class="section-card">
      <template #header><span>单条企业识别（v2.0 业务边界 + 比重测算）</span></template>
      <el-form :model="singleForm" label-width="100px">
        <el-form-item label="企业名称">
          <el-input v-model="singleForm.enterprise_name" placeholder="输入企业名称" style="width:300px" />
        </el-form-item>
        <el-form-item label="主营业务描述">
          <el-input v-model="singleForm.business_text" type="textarea" :rows="3"
            placeholder="输入企业主营业务描述文本，如：主要从事体育赛事运营、运动器材销售等" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="doSingleRecognition" :loading="recogStore.loading">识别</el-button>
        </el-form-item>
      </el-form>

      <!-- 识别结果 + 特征雷达图 -->
      <div v-if="singleResult" class="result-area">
        <el-row :gutter="16">
          <!-- 左侧：详细结果 -->
          <el-col :span="14">
            <el-card :body-style="{ padding: '16px' }">
              <div class="result-header">
                <span class="result-enterprise">{{ singleResult.enterprise_name || '未命名企业' }}</span>
                <el-tag :type="singleResult.sport_category === '非体育' ? 'info' : 'success'" size="large">
                  {{ singleResult.sport_category }}
                </el-tag>
              </div>
              <el-descriptions :column="3" border style="margin-top:12px">
                <el-descriptions-item label="置信度">{{ (singleResult.confidence * 100).toFixed(1) }}%</el-descriptions-item>
                <el-descriptions-item label="SportScore">
                  {{ (singleResult.sport_score != null ? singleResult.sport_score * 100 : (singleResult.sport_ratio || 0) * 100).toFixed(1) }}%
                  <el-tooltip content="体育业务证据评分，用于衡量体育业务证据强度，不表示营业收入占比" placement="top">
                    <el-icon style="margin-left:4px;cursor:help"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </el-descriptions-item>
                <el-descriptions-item label="候选状态">
                  <el-tag :type="singleResult.is_sport ? 'success' : 'info'" size="small">
                    {{ singleResult.is_sport ? '体育相关候选企业' : '非体育企业' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="行业代码关系">
                  {{ singleResult.code_type === 'direct' ? '直接体育相关' : singleResult.code_type === 'indirect' ? '间接体育相关' : '非体育代码' }}
                </el-descriptions-item>
                <el-descriptions-item label="代码—文本关系">
                  {{ { consistent: '相互支持', partial: '部分匹配', conflict: '存在冲突', unknown: '无法判断' }[singleResult.code_text_consistency] || singleResult.code_text_consistency }}
                </el-descriptions-item>
                <el-descriptions-item label="是否跨界">
                  <el-tag :type="singleResult.is_crossover ? 'warning' : 'info'" size="small">
                    {{ singleResult.is_crossover ? '是' : '否' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="跨界类型" :span="singleResult.crossover_type ? 1 : 0" v-if="singleResult.crossover_type">
                  {{ singleResult.crossover_type }}
                </el-descriptions-item>
                <el-descriptions-item label="业务边界">
                  共 {{ singleResult.total_business_lines }} 条业务线 | 体育 {{ singleResult.sport_business_lines }} 条
                </el-descriptions-item>
                <el-descriptions-item label="体育业务线" :span="2">
                  <el-tag v-for="(sl, i) in (singleResult.sport_lines || [])" :key="i" size="small" type="success" style="margin:2px">
                    {{ sl.line }} ({{ sl.category }})
                  </el-tag>
                  <span v-if="!(singleResult.sport_lines || []).length" style="color:#909399">无</span>
                </el-descriptions-item>
                <el-descriptions-item label="非体育业务" :span="3">
                  <el-tag v-for="(nl, i) in (singleResult.non_sport_lines || [])" :key="i" size="small" type="info" style="margin:2px">{{ nl }}</el-tag>
                  <span v-if="!(singleResult.non_sport_lines || []).length" style="color:#909399">全部为体育业务</span>
                </el-descriptions-item>
                <el-descriptions-item label="匹配关键词" :span="3">
                  <el-tag v-for="kw in singleResult.keywords" :key="kw" size="small" style="margin:2px">{{ kw }}</el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
          <!-- 右侧：特征权重雷达图 -->
          <el-col :span="10">
            <el-card>
              <template #header>四维特征权重</template>
              <RadarChart title="" :indicators="featureRadarIndicators" :series="featureRadarSeries" :height="280" />
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <!-- 批量识别 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>批量企业识别</span>
          <div>
            <el-button type="success" @click="loadCategoryDef">业态分类定义</el-button>
            <el-button type="primary" @click="addBatchRow">添加行</el-button>
            <el-button type="primary" @click="doBatchRecognition" :loading="recogStore.loading">批量识别</el-button>
          </div>
        </div>
      </template>

      <el-table :data="batchList" border stripe style="width:100%">
        <el-table-column label="企业名称" min-width="150">
          <template #default="{ row }">
            <el-input v-model="row.enterprise_name" placeholder="企业名称" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="主营业务描述" min-width="300">
          <template #default="{ row }">
            <el-input v-model="row.business_text" placeholder="输入主营业务描述" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="识别结果" min-width="120">
          <template #default="{ row }">
            <el-tag v-if="row.result" :type="row.result.sport_category === '非体育' ? 'info' : 'success'" size="small">
              {{ row.result.sport_category }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="100">
          <template #default="{ row }">
            <span v-if="row.result">{{ (row.result.confidence * 100).toFixed(1) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="SportScore" width="100">
          <template #default="{ row }">
            <el-progress v-if="row.result"
              :percentage="Math.round((row.result.sport_score != null ? row.result.sport_score : (row.result.sport_ratio || 0)) * 100)" :stroke-width="8"
              :color="(row.result.sport_score || row.result.sport_ratio || 0) > 0.5 ? '#67c23a' : (row.result.sport_score || row.result.sport_ratio || 0) > 0.2 ? '#e6a23c' : '#f56c6c'" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ $index }">
            <el-button type="danger" size="small" text @click="removeBatchRow($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 批量结果汇总 + 可视化图表 -->
      <div v-if="batchResults.length" style="margin-top:16px">
        <h4>识别结果统计</h4>
        <el-row :gutter="16">
          <el-col :span="8"><StatCard label="总企业数" :value="batchResults.length" icon="OfficeBuilding" color="#409eff" /></el-col>
          <el-col :span="8"><StatCard label="体育相关企业" :value="batchResults.filter(r=>r.sport_category!=='非体育').length" icon="TrophyBase" color="#67c23a" /></el-col>
          <el-col :span="8"><StatCard label="跨界经营企业" :value="batchResults.filter(r=>r.is_crossover).length" icon="Connection" color="#e6a23c" /></el-col>
        </el-row>

        <!-- 第一个图表行：置信度分布 + 业态分布 -->
        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="12">
            <el-card>
              <template #header>置信度分布直方图</template>
              <BarChart title="" :labels="confidenceLabels" :series="confidenceSeries"
                xName="置信度区间" yName="企业数量" :height="300" />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card>
              <template #header>识别业态分布</template>
              <PieChart title="" :data="categoryPieData" :height="300" />
            </el-card>
          </el-col>
        </el-row>

        <!-- 第二个图表行：比重分布 + 关键词云 -->
        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="14">
            <el-card>
              <template #header>SportScore 区间分布</template>
              <BarChart title="" :labels="ratioLabels" :series="ratioSeries"
                xName="占比区间" yName="企业数量" :height="300" />
            </el-card>
          </el-col>
          <el-col :span="10">
            <el-card>
              <template #header>企业跨界类型分布</template>
              <PieChart title="" :data="crossoverPieData" name="企业数量" :height="300" />
            </el-card>
          </el-col>
        </el-row>

        <!-- 关键词标签云 -->
        <el-card style="margin-top:16px">
          <template #header>关键词标签云</template>
          <div class="tag-cloud">
            <el-tag v-for="tag in allKeywords" :key="tag.text"
              :style="{ fontSize: tag.size + 'px', margin: '4px' }" :type="tag.type">
              {{ tag.text }}
            </el-tag>
          </div>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRecognitionStore } from '../store/recognition'
import StatCard from '../components/StatCard.vue'
import RadarChart from '../components/RadarChart.vue'
import BarChart from '../components/BarChart.vue'
import PieChart from '../components/PieChart.vue'

const recogStore = useRecognitionStore()

const singleForm = reactive({ enterprise_name: '', business_text: '' })
const singleResult = ref(null)

let uidCounter = 0
const batchList = reactive([
  { uid: ++uidCounter, enterprise_name: '', business_text: '', result: null },
  { uid: ++uidCounter, enterprise_name: '', business_text: '', result: null },
  { uid: ++uidCounter, enterprise_name: '', business_text: '', result: null },
])

const batchResults = computed(() => batchList.filter((r) => r.result).map((r) => r.result))

// ---- Single recognition feature radar ----
const featureRadarIndicators = [
  { name: '业务范围(W1)', max: 100 },
  { name: '关键词密度(W2)', max: 100 },
  { name: '代码权重(W3)', max: 100 },
  { name: '业态覆盖(W4)', max: 100 },
]
const featureRadarSeries = computed(() => {
  if (!singleResult.value?.feature_weights) return []
  const w = singleResult.value.feature_weights
  return [{
    name: singleResult.value.enterprise_name || '当前企业',
    data: [
      Math.round((w.w1_business_scope || 0) * 100),
      Math.round((w.w2_keyword_density || 0) * 100),
      Math.round((w.w3_code_weight || 0) * 100),
      Math.round((w.w4_category_coverage || 0) * 100),
    ],
    areaStyle: { opacity: 0.2, color: '#e6a23c' },
    lineStyle: { color: '#e6a23c' },
    itemStyle: { color: '#e6a23c' },
  }]
})

// ---- Batch charts: confidence distribution ----
const confidenceLabels = computed(() => {
  if (!batchResults.value.length) return ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
  const bins = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
  return bins
})
const confidenceSeries = computed(() => {
  if (!batchResults.value.length) return [{ name: '企业数', data: [0, 0, 0, 0, 0] }]
  const bins = [0, 0, 0, 0, 0]
  batchResults.value.forEach((r) => {
    const c = (r.confidence || 0) * 100
    if (c < 20) bins[0]++
    else if (c < 40) bins[1]++
    else if (c < 60) bins[2]++
    else if (c < 80) bins[3]++
    else bins[4]++
  })
  return [{ name: '企业数', data: bins, itemStyle: { color: '#409eff' } }]
})

// ---- Batch charts: category pie ----
const categoryPieData = computed(() => {
  if (!batchResults.value.length) return [{ name: '无数据', value: 1 }]
  const catMap = {}
  batchResults.value.forEach((r) => {
    const cat = r.sport_category || '未分类'
    catMap[cat] = (catMap[cat] || 0) + 1
  })
  return Object.entries(catMap).map(([name, value]) => ({ name, value }))
})

// ---- Batch charts: ratio distribution ----
const ratioLabels = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
const ratioSeries = computed(() => {
  const bins = [0, 0, 0, 0, 0]
  if (!batchResults.value.length) return [{ name: '企业数', data: bins }]
  batchResults.value.forEach((r) => {
    const s = (r.sport_score != null ? r.sport_score : (r.sport_ratio || 0)) * 100
    if (s < 20) bins[0]++
    else if (s < 40) bins[1]++
    else if (s < 60) bins[2]++
    else if (s < 80) bins[3]++
    else bins[4]++
  })
  return [{ name: '企业数', data: bins, itemStyle: { color: '#67c23a' } }]
})

// ---- Batch charts: crossover type pie ----
const crossoverPieData = computed(() => {
  const results = batchResults.value
  if (!results.length) return [{ name: '无数据', value: 1 }]
  const pure = results.filter((r) => !r.is_crossover).length
  const cross = results.filter((r) => r.is_crossover).length
  return [
    { name: '纯体育企业', value: pure },
    { name: '跨界经营企业', value: cross },
  ]
})

// ---- Keywords ----
const allKeywords = computed(() => {
  const kwMap = {}
  batchResults.value.forEach((r) => {
    (r.keywords || []).forEach((kw) => { kwMap[kw] = (kwMap[kw] || 0) + 1 })
  })
  return Object.entries(kwMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 30)
    .map(([text, count]) => ({
      text,
      size: Math.min(14 + count * 2, 24),
      type: ['', 'success', 'warning', 'danger', 'info'][count % 5] || '',
    }))
})

// ---- Actions ----
async function doSingleRecognition() {
  if (!singleForm.business_text) { ElMessage.warning('请输入主营业务描述'); return }
  try {
    const data = await recogStore.recognizeSingle(singleForm)
    singleResult.value = data
    ElMessage.success('识别完成')
  } catch { ElMessage.error('识别失败') }
}

async function doBatchRecognition() {
  const valid = batchList.filter((r) => r.business_text)
  if (!valid.length) { ElMessage.warning('请至少输入一条企业数据'); return }
  try {
    const data = await recogStore.recognizeBatch(valid)
    batchList.forEach((row) => { row.result = null })
    data.results.forEach((r) => {
      const row = batchList.find((item) => item.uid === r._uid)
      if (row) row.result = r
    })
    ElMessage.success(data.message || '批量识别完成')
  } catch { ElMessage.error('批量识别失败') }
}

async function loadCategoryDef() {
  try {
    const data = await recogStore.fetchCategories()
    const def = Object.entries(data).map(([cat, info]) => `${cat}: ${info.keywords.join(', ')}`).join('\n\n')
    ElMessage({ message: '业态分类定义已加载到控制台', type: 'success' })
    console.log('体育业态分类定义:\n', def)
  } catch { ElMessage.error('加载失败') }
}

function addBatchRow() { batchList.push({ uid: ++uidCounter, enterprise_name: '', business_text: '', result: null }) }
function removeBatchRow(index) { batchList.splice(index, 1) }
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 20px; }
.section-card { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.result-area { margin-top: 20px; }
.result-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.result-enterprise { font-size: 16px; font-weight: bold; }
.tag-cloud { display: flex; flex-wrap: wrap; align-items: center; }
</style>
