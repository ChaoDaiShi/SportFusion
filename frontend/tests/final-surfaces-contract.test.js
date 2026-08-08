import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('model evaluation distinguishes proxy metrics and missing real evaluation', async () => {
  const source = await readFile(new URL('../src/views/ModelEvaluation.vue', import.meta.url), 'utf8')
  assert.match(source, /综合一致率/)
  assert.match(source, /不等同人工金标准准确率/)
  assert.match(source, /hasEvaluation/)
  assert.match(source, /尚未生成模型评测/)
})

test('report export requires a provenance-aware confirmation', async () => {
  const source = await readFile(new URL('../src/views/ReportExport.vue', import.meta.url), 'utf8')
  assert.match(source, /requestDownload/)
  assert.match(source, /confirmDownload/)
  assert.match(source, /DataModeBadge/)
  assert.match(source, /确认生成并下载/)
})
