<template>
  <section class="context-assistant">
    <header><span>智能研判</span><DataModeBadge :provenance="provenance"/></header>
    <div class="chips"><span>{{ context.region }}</span><span>{{ context.year }} 年度</span><span>{{ context.selectedRiskId || '当前驾驶舱' }}</span></div>
    <h2>传统方法为何低估体育产业规模？</h2>
    <p v-if="latest">{{ latest.content }}</p>
    <p v-else>输入问题后，系统会引用当前数据批次和模型版本回答。</p>
    <div class="citations"><small v-for="item in citations" :key="item.id">{{ item.label }}：{{ item.value }}</small></div>
    <form @submit.prevent="submit"><el-input v-model="input" placeholder="询问指标、风险原因或测算差异"/><el-button native-type="submit" type="warning" :loading="isStreaming">发送</el-button></form>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import DataModeBadge from '../common/DataModeBadge.vue'
import { useAssistantStore } from '../../store/assistant'

const props = defineProps({
  context: { type: Object, required: true },
  provenance: { type: Object, required: true },
})
const assistant = useAssistantStore()
const { messages, citations, isStreaming } = storeToRefs(assistant)
const input = ref('')
const latest = computed(() => [...messages.value].reverse().find((item) => item.role === 'assistant'))

function submit() {
  const value = input.value.trim()
  if (!value) return
  assistant.send(value, props.context)
  input.value = ''
}
</script>

<style scoped>
.context-assistant { height: 100%; display: flex; flex-direction: column; padding: 16px; border: 2px solid var(--sf-blue); border-radius: var(--sf-radius-md); background: #fff8e8; color: var(--sf-ink); }
.context-assistant header { display: flex; justify-content: space-between; align-items: center; }
.context-assistant header > span { color: var(--sf-blue); font-size: 12px; font-weight: 900; }
.chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 12px; }
.chips span, .citations small { padding: 5px 7px; border-radius: 5px; background: #e8ecfa; color: #33415c; font-size: 11px; }
.context-assistant h2 { margin: 16px 0 8px; font-size: 18px; line-height: 1.45; }
.context-assistant p { color: var(--sf-text); line-height: 1.65; }
.citations { display: grid; gap: 5px; margin-top: auto; }
.context-assistant form { display: grid; grid-template-columns: 1fr 62px; gap: 6px; margin-top: 10px; }
</style>
