<template>
  <el-card class="provenance-panel">
    <template #header><span>数据与模型版本</span></template>
    <el-descriptions :column="2" size="small" border>
      <el-descriptions-item label="批次">{{ provenance?.batch_id || '—' }}</el-descriptions-item>
      <el-descriptions-item label="数据模式">{{ modeLabel }}</el-descriptions-item>
      <el-descriptions-item label="数据版本">{{ provenance?.data_version || provenance?.dictionary_version || '—' }}</el-descriptions-item>
      <el-descriptions-item label="词典版本">{{ provenance?.dictionary_version || '—' }}</el-descriptions-item>
      <el-descriptions-item label="行业代码映射">{{ provenance?.industry_code_map_version || '—' }}</el-descriptions-item>
      <el-descriptions-item label="特征Schema">{{ provenance?.feature_schema_version || '—' }}</el-descriptions-item>
      <el-descriptions-item label="SportScore参数">{{ provenance?.sportscore_parameter_version || '—' }}</el-descriptions-item>
      <el-descriptions-item label="SportShare模型">{{ provenance?.sportshare_model_version || '—' }}</el-descriptions-item>
      <el-descriptions-item label="宏观校准">{{ provenance?.macro_calibration_version || '—' }}</el-descriptions-item>
      <el-descriptions-item label="情景版本">{{ provenance?.scenario_version || '—' }}</el-descriptions-item>
      <el-descriptions-item v-if="provenance?.commit_sha" label="Commit SHA" :span="2">
        <code style="font-size:12px">{{ provenance.commit_sha }}</code>
      </el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  provenance: { type: Object, default: () => ({}) },
})

const modeLabel = computed(() => {
  const m = props.provenance?.data_mode || props.provenance?.mode
  if (m === 'formal') return '正式数据'
  if (m === 'demo') return '演示数据'
  if (m === 'test') return '测试数据'
  return m || '—'
})
</script>

<style scoped>
.provenance-panel { margin-top: 16px; }
</style>
