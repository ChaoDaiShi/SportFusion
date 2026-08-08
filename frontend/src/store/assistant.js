import { defineStore } from 'pinia'
import { ref } from 'vue'
import { streamAssistant } from '../api/assistant'
import { consumeSseChunk } from '../features/assistant/sse'

const warningLabels = {
  MODEL_UNAVAILABLE_RULE_FALLBACK: '模型服务暂不可用，当前回答由可追溯规则生成',
}

export const useAssistantStore = defineStore('assistant', () => {
  const messages = ref([])
  const progress = ref('')
  const citations = ref([])
  const actions = ref([])
  const warnings = ref([])
  const isStreaming = ref(false)
  const metadata = ref({})
  let controller = null

  function applyEvent(event, assistantMessage) {
    if (event.type === 'context_ready') metadata.value = event
    if (event.type === 'tool_started') progress.value = `正在${event.label}`
    if (event.type === 'tool_finished') progress.value = `${event.label}完成`
    if (event.type === 'answer_delta') assistantMessage.content += event.content || ''
    if (event.type === 'citations_ready') citations.value = event.citations || []
    if (event.type === 'actions_ready') actions.value = event.actions || []
    if (event.type === 'completed') {
      warnings.value = (event.warnings || []).map((item) => warningLabels[item] || item)
      progress.value = '分析完成'
    }
    if (event.type === 'error') {
      warnings.value = [event.content || '研判服务暂不可用']
      progress.value = '分析中断'
    }
  }

  async function send(message, context, history = []) {
    if (!message.trim() || isStreaming.value) return
    const priorHistory = history.length
      ? history
      : messages.value.map(({ role, content }) => ({ role, content }))
    const userMessage = { role: 'user', content: message.trim() }
    const assistantMessage = { role: 'assistant', content: '' }
    messages.value.push(userMessage, assistantMessage)
    citations.value = []
    actions.value = []
    warnings.value = []
    progress.value = '正在获取上下文'
    isStreaming.value = true
    controller = new AbortController()

    try {
      const response = await streamAssistant({
        message: userMessage.content,
        history: priorHistory,
        context,
        file_id: context.fileId || null,
      }, controller.signal)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const parsed = consumeSseChunk(buffer, decoder.decode(value, { stream: true }))
        buffer = parsed.remainder
        parsed.events.forEach((event) => applyEvent(event, assistantMessage))
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        warnings.value = ['研判服务暂不可用，请重试']
        progress.value = '分析中断'
      }
    } finally {
      isStreaming.value = false
      controller = null
    }
  }

  function cancel() {
    controller?.abort()
  }

  function reset() {
    cancel()
    messages.value = []
    progress.value = ''
    citations.value = []
    actions.value = []
    warnings.value = []
  }

  return {
    messages,
    progress,
    citations,
    actions,
    warnings,
    isStreaming,
    metadata,
    send,
    cancel,
    reset,
  }
})
