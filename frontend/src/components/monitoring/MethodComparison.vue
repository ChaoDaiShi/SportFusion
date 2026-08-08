<template>
  <div class="comparison">
    <div v-for="row in rows" :key="row.label" class="comparison-row">
      <div><span>{{ row.label }}</span><strong>{{ format(row.value) }}</strong></div>
      <div class="track"><i :style="{ width: `${row.width}%`, background: row.color }"></i></div>
    </div>
    <p>模型测算较传统方法高 <strong>{{ comparison.gap_percent }}%</strong></p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  comparison: { type: Object, required: true },
})
const max = computed(() => Math.max(
  props.comparison.traditional || 0,
  props.comparison.model || 0,
  1,
))
const rows = computed(() => [
  {
    label: '传统行业代码法',
    value: props.comparison.traditional,
    width: props.comparison.traditional / max.value * 100,
    color: 'var(--sf-yellow)',
  },
  {
    label: 'NLP 融合模型',
    value: props.comparison.model,
    width: props.comparison.model / max.value * 100,
    color: 'var(--sf-teal)',
  },
])
const format = (value) => Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 1 })
</script>

<style scoped>
.comparison-row { margin-bottom: 12px; }
.comparison-row > div:first-child { display: flex; justify-content: space-between; font-size: 12px; }
.track { height: 8px; margin-top: 6px; overflow: hidden; border-radius: 8px; background: #ebe5da; }
.track i { display: block; height: 100%; border-radius: inherit; }
.comparison p { color: var(--sf-muted); font-size: 12px; }
</style>
