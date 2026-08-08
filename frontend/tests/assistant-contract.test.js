import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('analysis workspace exposes citations, actions and provenance', async () => {
  const source = await readFile(new URL('../src/views/AnalysisAssistant.vue', import.meta.url), 'utf8')
  assert.match(source, /citations/)
  assert.match(source, /actions/)
  assert.match(source, /DataModeBadge/)
  assert.doesNotMatch(source, /小融|ChatAssistant/)
})

test('context assistant sends the current analysis context', async () => {
  const source = await readFile(new URL('../src/components/assistant/ContextAssistantPanel.vue', import.meta.url), 'utf8')
  assert.match(source, /assistant\.send\(value, props\.context\)/)
  assert.match(source, /provenance/)
})
