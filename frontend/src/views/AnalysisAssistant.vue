<template>
  <section class="assistant-workspace">
    <aside class="sessions">
      <h2>分析会话</h2>
      <el-button type="primary" @click="assistant.reset()">新建研判</el-button>
      <button class="session active" type="button">当前分析<small>{{ context.selectedRiskId || '综合监测' }}</small></button>
    </aside>

    <main class="conversation">
      <header><h1>智能决策问答</h1><p>基于当前数据批次、模型版本与风险证据</p></header>
      <div class="messages">
        <article v-for="(message, index) in messages" :key="index" :data-role="message.role">
          <span>{{ message.role === 'user' ? '问题' : '研判' }}</span><p>{{ message.content }}</p>
        </article>
        <el-empty v-if="!messages.length" description="可询问测算差异、风险原因或企业边界"/>
      </div>
      <el-alert v-if="warnings.length" :title="warnings.join('；')" type="warning" :closable="false"/>
      <p class="progress">{{ progress }}</p>
      <div class="action-row"><el-button v-for="action in actions" :key="action.id" @click="handleAction(action)">{{ action.label }}</el-button></div>
      <form @submit.prevent="submit"><el-input v-model="input" type="textarea" :rows="3" placeholder="输入分析问题或执行指令"/><el-button type="primary" native-type="submit" :loading="isStreaming">发送</el-button></form>
    </main>

    <aside class="inspector">
      <h2>依据与参数</h2>
      <DataModeBadge :provenance="snapshot.provenance"/>
      <dl><dt>数据版本</dt><dd>{{ snapshot.provenance.data_version }}</dd><dt>模型版本</dt><dd>{{ snapshot.provenance.model_version }}</dd></dl>
      <h3>引用依据</h3>
      <article v-for="item in citations" :key="item.id"><strong>{{ item.label }}</strong><p>{{ item.value }}</p><small>{{ item.data_version }} · {{ item.model_version }}</small></article>
    </aside>

    <el-dialog v-model="previewOpen" title="操作预览" width="480px">
      <p>{{ previewText }}</p>
      <template #footer><el-button @click="previewOpen = false">取消</el-button><el-button type="warning" @click="confirmAction">确认继续</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import DataModeBadge from '../components/common/DataModeBadge.vue'
import { useAssistantStore } from '../store/assistant'
import { useAnalysisContextStore } from '../store/analysis-context'
import { useMonitoringStore } from '../store/monitoring'

const route = useRoute()
const router = useRouter()
const assistant = useAssistantStore()
const contextStore = useAnalysisContextStore()
const monitoring = useMonitoringStore()
const { messages, progress, citations, actions, warnings, isStreaming } = storeToRefs(assistant)
const { snapshot } = storeToRefs(monitoring)
const context = contextStore.context
const input = ref('')
const previewOpen = ref(false)
const pendingAction = ref(null)
const previewText = computed(() => (
  pendingAction.value?.type === 'preview_report'
    ? `将使用数据版本 ${snapshot.value.provenance.data_version} 生成报告。`
    : `将针对风险 ${pendingAction.value?.payload?.risk_id || ''} 运行校正测算预览。`
))

function submit() {
  const value = input.value.trim()
  if (!value) return
  assistant.send(value, context)
  input.value = ''
}

function handleAction(action) {
  if (action.type === 'open_risk') {
    router.push(`/risks?risk_id=${action.payload.risk_id}`)
  } else if (action.type === 'navigate') {
    router.push(action.payload.path)
  } else {
    pendingAction.value = action
    previewOpen.value = true
  }
}

function confirmAction() {
  const action = pendingAction.value
  previewOpen.value = false
  if (action?.type === 'preview_report') router.push('/export')
  if (action?.type === 'preview_recalculation') ElMessage.success('校正测算已完成预览，原始结果未被覆盖')
}

onMounted(async () => {
  if (route.query.risk_id) {
    contextStore.patch({ selectedRiskId: String(route.query.risk_id) })
  }
  await monitoring.refresh(context.fileId || undefined)
})
</script>

<style scoped>
.assistant-workspace { min-height: calc(100vh - 36px); display: grid; grid-template-columns: 190px minmax(0, 1fr) 280px; overflow: hidden; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-lg); background: var(--sf-surface); box-shadow: var(--sf-shadow); }
.sessions, .inspector { padding: 18px; background: var(--sf-surface-muted); }
.inspector { background: var(--sf-surface); border-left: 1px solid var(--sf-line); }
.conversation { display: flex; min-width: 0; flex-direction: column; padding: 20px; }
.conversation header h1 { margin: 0; }
.conversation header p, .progress { color: var(--sf-muted); }
.messages { flex: 1; overflow: auto; }
.messages article { max-width: 82%; margin: 12px 0; padding: 12px; border-radius: 9px; background: #f3efe7; }
.messages article[data-role="user"] { margin-left: auto; background: var(--sf-blue); color: white; }
.messages span { font-size: 11px; font-weight: 800; }
.messages p { white-space: pre-wrap; }
.conversation form { display: grid; grid-template-columns: 1fr 88px; gap: 8px; }
.action-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.inspector dl { display: grid; grid-template-columns: 1fr auto; gap: 8px; }
.inspector article { margin-top: 8px; padding: 10px; border-radius: 6px; background: #f4f0e8; }
.session { width: 100%; margin-top: 12px; padding: 10px; border: 0; border-radius: 6px; background: var(--sf-surface); text-align: left; }
.session small { display: block; color: var(--sf-muted); }
@media (max-width: 1100px) { .assistant-workspace { grid-template-columns: 150px 1fr; }.inspector { display: none; } }
@media (max-width: 720px) { .assistant-workspace { grid-template-columns: 1fr; }.sessions { display: none; } }
</style>
