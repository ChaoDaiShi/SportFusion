import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveSnapshot } from '../src/features/monitoring/data-policy.js'

const snapshot = (mode, value, isComplete = true) => ({
  metrics: [{ value }],
  provenance: {
    mode,
    is_complete: isComplete,
    missing_fields: isComplete ? [] : ['model_metrics'],
  },
})

test('a complete remote snapshot wins and remains real', () => {
  const result = resolveSnapshot({
    remote: snapshot('real', 1),
    cached: snapshot('cached', 2),
    demo: snapshot('demo', 3),
  })
  assert.equal(result.provenance.mode, 'real')
})

test('a partial real snapshot wins without demo fields being inserted', () => {
  const result = resolveSnapshot({
    remote: snapshot('real', 1, false),
    cached: snapshot('real', 2),
    demo: snapshot('demo', 3),
  })
  assert.equal(result.provenance.mode, 'real')
  assert.deepEqual(result.provenance.missing_fields, ['model_metrics'])
  assert.equal(result.metrics[0].value, 1)
})

test('a cached real snapshot wins over demo when remote is absent', () => {
  const result = resolveSnapshot({
    remote: null,
    cached: snapshot('real', 2),
    demo: snapshot('demo', 3),
  })
  assert.equal(result.provenance.mode, 'cached')
  assert.equal(result.metrics[0].value, 2)
})

test('demo is used only when remote and cache are invalid', () => {
  const result = resolveSnapshot({
    remote: null,
    cached: null,
    demo: snapshot('demo', 3),
  })
  assert.equal(result.provenance.mode, 'demo')
})
