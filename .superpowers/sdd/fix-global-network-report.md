# Repository-wide network isolation: RED/GREEN evidence

## Scope

- Branch: `codex/phase0-safety-net`
- Base: `f61e792`
- Changed test infrastructure only; no production API, service, or Vue code changed.

## Root cause

Pytest only loads a `conftest.py` for tests below that file's directory. The
former autouse network fixture lived at `tests/conftest.py`, while
`pyproject.toml` collects both `tests` and sibling `backend/tests`. Therefore
the backend subtree did not receive the socket blocker. It also revealed that
the backend import-path setup had been scoped to `tests/conftest.py`.

## RED

1. Added `backend/tests/test_network_isolation.py` with a fake socket-shaped
   object, so its reserved address attempt cannot make a real connection.
2. Before adding the root blocker, running
   `python -m pytest backend/tests/test_network_isolation.py -q` failed because
   the C-level socket descriptor raised `TypeError` instead of the required
   `RuntimeError`. This proves `backend/tests` had no interceptor.
3. After the first minimal blocker, added IPv4 and IPv6 loopback expectations.
   The focused test then reported `2 failed, 1 passed`, because only
   `localhost` was initially recognized.

## GREEN

- Added repository-root `conftest.py`, so pytest applies the autouse blocker to
  both configured test roots.
- The blocker rejects non-loopback destinations through both `connect` and
  `connect_ex` with `RuntimeError` before calling the original socket method.
- `ipaddress.ip_address(...).is_loopback` preserves `127.0.0.1` and `::1`; the
  explicit `localhost` allowance preserves Windows TestClient behavior.
- Moved the shared `backend` `sys.path` setup into the root conftest and left
  `tests/conftest.py` with only its `app` and `client` fixtures, avoiding
  duplicate blocker/fixture ordering.

## Verification

- Focused network regression: `3 passed in 0.08s`.
- Backend tests: `7 passed in 0.10s`.
- API smoke: `2 passed, 1 xfailed`; the only xfail is P0-07.
- Full non-formal suite: `38 passed, 2 deselected, 1 xfailed, 7 warnings`.
- Ruff on the new root conftest and the CI lint surfaces is recorded in the
  final verification run.

The existing Pydantic class-config deprecation warnings are unchanged and do
not come from this test-infrastructure change.
