import { writeFile } from 'node:fs/promises'

const port = process.argv[2] || '9222'
const output = process.argv[3] || 'monitoring-preview.png'
const pages = await fetch(`http://127.0.0.1:${port}/json/list`).then((response) => response.json())
const page = pages.find((item) => item.type === 'page' && item.url.includes('/monitoring'))

if (!page) throw new Error('未找到监测驾驶舱预览页')

const socket = new WebSocket(page.webSocketDebuggerUrl)
const pending = new Map()
let sequence = 0

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence
    pending.set(id, { resolve, reject })
    socket.send(JSON.stringify({ id, method, params }))
  })
}

socket.onmessage = ({ data }) => {
  const message = JSON.parse(data)
  if (!message.id || !pending.has(message.id)) return
  const request = pending.get(message.id)
  pending.delete(message.id)
  if (message.error) request.reject(new Error(message.error.message))
  else request.resolve(message.result || {})
}

await new Promise((resolve, reject) => {
  socket.onopen = resolve
  socket.onerror = reject
})

await send('Emulation.setDeviceMetricsOverride', {
  width: 1920,
  height: 1080,
  deviceScaleFactor: 1,
  mobile: false,
})
await send('Page.reload', { ignoreCache: true })
await new Promise((resolve) => setTimeout(resolve, 7000))

const screenshot = await send('Page.captureScreenshot', {
  format: 'png',
  fromSurface: true,
  captureBeyondViewport: false,
})
await writeFile(output, Buffer.from(screenshot.data, 'base64'))

const layout = await send('Runtime.evaluate', {
  expression: `JSON.stringify({
    title: document.title,
    width: document.documentElement.scrollWidth,
    viewport: innerWidth,
    cards: [...document.querySelectorAll('.metric-grid > *')].map((element) => ({
      x: Math.round(element.getBoundingClientRect().x),
      width: Math.round(element.getBoundingClientRect().width),
    })),
    canvases: [...document.querySelectorAll('canvas')].map((canvas) => ({
      width: canvas.width,
      height: canvas.height,
    })),
  })`,
  returnByValue: true,
})

console.log(layout.result.value)
socket.close()
