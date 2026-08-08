<template>
  <el-card class="stat-card" shadow="hover" :style="{ borderTop: `3px solid ${color}` }">
    <div class="stat-content">
      <div class="stat-info">
        <div class="stat-label">{{ label }}</div>
        <div class="stat-value">{{ formattedValue }}</div>
        <div class="stat-sub" v-if="sub">{{ sub }}</div>
      </div>
      <div class="stat-icon">
        <el-icon :size="36" :color="color"><component :is="icon" /></el-icon>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, default: '' },
  value: { type: [Number, String], default: 0 },
  unit: { type: String, default: '' },
  sub: { type: String, default: '' },
  icon: { type: String, default: 'DataLine' },
  color: { type: String, default: '#409eff' },
  format: { type: String, default: 'number' }, // number | percent
})

const formattedValue = computed(() => {
  const v = props.value
  if (props.format === 'percent') {
    return (Number(v) * 100).toFixed(1) + '%'
  }
  if (typeof v === 'number') {
    return v.toLocaleString() + (props.unit ? ' ' + props.unit : '')
  }
  return v + (props.unit ? ' ' + props.unit : '')
})
</script>

<style scoped>
.stat-card { border-radius: 8px; }
.stat-content { display: flex; justify-content: space-between; align-items: center; }
.stat-label { color: #909399; font-size: 13px; margin-bottom: 8px; }
.stat-value { font-size: 26px; font-weight: bold; color: #303133; }
.stat-sub { font-size: 12px; color: #909399; margin-top: 4px; }
.stat-icon { opacity: 0.8; }
</style>
