<template>
  <span class="mode-badge" :data-mode="provenance.mode" :title="tooltip">
    {{ labels[provenance.mode] || '数据状态未知' }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  provenance: { type: Object, required: true },
})

const labels = {
  real: '真实数据',
  cached: '历史快照',
  demo: '演示数据保障',
}
const tooltip = computed(() => (
  `${labels[props.provenance.mode] || '数据状态未知'} · ${props.provenance.updated_at || '无更新时间'}`
))
</script>

<style scoped>
.mode-badge { display: inline-flex; padding: 6px 9px; border-radius: 6px; font-size: 12px; font-weight: 700; white-space: nowrap; }
.mode-badge[data-mode="real"] { background: #dcf1eb; color: #087665; }
.mode-badge[data-mode="cached"] { background: #fff0ca; color: #875a00; }
.mode-badge[data-mode="demo"] { background: #e4e8f7; color: #3046a5; }
</style>
