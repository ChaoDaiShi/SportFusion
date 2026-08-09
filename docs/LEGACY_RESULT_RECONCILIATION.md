# Legacy Result Reconciliation — Recognition Set Operations

## Canonical Values (Current Release)

Based on cross-verification of BATCH-20260803-R1, formal batch data,
and current algorithm definitions:

| Metric | Canonical Value | Source |
|--------|----------------|--------|
| Total enterprises | 76,687 | enterprise_dataset |
| Traditional direct-code | 8,016 | industry_code lookup |
| SportFusion candidates | 8,950 | sport_ratio_results |
| Intersection | 8,016 | Traditional ⊂ SportFusion |
| SportFusion only | 934 | 8950 - 8016 |
| Traditional only | 0 | — |
| Net increase | 934 | 934 - 0 |
| Coverage increase | 11.65% | 934 / 8016 |
| Crossover | 977 | 跨界类型 column |

## Candidate Source Structure

| Source | Count |
|--------|-------|
| Direct code base coverage | 8,016 |
| Pure text incremental | 878 |
| Indirect code confirmed | 56 |
| **Total** | **8,950** |

Outside direct code = 878 + 56 = 934

Crossover composition:
- Outside direct code: 934
- Direct code multi-business: 43
- **Total crossover**: **977**

## Legacy Historical Values (retained for reference only)

Prior reports and early Golden regression tests used these values:

| Metric | Legacy Value |
|--------|-------------|
| Intersection | 7,999 |
| SportFusion only | 951 |
| Traditional only | 17 |

No per-enterprise locked artifact has been found that independently
supports this specific set relationship. Current formal batch data
and algorithm definitions consistently produce the canonical values above.

The difference arises from:
1. All 8,016 traditional direct-code enterprises are identified
   as sport candidates by the current SportFusion pipeline
2. Legacy 7,999 intersection implies 17 traditional-code enterprises
   that SportFusion did NOT flag — no such enterprises exist in
   current batch data

## Semantic Note

The relationship Traditional ⊂ SportFusion is more accurately
represented as a nested/incremental structure rather than a
traditional Venn diagram overlap.

951 should ONLY appear as a legacy historical reference value.
It should not be redefined to represent any other metric.
