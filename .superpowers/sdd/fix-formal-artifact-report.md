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
