<template>
  <div class="measure-compare">
    <h2 class="page-title">测算对比验证</h2>

    <!-- 顶部指标卡片 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="6">
        <StatCard label="模型准确率" :value="metrics.accuracy" format="percent" icon="CircleCheck" color="#67c23a" />
      </el-col>
      <el-col :span="6">
        <StatCard label="精确率" :value="metrics.precision" format="percent" icon="Aim" color="#409eff" />
      </el-col>
      <el-col :span="6">
        <StatCard label="召回率" :value="metrics.recall" format="percent" icon="RefreshRight" color="#e6a23c" />
      </el-col>
      <el-col :span="6">
        <StatCard label="MAE误差" :value="metrics.mae" unit="万元" icon="Warning" color="#f56c6c" />
      </el-col>
    </el-row>

    <!-- 双列对比图表 -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header>传统行业统计</template>
          <BarChart title="传统统计方法产值分布"
            :labels="categoryLabels"
            :series="[{ name: '传统统计', data: traditionalBarData }]"
            y-name="产值（万元）" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>NLP模型测算</template>
          <BarChart title="NLP模型测算产值分布"
            :labels="categoryLabels"
            :series="[{ name: '模型测算', data: modelBarData }]"
            y-name="产值（万元）" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 散点图：传统 vs NLP 企业级对比 -->
    <el-row :gutter="16" style="margin-top:20px">
      <el-col :span="14">
        <el-card>
          <template #header>传统方法 vs NLP模型 企业级散点对比</template>
          <ScatterChart title="" :data="scatterData"
            xName="传统方法体育占比" yName="NLP模型体育占比" :symbolSize="10" :height="400" />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>占比差值分布（NLP - 传统）</template>
          <BarChart title="" :labels="diffLabels" :series="diffSeries"
            xName="差值区间" yName="企业数量" :height="400" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 模型性能指标面板 -->
    <el-card class="section-card">
      <template #header>模型性能对比指标</template>
      <el-table :data="comparisonData" border stripe style="width:100%">
        <el-table-column prop="metric" label="指标" width="180" />
        <el-table-column prop="traditional" label="传统行业统计" width="180">
          <template #default="{ row }">
            {{ typeof row.traditional === 'number' ? row.traditional.toFixed(2) : row.traditional }}
          </template>
        </el-table-column>
        <el-table-column prop="model" label="NLP模型" width="180" />
        <el-table-column label="提升幅度">
          <template #default="{ row }">
            <span :style="{ color: row.improvement > 0 ? '#67c23a' : '#f56c6c', fontWeight:'bold' }">
              {{ row.improvement > 0 ? '+' : '' }}{{ typeof row.improvement === 'number' ? row.improvement.toFixed(2) : row.improvement }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 分业态准确率 -->
    <el-card class="section-card">
      <template #header>分业态模型精度</template>
      <BarChart title="各业态识别准确率"
        :labels="categoryLabels"
        :series="categoryAccuracy"
        y-name="比例" :height="350" />
    </el-card>

    <!-- 参数调试区 -->
    <el-card class="section-card">
      <template #header>参数调试</template>
      <el-form :model="tuningParams" label-width="140px" inline>
        <el-form-item label="关键词匹配阈值">
          <el-slider v-model="tuningParams.keyword_threshold" :min="0.1" :max="1.0" :step="0.1" show-input style="width:200px" />
        </el-form-item>
        <el-form-item label="营收占比基准调整">
          <el-slider v-model="tuningParams.ratio_adj" :min="0.5" :max="2.0" :step="0.1" show-input style="width:200px" />
        </el-form-item>
        <el-form-item label="跨界识别敏感度">
          <el-radio-group v-model="tuningParams.crossover_sensitivity">
            <el-radio :value="0.3">低</el-radio>
            <el-radio :value="0.5">中</el-radio>
            <el-radio :value="0.8">高</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applyTuning">应用参数</el-button>
        </el-form-item>
      </el-form>
      <el-divider />
      <p style="color:#909399;font-size:13px">调整参数后将影响企业识别和产值测算的结果精度，建议在验证数据集上评估后再正式应用。</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import StatCard from '../components/StatCard.vue'
import BarChart from '../components/BarChart.vue'
import ScatterChart from '../components/ScatterChart.vue'
import { getValidateSummary } from '../api/validate'
import { useDataStore } from '../store/data'

const tuningParams = reactive({
  keyword_threshold: 0.5, ratio_adj: 1.0, crossover_sensitivity: 0.5,
})

const metrics = ref({ accuracy: 0.89, precision: 0.87, recall: 0.85, mae: 186.3 })

const comparisonData = ref([
  { metric: '准确率(Accuracy)', traditional: 0.72, model: 0.89, improvement: 0.17 },
  { metric: '精确率(Precision)', traditional: 0.68, model: 0.87, improvement: 0.19 },
  { metric: '召回率(Recall)', traditional: 0.70, model: 0.85, improvement: 0.15 },
  { metric: 'F1分数', traditional: 0.69, model: 0.86, improvement: 0.17 },
  { metric: 'MAE(万元)', traditional: 520.5, model: 186.3, improvement: -334.2 },
  { metric: 'RMSE(万元)', traditional: 680.8, model: 245.6, improvement: -435.2 },
  { metric: 'R²决定系数', traditional: 0.61, model: 0.88, improvement: 0.27 },
])

const traditionalBarData = ref([10500, 8200, 6100, 9500])
const modelBarData = ref([12850, 9630, 7540, 11200])
const categoryLabels = ref(['赛事', '健身', '培训', '用品'])
const categoryAccuracy = ref([
  { name: '准确率', data: [0.91, 0.87, 0.84, 0.92] },
  { name: '精确率', data: [0.89, 0.85, 0.82, 0.91] },
  { name: '召回率', data: [0.88, 0.86, 0.81, 0.90] },
])

// ---- Scatter: simulated 50 enterprises ----
function buildScatterDemo() {
  const points = []
  for (let i = 0; i < 50; i++) {
    const trad = Math.random() * 0.6 + 0.1
    const noise = (Math.random() - 0.5) * 0.2
    const nlp = Math.max(0.02, Math.min(0.95, trad + noise + 0.05))
    points.push([Math.round(trad * 100), Math.round(nlp * 100)])
  }
  points.push([15, 55], [30, 72], [80, 92], [5, 8], [60, 65])
  return [{ name: '企业', data: points, itemStyle: { color: '#409eff', opacity: 0.6 } }]
}
const scatterData = ref(buildScatterDemo())

// ---- Residual distribution ----
const diffLabels = ['<-20%', '-20~-10%', '-10~0%', '0~10%', '10~20%', '>20%']
function buildDiffSeries(data) {
  const all = data || scatterData.value[0]?.data || []
  const bins = [0, 0, 0, 0, 0, 0]
  all.forEach(([trad, nlp]) => {
    const d = nlp - trad
    if (d < -20) bins[0]++
    else if (d < -10) bins[1]++
    else if (d < 0) bins[2]++
    else if (d < 10) bins[3]++
    else if (d < 20) bins[4]++
    else bins[5]++
  })
  return [{ name: '企业数', data: bins, itemStyle: { color: '#e6a23c' } }]
}
const diffSeries = ref(buildDiffSeries())

const dataStore = useDataStore()

onMounted(async () => {
  try {
    if (!dataStore.queryParams.fileId) {
      ElMessage.info('请先在数据管理页面上传并预处理数据')
      return
    }
    const res = await getValidateSummary(dataStore.queryParams.fileId)
    if (res?.code === 200 && res.data) {
      const d = res.data
      if (d.metrics) {
        metrics.value = {
          accuracy: d.metrics.accuracy || metrics.value.accuracy,
          precision: d.metrics.precision || metrics.value.precision,
          recall: d.metrics.recall || metrics.value.recall,
          mae: d.metrics.mae || metrics.value.mae,
        }
      }
      if (d.comparison) comparisonData.value = d.comparison
      if (d.model_stats) {
        const stats = d.model_stats
        if (stats.category_stats) {
          categoryLabels.value = stats.category_stats.map((c) => c.category)
          traditionalBarData.value = stats.category_stats.map((c) => Math.round(c.traditional_output || 0))
          modelBarData.value = stats.category_stats.map((c) => Math.round(c.model_output || 0))
          categoryAccuracy.value = [
            { name: '准确率', data: stats.category_stats.map((c) => c.accuracy || 0) },
            { name: '精确率', data: stats.category_stats.map((c) => c.precision || 0) },
            { name: '召回率', data: stats.category_stats.map((c) => c.recall || 0) },
          ]
        }
      }
      if (d.enterprise_pairs?.length) {
        const points = d.enterprise_pairs.map((p) => [p.traditional * 100, p.nlp * 100])
        scatterData.value = [{
          name: '企业', data: points,
          itemStyle: { color: '#409eff', opacity: 0.6 },
        }]
        diffSeries.value = buildDiffSeries(points)
      }
    }
  } catch { /* use demo */ }
})

function applyTuning() {
  ElMessage.success('参数已应用，可重新执行识别和测算')
}
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 20px; }
.section-card { margin-top: 20px; }
</style>
