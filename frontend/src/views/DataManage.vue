<template>
  <div class="data-manage">
    <h2 class="page-title">数据管理</h2>

    <!-- 文件上传区域 -->
    <el-card class="section-card">
      <template #header><span>数据上传</span></template>
      <el-upload ref="uploadRef" drag :auto-upload="false" :on-change="handleFileChange" :limit="1"
        accept=".xlsx,.xls,.csv">
        <el-icon class="el-icon--upload" :size="48"><UploadFilled /></el-icon>
        <div class="upload-text">将Excel/CSV文件拖拽到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="upload-tip">支持 .xlsx / .xls / .csv 格式，建议文件大小不超过50MB</div>
        </template>
      </el-upload>
      <div class="upload-actions" v-if="dataStore.uploadFile">
        <el-button type="primary" @click="doUpload" :loading="dataStore.loading">开始上传并解析</el-button>
        <span class="file-name">{{ dataStore.uploadFile.name }}</span>
      </div>
    </el-card>

    <!-- 数据质量仪表盘 -->
    <el-card class="section-card" v-if="dataStore.fileInfo">
      <template #header><span>数据质量概览</span></template>
      <el-row :gutter="16">
        <el-col :span="8">
          <GaugeChart title="数据完整度" :value="dataQuality.completeness" :max="100" unit="%" color="#67c23a" :height="200" />
        </el-col>
        <el-col :span="8">
          <GaugeChart title="列有效性" :value="dataQuality.validity" :max="100" unit="%" color="#409eff" :height="200" />
        </el-col>
        <el-col :span="8">
          <GaugeChart title="去重率" :value="dataQuality.uniqueness" :max="100" unit="%" color="#e6a23c" :height="200" />
        </el-col>
      </el-row>
    </el-card>

    <!-- NLP预处理 -->
    <el-card class="section-card" v-if="dataStore.fileInfo">
      <template #header>
        <div class="card-header">
          <span>NLP文本预处理</span>
          <el-tag v-if="dataStore.preprocessStats" type="success">
            已处理: {{ dataStore.preprocessStats.total }} 条
          </el-tag>
        </div>
      </template>
      <div class="nlp-actions">
        <el-button type="primary" @click="doPreprocess" :loading="dataStore.loading"
          :disabled="!dataStore.queryParams.fileId">
          执行分词+体育标签标注
        </el-button>
        <span class="nlp-tip">基于"主要业务活动"字段进行中文分词、关键词提取、体育业务标签标注</span>
      </div>

      <!-- 预处理统计结果 -->
      <div v-if="dataStore.preprocessStats" class="nlp-results">
        <el-row :gutter="20">
          <el-col :span="6">
            <div class="stat-item">
              <div class="stat-value">{{ dataStore.preprocessStats.sport_enterprise_count }}</div>
              <div class="stat-label">体育企业数</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-item">
              <div class="stat-value">{{ dataStore.preprocessStats.sport_ratio }}%</div>
              <div class="stat-label">体育企业占比</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-item">
              <div class="stat-value">{{ dataStore.preprocessStats.crossover_count }}</div>
              <div class="stat-label">跨界经营者</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-item">
              <div class="stat-value">{{ dataStore.preprocessStats.code_direct_count + dataStore.preprocessStats.code_indirect_count }}</div>
              <div class="stat-label">相关行业代码</div>
            </div>
          </el-col>
        </el-row>

        <!-- 业态分布标签 -->
        <div class="category-dist" v-if="dataStore.preprocessStats.category_distribution">
          <div class="sub-title">体育业态分布</div>
          <div class="category-tags">
            <el-tag v-for="(count, cat) in dataStore.preprocessStats.category_distribution" :key="cat"
              :type="count > 500 ? 'danger' : count > 100 ? 'warning' : 'info'" effect="plain" style="margin: 4px">
              {{ cat }}: {{ count }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 数据预览表格 + 列统计图表 -->
    <el-card class="section-card" v-if="dataStore.fileInfo">
      <template #header>
        <div class="card-header">
          <span>数据预览</span>
          <div>
            <el-tag type="success">总行数: {{ dataStore.previewData.total }}</el-tag>
            <el-tag type="info" style="margin-left:8px">列数: {{ (dataStore.fileInfo?.columns || []).length }}</el-tag>
          </div>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :span="16">
          <DataTable :data="dataStore.previewData.records || []" :columns="tableColumns"
            :total="dataStore.previewData.total" show-pagination
            @page-change="onPageChange" @size-change="onSizeChange" />
        </el-col>
        <el-col :span="8">
          <BarChart title="各列非空值统计" :labels="columnStatLabels" :series="columnStatSeries"
            xName="" yName="非空值数量" :height="350" />
        </el-col>
      </el-row>
    </el-card>

    <!-- 清洗配置 -->
    <el-card class="section-card" v-if="dataStore.fileInfo">
      <template #header><span>数据清洗配置</span></template>
      <el-form :model="cleanForm" label-width="120px" inline>
        <el-form-item label="去重">
          <el-switch v-model="cleanForm.drop_duplicates" />
        </el-form-item>
        <el-form-item label="缺失值处理">
          <el-radio-group v-model="cleanForm.fill_na_strategy">
            <el-radio value="zero">填充0</el-radio>
            <el-radio value="mean">填充均值</el-radio>
            <el-radio value="median">填充中位数</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="删除含空行">
          <el-switch v-model="cleanForm.drop_null_rows" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="doClean" :loading="dataStore.loading">执行清洗</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useDataStore } from '../store/data'
import DataTable from '../components/DataTable.vue'
import GaugeChart from '../components/GaugeChart.vue'
import BarChart from '../components/BarChart.vue'

const dataStore = useDataStore()
const uploadRef = ref(null)

const cleanForm = reactive({
  drop_duplicates: true, fill_na_strategy: 'zero', drop_null_rows: false,
})

const tableColumns = computed(() => {
  const cols = dataStore.fileInfo?.columns || []
  return cols.map((c) => ({ prop: c, label: c, minWidth: 120 }))
})

// ---- Data quality gauges ----
const dataQuality = computed(() => {
  const records = dataStore.previewData.records || []
  const total = dataStore.previewData.total || 1
  const cols = dataStore.fileInfo?.columns || []

  // Completeness: average non-null ratio across columns
  let completeness = 100
  if (records.length && cols.length) {
    let nonNullTotal = 0
    cols.forEach((col) => {
      records.forEach((r) => { if (r[col] != null && r[col] !== '') nonNullTotal++ })
    })
    completeness = Math.round((nonNullTotal / (records.length * cols.length)) * 100)
  }

  // Validity: columns that have >80% non-null
  let validCols = 0
  if (records.length) {
    cols.forEach((col) => {
      const nonNull = records.filter((r) => r[col] != null && r[col] !== '').length
      if (nonNull / records.length > 0.8) validCols++
    })
  }
  const validity = cols.length ? Math.round((validCols / cols.length) * 100) : 100

  // Uniqueness: calculate real unique ratio based on records
    const uniqueRecords = new Set(records.map((r) => JSON.stringify(r))).size
    const uniqueness = total > 0 ? Math.round((uniqueRecords / total) * 100) : 100

  return { completeness, validity, uniqueness }
})

// ---- Column stats bar chart ----
const columnStatLabels = computed(() => {
  return (dataStore.fileInfo?.columns || []).map((c) => c.length > 6 ? c.slice(0, 6) + '..' : c)
})
const columnStatSeries = computed(() => {
  const records = dataStore.previewData.records || []
  const cols = dataStore.fileInfo?.columns || []
  if (!records.length || !cols.length) return [{ name: '非空值', data: [] }]
  const counts = cols.map((col) => records.filter((r) => r[col] != null && r[col] !== '').length)
  return [{ name: '非空值', data: counts, itemStyle: { color: '#409eff' } }]
})

// ---- Actions ----
function handleFileChange(file) { dataStore.uploadFile = file.raw }

async function doUpload() {
  if (!dataStore.uploadFile) { ElMessage.warning('请先选择文件'); return }
  try {
    const res = await dataStore.upload(dataStore.uploadFile)
    if (res.code === 200) {
      ElMessage.success('文件上传成功')
      await loadPreview()
    }
  } catch { ElMessage.error('上传失败') }
}

async function loadPreview() {
  if (!dataStore.queryParams.fileId) return
  await dataStore.fetchPreview(dataStore.queryParams.fileId, { page: dataStore.queryParams.page, page_size: dataStore.queryParams.pageSize })
}

async function doClean() {
  if (!dataStore.queryParams.fileId) return
  try {
    const res = await dataStore.clean(dataStore.queryParams.fileId, { ...cleanForm })
    if (res.code === 200) {
      ElMessage.success('数据清洗完成')
      await loadPreview()
    }
  } catch { ElMessage.error('清洗失败') }
}

async function doPreprocess() {
  if (!dataStore.queryParams.fileId) return
  try {
    const res = await dataStore.nlpPreprocess(dataStore.queryParams.fileId)
    if (res.code === 200) {
      ElMessage.success(`NLP预处理完成！识别出 ${res.data.stats.sport_enterprise_count} 家体育相关企业`)
    }
  } catch { ElMessage.error('预处理失败') }
}

function onPageChange(page) { dataStore.queryParams.page = page; loadPreview() }
function onSizeChange(size) { dataStore.queryParams.pageSize = size; dataStore.queryParams.page = 1; loadPreview() }

onMounted(async () => {
  if (dataStore.queryParams.fileId && dataStore.fileInfo) {
    await loadPreview()
  }
})
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 20px; color: #303133; }
.section-card { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.upload-text { color: #909399; font-size: 14px; margin-top: 12px; }
.upload-text em { color: #409eff; font-style: normal; }
.upload-tip { font-size: 12px; color: #c0c4cc; margin-top: 8px; }
.upload-actions { margin-top: 16px; display: flex; align-items: center; gap: 16px; }
.file-name { color: #606266; font-size: 13px; }
.nlp-actions { display: flex; align-items: center; gap: 16px; }
.nlp-tip { color: #909399; font-size: 13px; }
.nlp-results { margin-top: 20px; }
.stat-item { text-align: center; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.stat-value { font-size: 28px; font-weight: 700; color: #409eff; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
.sub-title { font-size: 14px; font-weight: 600; color: #303133; margin: 16px 0 8px; }
.category-dist { margin-top: 16px; }
</style>
