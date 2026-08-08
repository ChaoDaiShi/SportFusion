import test from 'node:test'
import assert from 'node:assert/strict'
import { consumeSseChunk } from '../src/features/assistant/sse.js'

test('parser preserves a split event until the next chunk', () => {
  const first = consumeSseChunk('', 'data: {"type":"answer_')
  assert.deepEqual(first.events, [])
  const second = consumeSseChunk(first.remainder, 'delta","content":"结论"}\n\n')
  assert.equal(second.events[0].type, 'answer_delta')
  assert.equal(second.events[0].content, '结论')
  assert.equal(second.remainder, '')
})

test('parser returns multiple complete events', () => {
  const result = consumeSseChunk(
    '',
    'data: {"type":"tool_started"}\n\ndata: {"type":"completed"}\n\n',
  )
  assert.deepEqual(
    result.events.map((event) => event.type),
    ['tool_started', 'completed'],
  )
})
