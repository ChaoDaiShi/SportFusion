# SportFusion Formal Reproduction Guide

## Prerequisites

- Python 3.11
- uv (Python package manager)
- Node.js 24+ (frontend)

## Quick Start

```bash
# 1. Clone and install
git clone <repo>
cd <repo>
uv sync --locked
cd frontend && npm ci && cd ..

# 2. Initialize DB (new/temp only — never migrate production DB)
uv run alembic upgrade head

# 3. Verify formal artifacts
python scripts/reproduce_formal.py --dry-run

# 4. Run full reproduction pipeline
python scripts/reproduce_formal.py --skip-missing

# 5. Run tests
uv run pytest backend/tests/ -m "not formal_artifact"
uv run pytest backend/tests/formal_golden/ -v  # Golden tests (skips if missing)

# 6. Frontend
cd frontend && npm run build
```

## Key Concepts

- **SportScore** = 体育业务证据评分 [0,1] — recognition evidence, not revenue share
- **SportShare** = 体育经营活动结构比重估计值 — structural estimate, not revenue %
- **Scale** = Official total constrained structural allocation (2170.80亿元)
- **Formal** = Uses real artifacts only, never falls back to demo

## Missing Artifacts

If formal artifacts are missing, Golden regression tests will SKIP.
No synthetic data is generated to pass tests.

See `docs/FORMAL_ARTIFACTS.md` for artifact status.
