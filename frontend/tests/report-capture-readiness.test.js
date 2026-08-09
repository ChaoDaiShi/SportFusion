import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const reviewPath = fileURLToPath(new URL('../src/views/ReviewWorkbench.vue', import.meta.url))
const directoryPath = fileURLToPath(new URL('../src/views/EnterpriseDirectory.vue', import.meta.url))
const sharePath = fileURLToPath(new URL('../src/views/SportShare.vue', import.meta.url))

test('review workbench loads tasks when the page mounts', () => {
  const source = readFileSync(reviewPath, 'utf8')
  assert.match(source, /import\s*\{[^}]*\bonMounted\b[^}]*\}\s*from\s*['"]vue['"]/)
  assert.match(source, /onMounted\(loadTasks\)/)
})

test('report-facing empty tables use explicit Chinese copy', () => {
  const reviewSource = readFileSync(reviewPath, 'utf8')
  const directorySource = readFileSync(directoryPath, 'utf8')
  const shareSource = readFileSync(sharePath, 'utf8')

  assert.match(reviewSource, /<el-table[^>]*empty-text="暂无复核任务"/)
  assert.match(directorySource, /<el-table[^>]*empty-text="暂无已确认的名录数据"/)
  assert.match(shareSource, /<el-table[^>]*empty-text="暂无经营比重测算结果"/)
})
