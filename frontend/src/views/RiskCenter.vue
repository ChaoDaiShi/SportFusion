<template>
  <section class="page-shell risk-page">
    <header class="page-heading">
      <div><h1>风险事件中心</h1><p>按事件核验触发依据、影响范围与处置状态</p></div>
      <DataModeBadge :provenance="snapshot.provenance" />
    </header>

    <div class="filters">
      <el-input v-model="query" clearable placeholder="搜索风险、区域或业态" />
      <el-select v-model="level" clearable placeholder="风险等级">
        <el-option label="高风险" value="high" />
        <el-option label="中风险" value="medium" />
        <el-option label="关注" value="watch" />
      </el-select>
      <el-select v-model="riskType" clearable placeholder="风险类型">
        <el-option v-for="(label, value) in typeLabels" :key="value" :label="label" :value="value" />
      </el-select>
    </div>

    <div class="risk-list">
      <button v-for="risk in filteredRisks" :key="risk.id" type="button" class="risk-item" @click="openRisk(risk)">
        <span class="level" :data-level="risk.level">{{ levelLabels[risk.level] }}</span>
        <span class="copy"><strong>{{ risk.title }}</strong><small>{{ typeLabels[risk.type] }} · {{ risk.region }} · {{ statusLabels[risk.status] }}</small></span>
        <span><small>可信度</small><strong>{{ Math.round(risk.confidence * 100) }}%</strong></span>
        <b>{{ risk.score }}</b>
      </button>
      <el-empty v-if="!filteredRisks.length" description="没有符合当前条件的风险事件" :image-size="72" />
    </div>

    <el-drawer v-model="drawerOpen" size="420px" title="风险证据与处置" @closed="handleDrawerClosed">
      <template v-if="selectedRisk">
        <span class="level" :data-level="selectedRisk.level">{{ levelLabels[selectedRisk.level] }}</span>
        <h2>{{ selectedRisk.title }}</h2>
        <p class="meta">{{ selectedRisk.id }} · {{ selectedRisk.region }} · 可信度 {{ Math.round(selectedRisk.confidence * 100) }}%</p>

        <div class="score-grid">
          <div v-for="item in scoreItems" :key="item.label">
            <span>{{ item.label }}</span><el-progress :percentage="item.value" :show-text="false"/><b>{{ item.value }}</b>
          </div>
        </div>

        <el-tabs v-model="activeTab">
          <el-tab-pane label="触发证据" name="evidence"><ul><li v-for="evidence in selectedRisk.evidence" :key="evidence">{{ evidence }}</li></ul></el-tab-pane>
          <el-tab-pane label="变化轨迹" name="timeline"><ol class="lifecycle"><li class="done">已发现</li><li class="done">待核验</li><li class="current">分析中</li><li>待处置</li><li>已解决/持续观察</li></ol></el-tab-pane>
          <el-tab-pane label="处置记录" name="actions"><el-empty description="当前事件尚无已完成处置记录" :image-size="64"/></el-tab-pane>
        </el-tabs>

        <div class="drawer-actions">
          <el-button @click="markVerified">标记核验结果</el-button>
          <el-button type="primary" @click="goAssistant">进入智能研判</el-button>
          <el-button class="wide" type="warning" @click="previewOpen = true">运行校正测算</el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="previewOpen" title="校正测算预览" width="480px">
      <el-descriptions v-if="selectedRisk" :column="1" border>
        <el-descriptions-item label="风险事件">{{ selectedRisk.id }}</el-descriptions-item>
        <el-descriptions-item label="影响区域">{{ selectedRisk.region }}</el-descriptions-item>
        <el-descriptions-item label="数据版本">{{ snapshot.provenance.data_version }}</el-descriptions-item>
        <el-descriptions-item label="模型版本">{{ snapshot.provenance.model_version }}</el-descriptions-item>
      </el-descriptions>
      <template #footer><el-button @click="previewOpen = false">取消</el-button><el-button type="warning" @click="confirmPreview">确认运行</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import DataModeBadge from '../components/common/DataModeBadge.vue'
import { useMonitoringStore } from '../store/monitoring'
import { useDataStore } from '../store/data'

const route = useRoute()
const router = useRouter()
const monitoring = useMonitoringStore()
const dataStore = useDataStore()
const { snapshot, selectedRisk } = storeToRefs(monitoring)

const query = ref('')
const level = ref('')
const riskType = ref('')
const drawerOpen = ref(false)
const previewOpen = ref(false)
const activeTab = ref('evidence')

const levelLabels = { high: '高风险', medium: '中风险', watch: '关注' }
const typeLabels = {
  enterprise_boundary: '企业识别',
  industry_structure: '产业结构',
  data_quality: '数据质量',
  model_performance: '模型性能',
  measurement_gap: '测算偏差',
}
const statusLabels = {
  new: '新发现',
  pending_verification: '待核验',
  analyzing: '分析中',
  pending_action: '待处置',
  resolved: '已解决',
  monitoring: '持续观察',
}

const filteredRisks = computed(() => snapshot.value.risks.filter((risk) => (
  (!query.value || `${risk.title}${risk.region}${risk.category || ''}`.includes(query.value))
  && (!level.value || risk.level === level.value)
  && (!riskType.value || risk.type === riskType.value)
)))
const scoreItems = computed(() => selectedRisk.value ? [
  { label: '偏离程度', value: selectedRisk.value.deviation_score },
  { label: '影响范围', value: selectedRisk.value.impact_score },
  { label: '证据可信度', value: selectedRisk.value.evidence_score },
] : [])

function openRisk(risk) {
  monitoring.selectRisk(risk)
  drawerOpen.value = true
  router.replace({ query: { ...route.query, risk_id: risk.id } })
}

function openFromQuery() {
  const risk = snapshot.value.risks.find((item) => item.id === route.query.risk_id)
  if (risk) openRisk(risk)
}

function handleDrawerClosed() {
  monitoring.clearRisk()
  const nextQuery = { ...route.query }
  delete nextQuery.risk_id
  router.replace({ query: nextQuery })
}

function markVerified() {
  ElMessage.success('核验结果已记录在当前演示会话')
  activeTab.value = 'timeline'
}

function goAssistant() {
  router.push(`/assistant?risk_id=${selectedRisk.value.id}`)
}

function confirmPreview() {
  previewOpen.value = false
  ElMessage.success('校正测算已完成预览，原始结果未被覆盖')
}

onMounted(async () => {
  await monitoring.refresh(dataStore.queryParams.fileId)
  openFromQuery()
})
watch(() => route.query.risk_id, openFromQuery)
</script>

<style scoped>
.filters { display: grid; grid-template-columns: 1fr 180px 180px; gap: 10px; margin-bottom: 14px; }
.risk-list { overflow: hidden; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-md); background: var(--sf-surface); }
.risk-item { width: 100%; display: grid; grid-template-columns: 72px 1fr 86px 48px; gap: 14px; align-items: center; padding: 15px; border: 0; border-bottom: 1px solid var(--sf-line); background: transparent; color: var(--sf-ink); text-align: left; cursor: pointer; }
.risk-item:hover { background: #f8f3e9; }
.copy { display: grid; gap: 5px; }
.copy small, .meta { color: var(--sf-muted); }
.level { width: max-content; padding: 4px 7px; border-radius: 5px; font-size: 12px; font-weight: 800; }
.level[data-level="high"] { background: #fbe0da; color: #c34732; }
.level[data-level="medium"] { background: #fff0ca; color: #976200; }
.level[data-level="watch"] { background: #dff3ed; color: #127867; }
.score-grid > div { display: grid; grid-template-columns: 80px 1fr 30px; gap: 8px; align-items: center; margin: 12px 0; }
.drawer-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 18px; }
.drawer-actions .wide { grid-column: 1 / -1; }
.lifecycle { display: grid; gap: 8px; padding-left: 20px; }
.lifecycle .done { color: var(--sf-teal); }
.lifecycle .current { color: #9a6500; font-weight: 800; }
@media (max-width: 900px) { .filters { grid-template-columns: 1fr; }.risk-item { grid-template-columns: 70px 1fr 42px; }.risk-item > span:nth-child(3) { display: none; } }
</style>
