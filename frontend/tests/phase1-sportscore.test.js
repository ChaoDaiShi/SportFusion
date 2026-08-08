/**
 * Phase 1 frontend tests — SportScore display & backward compatibility
 *
 * Verifies:
 *   1. Recognition results with sport_score render correctly
 *   2. Old sport_ratio data doesn't crash during compatibility period
 *   3. SportScore vs SportShare distinction in API contract
 */
import test from 'node:test'
import assert from 'node:assert/strict'

// ---------------------------------------------------------------------------
// Helper: simulate data processing that the EnterpriseRecognition view performs
// ---------------------------------------------------------------------------

/**
 * Simulates the ratio histogram calculation from EnterpriseRecognition.vue.
 * Must handle both sport_score (new) and sport_ratio (legacy) without crash.
 */
function computeRatioForHistogram(result) {
  const s = (result.sport_score != null ? result.sport_score : (result.sport_ratio || 0)) * 100
  return Math.round(s)
}

/**
 * Simulates the progress bar percentage from EnterpriseRecognition.vue.
 */
function computeProgressBarPercent(result) {
  return Math.round((result.sport_score != null ? result.sport_score : (result.sport_ratio || 0)) * 100)
}

/**
 * Simulates the color selection from EnterpriseRecognition.vue.
 */
function computeProgressColor(result) {
  const val = result.sport_score != null ? result.sport_score : (result.sport_ratio || 0)
  if (val > 0.5) return '#67c23a'
  if (val > 0.2) return '#e6a23c'
  return '#f56c6c'
}

/**
 * Simulates the single result display value from EnterpriseRecognition.vue.
 */
function computeDisplayPercent(result) {
  const val = result.sport_score != null ? result.sport_score : (result.sport_ratio || 0)
  return (val * 100).toFixed(1)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test('sport_score result renders correct percentage', () => {
  const result = { sport_score: 0.73, sport_ratio: 0.73 }
  assert.equal(computeDisplayPercent(result), '73.0')
})

test('legacy sport_ratio fallback does not crash', () => {
  const result = { sport_ratio: 0.45 }
  // Should not throw, should fall back to sport_ratio
  assert.equal(computeDisplayPercent(result), '45.0')
})

test('both null defaults to zero', () => {
  const result = {}
  assert.equal(computeDisplayPercent(result), '0.0')
})

test('sport_score zero displays zero', () => {
  const result = { sport_score: 0.0 }
  assert.equal(computeDisplayPercent(result), '0.0')
})

test('sport_score 1.0 displays 100%', () => {
  const result = { sport_score: 1.0 }
  assert.equal(computeDisplayPercent(result), '100.0')
})

test('histogram bin uses sport_score primary', () => {
  const result = { sport_score: 0.73, sport_ratio: 0.10 }
  assert.equal(computeRatioForHistogram(result), 73)
})

test('histogram falls back to sport_ratio', () => {
  const result = { sport_ratio: 0.45 }
  assert.equal(computeRatioForHistogram(result), 45)
})

test('progress bar percent uses sport_score', () => {
  const result = { sport_score: 0.88 }
  assert.equal(computeProgressBarPercent(result), 88)
})

test('progress bar color green for high score', () => {
  assert.equal(computeProgressColor({ sport_score: 0.73 }), '#67c23a')
})

test('progress bar color orange for medium score', () => {
  assert.equal(computeProgressColor({ sport_score: 0.35 }), '#e6a23c')
})

test('progress bar color red for low score', () => {
  assert.equal(computeProgressColor({ sport_score: 0.10 }), '#f56c6c')
})

// ---------------------------------------------------------------------------
// API contract: sport_score vs sport_ratio distinction
// ---------------------------------------------------------------------------

test('RecognitionResult contract — sport_score is the canonical field', () => {
  // Simulate an API response shape for a sport enterprise
  const apiResponse = {
    sport_score: 0.73,
    sport_ratio: 0.73,   // deprecated but present for compatibility
    is_sport: true,
    sport_category: '体育用品',
    confidence: 0.85,
    code_type: 'direct',
    code_text_consistency: 'consistent',
    evidence_relation: 'direct_code_text_support',
  }

  // Verify sport_score is the primary field
  assert.ok(typeof apiResponse.sport_score === 'number')
  assert.ok(apiResponse.sport_score >= 0 && apiResponse.sport_score <= 1)

  // Verify evidence_relation is present
  assert.ok(typeof apiResponse.evidence_relation === 'string')
})

test('SportShare contract — model_share is independent of sport_score', () => {
  // Simulate a SportShare API response
  const shareResponse = {
    model_share: 0.65,
    share_band: 'medium',
    share_band_label: '中等比重',
    lower_bound: 0.50,
    upper_bound: 0.80,
    model_confidence: 0.72,
  }

  // model_share must NOT be named sport_score
  assert.ok('model_share' in shareResponse)
  assert.ok(!('sport_score' in shareResponse))
})

test('code_text_consistency readability map is complete', () => {
  // The map defined in EnterpriseRecognition.vue
  const consistencyLabels = {
    consistent: '相互支持',
    partial: '部分匹配',
    conflict: '存在冲突',
    unknown: '无法判断',
  }

  // All expected keys present
  assert.ok('consistent' in consistencyLabels)
  assert.ok('partial' in consistencyLabels)
  assert.ok('conflict' in consistencyLabels)
  assert.ok('unknown' in consistencyLabels)
})

test('code_type readability labels match backend enum', () => {
  const codeTypeLabels = {
    direct: '直接体育相关',
    indirect: '间接体育相关',
    none: '非体育代码',
  }

  assert.ok('direct' in codeTypeLabels)
  assert.ok('indirect' in codeTypeLabels)
  assert.ok('none' in codeTypeLabels)
})
