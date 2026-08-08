<template>
  <section class="page-shell evaluation-page">
    <header class="page-heading">
      <div><h1>模型性能评估</h1><p>准确性、异常输入表现与资源消耗</p></div>
      <div><DataModeBadge :provenance="snapshot.provenance"/><el-button @click="router.push('/compare')">查看传统方法对比</el-button></div>
    </header>
    <el-alert v-if="snapshot.provenance.mode === 'demo'" title="当前显示演示评测数据" type="info" :closable="false" show-icon/>

    <template v-if="hasEvaluation">
      <h2>识别效果</h2>
      <div class="metric-grid">
        <MetricCard label="综合一致率" :value="rate(metrics.accuracy)" unit="%" note="当前结果为代理评估，不等同人工金标准准确率" tone="blue"/>
        <MetricCard label="Precision" :value="rate(metrics.precision)" unit="%" note="模型识别结果与传统口径的交集比例" tone="teal"/>
        <MetricCard label="Recall" :value="rate(metrics.recall)" unit="%" note="传统口径样本被模型覆盖的比例" tone="yellow"/>
        <MetricCard label="MAE" :value="Number(metrics.mae || 0).toFixed(3)" unit="" note="经营比重差异的平均绝对误差" tone="red"/>
      </div>

      <h2>异常输入测试</h2>
      <div class="robust-grid">
        <article v-for="item in robustness" :key="item.label"><span>{{ item.label }}</span><strong>{{ rate(item.value) }}%</strong><el-progress :percentage="rate(item.value)" :show-text="false"/></article>
      </div>

      <h2>运行效率</h2>
      <div class="efficiency">
        <article><span>单万条记录耗时</span><strong>{{ metrics.runtime_seconds_per_10k }} 秒</strong></article>
        <article><span>峰值内存</span><strong>{{ metrics.peak_memory_mb }} MB</strong></article>
        <p>数据版本 {{ snapshot.provenance.data_version }} · 模型版本 {{ snapshot.provenance.model_version }}</p>
      </div>
    </template>

    <el-empty v-else description="当前真实批次尚未生成模型评测与异常输入测试结果"><el-button type="primary" @click="router.push('/compare')">运行模型评估</el-button></el-empty>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import DataModeBadge from '../components/common/DataModeBadge.vue'
import MetricCard from '../components/monitoring/MetricCard.vue'
import { useMonitoringStore } from '../store/monitoring'
import { useDataStore } from '../store/data'

const router = useRouter()
const monitoring = useMonitoringStore()
const dataStore = useDataStore()
const { snapshot } = storeToRefs(monitoring)
const metrics = computed(() => snapshot.value.model_metrics || {})
const hasEvaluation = computed(() => Object.keys(metrics.value).length > 0)
const rate = (value) => Number((Number(value || 0) * 100).toFixed(1))
const robustness = computed(() => [
  { label: '正常样本', value: metrics.value.normal_input_pass_rate },
  { label: '缺失文本', value: metrics.value.missing_text_pass_rate },
  { label: '噪声输入', value: metrics.value.noise_input_pass_rate },
])

onMounted(() => monitoring.refresh(dataStore.queryParams.fileId))
</script>

<style scoped>
.page-heading > div:last-child { display: flex; align-items: center; gap: 8px; }
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.evaluation-page h2 { margin: 22px 0 10px; font-size: 16px; }
.robust-grid, .efficiency { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.robust-grid article, .efficiency article { padding: 16px; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-md); background: var(--sf-surface); }
.robust-grid strong, .efficiency strong { display: block; margin: 8px 0; font-size: 24px; }
.efficiency { grid-template-columns: 1fr 1fr; }
.efficiency p { grid-column: 1 / -1; color: var(--sf-muted); }
@media (max-width: 1000px) { .metric-grid { grid-template-columns: 1fr 1fr; }.robust-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .metric-grid, .efficiency { grid-template-columns: 1fr; }.efficiency p { grid-column: auto; } }
</style>
