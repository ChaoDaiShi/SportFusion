# Formal Artifact Contract Gate Fix Report

## Scope

This change is limited to Phase 0 tests and test support. It does not add production
algorithm code or any file under `artifacts/formal/`.

The previous marked test parsed the artifact inline. It checked only selected values,
accepted distributions with the same sum, counted 24 passing audits without rejecting
extra failures, and verified SHA256 only for the fixed minimum file list. Consequently,
a recomputed manifest could certify legacy or semantically incorrect data.

## Test-first evidence

### RED 1: desired validator API

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\golden\test_formal_contract_validator.py -q --basetemp=.pytest-tmp-formal-contract-red-1
```

Result: `1 failed`. The valid synthetic artifact test failed because
`tests.golden.formal_contract` did not exist.

The minimal implementation introduced only the callable API. The valid-artifact test
then passed.

### RED 2: adversarial contract cases

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\golden\test_formal_contract_validator.py -q --basetemp=.pytest-tmp-formal-contract-red-3
```

Result: `55 failed, 1 passed`. Every mutation was incorrectly accepted by the minimal
validator. The failures covered provenance and metadata states, same-sum distribution
changes, all locked metric groups, audit integrity, duplicate keyed rows, and unsafe or
inexact SHA256 manifests.

### GREEN

Focused validator command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\golden\test_formal_contract_validator.py -q --basetemp=.pytest-tmp-formal-contract-green-3
```

Result: `56 passed`.

Golden suite command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\golden -q --basetemp=.pytest-tmp-formal-contract-golden
```

Result: `61 passed, 2 skipped`. Both marked real-artifact tests listed the complete
14-file minimum requirement in their skip reason.

Full normal-CI test command:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not formal_artifact" -q --basetemp=.pytest-tmp-formal-contract-full
```

Result: `98 passed, 2 deselected, 1 xfailed`. The xfail is the existing `P0-07` API
compatibility case. Seven existing Pydantic deprecation warnings remain.

Ruff command:

```powershell
.\.venv\Scripts\ruff.exe check backend\core tests alembic
```

Result: `All checks passed!`

## Follow-up: regional-share and CSV-header closure

This final follow-up remains test/support-only. No file under `artifacts/formal/`
was created or changed.

The validator now checks every region row, including any optional unresolved aggregate:
`scale_100m_cny` is finite and non-negative; `share` is finite and within `[0, 1]`;
and `share` equals `scale_100m_cny / official_total_100m_cny` to the existing
`1e-4` share tolerance. The established official-total, Chengdu, 21-mapped-row, and
top-five-share checks remain in place.

All three CSV schemas now require their documented headers in exact order. Duplicate
header diagnostics remain first, while missing and extra header diagnostics include
their respective field lists before the order-specific diagnostic is evaluated.

### Test-first evidence

RED command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\golden\test_formal_contract_validator.py -q --basetemp=.pytest-tmp-regional-header-red
```

Result: `8 failed, 122 passed`. The failures were five rehashed non-Chengdu row
mutations (`share=999`, negative scale, negative share, share above one, and
scale/share inconsistency) and rehashed header-order mutations for category, region,
and scenario CSV files.

Focused GREEN command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\golden\test_formal_contract_validator.py -q --basetemp=.pytest-tmp-regional-header-green-2
```

Result: `130 passed`.

Full non-formal command:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not formal_artifact" -q --basetemp=.pytest-tmp-regional-header-full
```

Result: `172 passed, 2 deselected, 1 xfailed, 7 warnings`. The xfail remains the
documented `P0-07` API compatibility case; the warnings are existing Pydantic
deprecation warnings.

Formal real-artifact command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\golden\test_formal_artifact.py -m formal_artifact -q -rs --basetemp=.pytest-tmp-regional-header-formal
```

Result: `2 skipped`; both skips state that the complete 14-file formal artifact,
including `SHA256SUMS`, is unavailable.

Ruff command:

```powershell
.\.venv\Scripts\ruff.exe check backend\core tests alembic
```

Result: `All checks passed!`

## Minimal schema decisions

- `batch_metadata.json` uses the Section 9.1 names directly. It requires formal mode,
  `formal-completed`, runtime/lock timestamps, non-placeholder version and model/config
  identifiers, the four specified SHA256 values, and explicit threshold, alpha, and
  official-total references.
- `input_manifest.json` repeats batch number, formal mode, source mode, and input digest.
  `inputs` is a non-empty list of objects with `path`, `sha256`, and `provenance`. At
  least one declared input digest must bind the top-level batch input digest.
- SportShare source counts are held in a `sources` object and accompanied by
  `total_share_results`. This makes exact keyed comparison possible without treating
  unrelated summary metadata as a source category.
- Category, region, and scenario CSV records are keyed by `category`, `region`, and
  `scenario_id`. Duplicate keys are rejected before aggregate checks.
- Binary metrics expose `binary_evaluable` and `reference_labels`; category metrics
  expose `category_evaluable`. These fixture-backed denominators are required rather
  than inferred.
- `SHA256SUMS` accepts standard text/binary separators, requires safe relative POSIX
  paths, rejects duplicates/absolute/traversal paths, and must equal the recursive set
  of every actual file except `SHA256SUMS` itself. Hashes are calculated from raw bytes.

The synthetic valid artifact includes one extra recursively nested evidence file to
prove that coverage is not limited to `REQUIRED`. Synthetic artifacts are created only
under pytest temporary directories and contain no claim of real formal results.

## Follow-up: formal-contract ambiguity closure

### Scope and source locks

This follow-up remains test/support-only. It adds no real formal artifact and no
production algorithm code. The Golden fixture gained only two source-locked region
invariants: exactly 21 mapped city/prefecture rows and a top-five share of `0.7227`.
Unknown city names/values and unknown interior scenario outputs were not added to the
fixture. The valid artifact builder creates synthetic region values only inside pytest
temporary directories.

The minimal formal schema is now explicit:

- input provenance is the typed exact string `formal`; marker tokens `legacy`, `demo`,
  `test`, `historical`, `synthetic`, `mock`, and `fallback` are rejected case-insensitively
  in identifiers and normalized input paths, and any processed-batch path is rejected;
- lock timestamps are timezone-aware ISO-8601 values ordered as
  `start_time <= end_time <= locked_at`; `runtime_env_json` is a nonempty object;
- region CSV rows use exact headers `region,scale_100m_cny,share,mapping_status`, with
  exactly 21 `mapped` rows; an optional unresolved aggregate uses the exact key
  `__UNRESOLVED__` and `mapping_status=unresolved` and is excluded from CR5;
- scenario CSV rows use the exact 3 x 4 grid
  `{conservative,baseline,expanded} x {0,.10,.20,.30}` and IDs formatted as
  `{evidence_profile}-alpha-{alpha:.2f}`; only the baseline, official total, and global
  minimum/maximum remain numerically locked;
- JSON parsing rejects duplicate keys at every object level; each CSV uses a documented
  exact unique header set and exact row keys;
- each of exactly 24 unique audit checks contains `check_id`, `name`, `status`,
  `expected`, `actual`, and `detail`; every status is `PASS`, text fields are nonempty,
  and expected/actual values are finite JSON scalars.

### Test-first evidence

RED command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\golden\test_formal_contract_validator.py -q --basetemp=.pytest-tmp-formal-ambiguity-red
```

Result: `48 failed, 56 passed`. Failures reproduced the permissive provenance/path,
timestamp/runtime, region/scenario, serialization, and audit-record bypasses. Raw JSON
and CSV mutations bypassed the helper writers while retaining recomputed SHA manifests.

Focused GREEN command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\golden\test_formal_contract_validator.py -q --basetemp=.pytest-tmp-formal-ambiguity-focused-final
```

Result: `122 passed`.

Full non-formal command:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not formal_artifact" -q --basetemp=.pytest-tmp-formal-ambiguity-full
```

Result: `164 passed, 2 deselected, 1 xfailed`. The xfail remains the documented `P0-07`
API compatibility case. Seven existing Pydantic deprecation warnings remain.

Formal real-artifact command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\golden\test_formal_artifact.py -m formal_artifact -q -rs --basetemp=.pytest-tmp-formal-ambiguity-formal
```

Result: `2 skipped`; both skip reasons list all 14 required formal files, including
`SHA256SUMS`. No real formal artifact was created.

Ruff command:

```powershell
.\.venv\Scripts\ruff.exe check backend\core tests alembic
```

Result: `All checks passed!`
