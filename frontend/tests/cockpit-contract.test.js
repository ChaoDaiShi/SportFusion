import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('cockpit exposes provenance, comparison and risk navigation', async () => {
  const source = await readFile(new URL('../src/views/MonitoringCockpit.vue', import.meta.url), 'utf8')
  assert.match(source, /DataModeBadge/)
  assert.match(source, /snapshot\.method_comparison/)
  assert.match(source, /path:\s*['"]\/risks['"]/)
  assert.doesNotMatch(source, /ChatAssistant|小融/)
  assert.match(source, /repeat\(auto-fit/)
})

test('data mode badge names all supported provenance modes', async () => {
  const source = await readFile(new URL('../src/components/common/DataModeBadge.vue', import.meta.url), 'utf8')
  assert.match(source, /真实数据/)
  assert.match(source, /历史快照/)
  assert.match(source, /演示数据保障/)
})

test('map uses output-index wording instead of a currency unit', async () => {
  const source = await readFile(new URL('../src/components/MapHeatmap.vue', import.meta.url), 'utf8')
  assert.match(source, /valueLabel/)
  assert.doesNotMatch(source, /体育产值: \{c\}万元/)
  assert.match(source, /510000_full\.json/)
  assert.match(source, /registerMap\('sichuan'/)
  assert.match(source, /notMerge:\s*true/)
})
