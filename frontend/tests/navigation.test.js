import test from 'node:test'
import assert from 'node:assert/strict'
import { navigationGroups } from '../src/config/navigation.js'

test('navigation uses the approved four product groups', () => {
  assert.deepEqual(
    navigationGroups.map((group) => group.label),
    ['监测总览', '核心分析', '可信验证', '成果应用'],
  )
})

test('navigation contains no mascot or emoji copy', () => {
  const text = JSON.stringify(navigationGroups)
  assert.equal(text.includes('小融'), false)
  assert.equal(/[\u{1F300}-\u{1FAFF}]/u.test(text), false)
})
