import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('risk center supports query-driven evidence and guarded recalculation', async () => {
  const source = await readFile(new URL('../src/views/RiskCenter.vue', import.meta.url), 'utf8')
  assert.match(source, /route\.query\.risk_id/)
  assert.match(source, /selectedRisk\.evidence/)
  assert.match(source, /校正测算预览/)
  assert.match(source, /原始结果未被覆盖/)
})

test('risk center routes selected evidence into the assistant', async () => {
  const source = await readFile(new URL('../src/views/RiskCenter.vue', import.meta.url), 'utf8')
  assert.match(source, /\/assistant\?risk_id=/)
  assert.match(source, /DataModeBadge/)
})
