<template>
  <div class="risk-table" role="table" aria-label="风险事件">
    <button
      v-for="risk in risks"
      :key="risk.id"
      class="risk-row"
      type="button"
      @click="$emit('select', risk)"
    >
      <span class="risk-level" :data-level="risk.level">{{ levelLabel[risk.level] }}</span>
      <span class="risk-copy"><strong>{{ risk.title }}</strong><small>{{ typeLabel[risk.type] }} · {{ risk.region }}</small></span>
      <span class="risk-score">{{ risk.score }}</span>
    </button>
    <p v-if="!risks.length" class="empty-risk">当前批次未触发结构风险</p>
  </div>
</template>

<script setup>
defineProps({ risks: { type: Array, default: () => [] } })
defineEmits(['select'])
const levelLabel = { high: '高风险', medium: '中风险', watch: '关注' }
const typeLabel = {
  enterprise_boundary: '企业识别',
  industry_structure: '产业结构',
  data_quality: '数据质量',
  model_performance: '模型性能',
  measurement_gap: '测算偏差',
}
</script>

<style scoped>
.risk-table { display: grid; gap: 6px; }
.risk-row { width: 100%; display: grid; grid-template-columns: 52px minmax(0, 1fr) 32px; gap: 10px; align-items: center; padding: 10px; border: 0; border-radius: 7px; background: #f7f2e9; color: var(--sf-ink); text-align: left; cursor: pointer; }
.risk-row:hover { background: #eee7da; }
.risk-level { padding: 4px 5px; border-radius: 4px; font-size: 10px; font-weight: 800; text-align: center; }
.risk-level[data-level="high"] { background: #fbe0da; color: #c34732; }
.risk-level[data-level="medium"] { background: #fff0ca; color: #976200; }
.risk-level[data-level="watch"] { background: #dff3ed; color: #127867; }
.risk-copy { min-width: 0; display: grid; gap: 3px; }
.risk-copy strong { overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.risk-copy small { color: var(--sf-muted); font-size: 10px; }
.risk-score { font-size: 17px; font-weight: 900; text-align: right; }
.empty-risk { margin: 14px 0; color: var(--sf-muted); font-size: 12px; text-align: center; }
</style>
