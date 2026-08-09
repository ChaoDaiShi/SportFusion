<template>
  <div class="directory-page">
    <h2 class="page-title">动态名录</h2>
    <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px">
      动态名录仅包含已确认/锁定的企业。待复核和争议企业不在此列。
    </el-alert>

    <el-card class="section-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="4"><el-input v-model="filters.batch_id" placeholder="批次ID" clearable /></el-col>
        <el-col :span="4"><el-input v-model="filters.region" placeholder="区域" clearable /></el-col>
        <el-col :span="4"><el-select v-model="filters.category" placeholder="业态" clearable><el-option v-for="c in categories" :key="c" :label="c" :value="c" /></el-select></el-col>
        <el-col :span="4"><el-select v-model="filters.priority" placeholder="优先级" clearable><el-option label="P1" value="P1" /><el-option label="P2" value="P2" /><el-option label="P3" value="P3" /><el-option label="P4" value="P4" /></el-select></el-col>
        <el-col :span="4"><el-button type="primary" @click="loadDirectory">查询</el-button></el-col>
      </el-row>
    </el-card>

    <el-table :data="entries" border stripe style="margin-top:16px" v-loading="loading" empty-text="暂无已确认的名录数据">
      <el-table-column prop="enterprise_name" label="企业名称" min-width="150" />
      <el-table-column prop="region" label="区域" width="100" />
      <el-table-column label="SportScore" width="100"><template #default="{row}">{{ row.sport_score?.toFixed(3) }}</template></el-table-column>
      <el-table-column prop="sport_category" label="体育业态" width="100" />
      <el-table-column label="比重" width="100"><template #default="{row}">{{ row.effective_share?.toFixed(2) }}</template></el-table-column>
      <el-table-column prop="share_source" label="来源" width="80"><template #default="{row}"><el-tag size="small" :type="row.share_source==='model'?'success':row.share_source==='manual'?'warning':'info'">{{ sourceLabel(row.share_source) }}</el-tag></template></el-table-column>
      <el-table-column prop="review_status" label="复核" width="80"><template #default="{row}"><el-tag size="small" :type="row.review_status==='confirmed'?'success':'info'">{{ row.review_status }}</el-tag></template></el-table-column>
      <el-table-column prop="priority" label="优先级" width="70" />
    </el-table>

    <el-empty v-if="!loading && entries.length === 0" description="暂无已确认的名录数据" />

    <ProvenancePanel v-if="entries.length" :provenance="entries[0]?.provenance || {}" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import ProvenancePanel from '../components/ProvenancePanel.vue'
import request from '../api/index'

const entries = ref([])
const loading = ref(false)
const filters = reactive({ batch_id: '', region: '', category: '', priority: '' })
const categories = ['体育赛事','健身休闲','体育用品','体育培训','体育场馆','体育传媒','体育管理','电子竞技','体育彩票']

function sourceLabel(s) {
  if (s === 'model') return '模型估计'
  if (s === 'fallback') return '分层回退'
  if (s === 'manual') return '人工核定'
  if (s === 'artifact_required') return '模型缺失'
  return s || '—'
}

async function loadDirectory() {
  loading.value = true
  try {
    const params = {}
    if (filters.batch_id) params.batch_id = filters.batch_id
    if (filters.region) params.region = filters.region
    if (filters.category) params.category = filters.category
    if (filters.priority) params.priority = filters.priority
    const res = await request.get('/directory/', { params })
    entries.value = res.data?.entries || []
    ElMessage.success(`加载 ${entries.value.length} 家企业`)
  } catch { ElMessage.error('加载名录失败') }
  finally { loading.value = false }
}

onMounted(loadDirectory)
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 20px; }
.section-card { margin-bottom: 16px; }
</style>
