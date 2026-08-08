<template>
  <section v-loading="loading" class="page-shell cockpit-page">
    <header class="page-heading">
      <div><h1>体育产业统计监测驾驶舱</h1><p>企业级识别、经营比重测算与区域风险研判</p></div>
      <div class="heading-actions"><DataModeBadge :provenance="snapshot.provenance"/><el-button type="primary" @click="router.push('/export')">生成成果报告</el-button></div>
    </header>
    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false"><el-button link @click="refresh(fileId)">重新加载</el-button></el-alert>
    <div class="pipeline"><article v-for="(step, index) in snapshot.pipeline" :key="step.id"><span>{{ index + 1 }}</span><strong>{{ step.label }}</strong><small>{{ step.description }}</small></article></div>
    <div class="metric-grid"><MetricCard v-for="metric in snapshot.metrics" :key="metric.id" v-bind="metric"/></div>
    <div class="cockpit-grid">
      <article class="panel"><header><strong>测算差异与重点风险</strong></header><MethodComparison v-if="snapshot.method_comparison" :comparison="snapshot.method_comparison"/><el-empty v-else description="当前真实批次尚未生成方法对比结果" :image-size="54"/><RiskTable :risks="snapshot.risks.slice(0, 3)" @select="openRisk"/></article>
      <article class="panel map-panel"><header><strong>区域产业规模与结构风险</strong></header><MapHeatmap title="区域产出指数" value-label="体育产出指数" :data="snapshot.regions" :height="270"/></article>
      <ContextAssistantPanel class="insight-panel" :context="analysisContext.context" :provenance="snapshot.provenance"/>
    </div>
    <article class="panel result-panel"><header><strong>风险事件明细</strong><el-button link @click="router.push('/risks')">查看全部</el-button></header><RiskTable :risks="snapshot.risks" @select="openRisk"/></article>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import DataModeBadge from '../components/common/DataModeBadge.vue'
import ContextAssistantPanel from '../components/assistant/ContextAssistantPanel.vue'
import MapHeatmap from '../components/MapHeatmap.vue'
import MetricCard from '../components/monitoring/MetricCard.vue'
import MethodComparison from '../components/monitoring/MethodComparison.vue'
import RiskTable from '../components/monitoring/RiskTable.vue'
import { useAnalysisContextStore } from '../store/analysis-context'
import { useDataStore } from '../store/data'
import { useMonitoringStore } from '../store/monitoring'

const router = useRouter()
const dataStore = useDataStore()
const monitoringStore = useMonitoringStore()
const analysisContext = useAnalysisContextStore()
const { snapshot, loading, error } = storeToRefs(monitoringStore)
const fileId = computed(() => dataStore.queryParams.fileId)
const refresh = (id) => monitoringStore.refresh(id)

function openRisk(risk) {
  monitoringStore.selectRisk(risk)
  analysisContext.patch({
    selectedRiskId: risk.id,
    region: risk.region || '四川省',
    category: risk.category || '',
  })
  router.push({ path: '/risks', query: { risk_id: risk.id } })
}

onMounted(() => monitoringStore.refresh(fileId.value))
</script>

<style scoped>
.cockpit-page { min-width: 0; }
.heading-actions, .panel > header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.pipeline { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin-bottom: 12px; }
.pipeline article { position: relative; display: grid; grid-template-columns: 30px 1fr; gap: 2px 8px; align-items: center; padding: 10px; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-sm); background: var(--sf-surface); }
.pipeline article:not(:last-child)::after { position: absolute; right: -8px; width: 8px; height: 1px; background: var(--sf-yellow); content: ''; }
.pipeline span { grid-row: 1 / 3; display: grid; width: 28px; height: 28px; place-items: center; border-radius: 50%; background: #e5eafa; color: var(--sf-blue); font-weight: 800; }
.pipeline small { color: var(--sf-muted); }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; margin-bottom: 12px; }
.cockpit-grid { display: grid; grid-template-columns: minmax(260px, .84fr) minmax(420px, 1.45fr) minmax(280px, .92fr); gap: 10px; }
.panel { min-width: 0; padding: 14px; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-md); background: var(--sf-surface); }
.panel > header { margin-bottom: 12px; }
.result-panel { margin-top: 10px; }
@media (max-width: 1100px) { .cockpit-grid { grid-template-columns: 1fr; }.metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.pipeline { grid-template-columns: 1fr; }.pipeline article::after { display: none; } }
@media (max-width: 650px) { .metric-grid { grid-template-columns: 1fr; }.heading-actions { align-items: flex-start; flex-direction: column; } }
</style>
