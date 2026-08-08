<template>
  <article class="metric-card" :style="{ '--tone': toneColor }">
    <span class="metric-dot" aria-hidden="true"></span>
    <small>{{ label }}</small>
    <strong>{{ formatted }}<em>{{ unit }}</em></strong>
    <p>{{ note }}</p>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: String,
  value: [Number, String],
  unit: String,
  note: String,
  tone: { type: String, default: 'blue' },
})

const colors = {
  teal: 'var(--sf-teal)',
  red: 'var(--sf-red)',
  yellow: 'var(--sf-yellow)',
  blue: 'var(--sf-blue)',
}
const toneColor = computed(() => colors[props.tone] || colors.blue)
const formatted = computed(() => (
  typeof props.value === 'number'
    ? props.value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
    : props.value
))
</script>

<style scoped>
.metric-card { position: relative; padding: 16px; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-md); background: var(--sf-surface); }
.metric-dot { position: absolute; right: 14px; top: 14px; width: 9px; height: 9px; border-radius: 50%; background: var(--tone); }
small, p { color: var(--sf-muted); }
strong { display: block; margin-top: 8px; font-size: 28px; letter-spacing: -0.04em; }
em { margin-left: 5px; font-size: 12px; font-style: normal; font-weight: 500; }
p { margin: 7px 0 0; font-size: 12px; }
</style>
