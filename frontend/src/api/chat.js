import request from './index'

/**
 * 获取预设智能问题列表
 */
export function getPresetQuestions() {
  return request.get('/chat/presets')
}

/**
 * 非流式发送消息（备用）
 */
export function sendChat(message, history = []) {
  return request.post('/chat/send', { message, history })
}

/**
 * 流式聊天 — 返回原生 fetch Response 供 ReadableStream 消费
 *
 * 不经过 axios 拦截器，直接使用 fetch 获取流式响应。
 * 调用方通过 response.body.getReader() 读取 SSE 事件流。
 *
 * @param {string} message - 用户消息
 * @param {Array} history - 历史消息 [{role, content}]
 * @returns {Promise<Response>} fetch Response（body 为 ReadableStream）
 */
export function streamChat(message, history = []) {
  return fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message, history }),
  })
}
