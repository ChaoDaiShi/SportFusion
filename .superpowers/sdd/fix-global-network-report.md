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

## Session-fixture ordering follow-up

### Root cause

The repository-root guard was function-scoped, but `tests/conftest.py` creates
the FastAPI `app` fixture at session scope. Pytest sets up higher-scoped
fixtures first, so application import could happen before the socket guard.

### RED

- Extended `backend/tests/test_network_isolation.py` with a scope assertion and
  safe fake-socket cases covering both `connect` and `connect_ex` for reserved
  non-loopback IPv4 and IPv6 destinations. No case performs real I/O.
- Before the fixture change, the focused test run failed exactly at the new
  assertion: `assert 'function' == 'session'` (`1 failed, 6 passed`).

### GREEN

- Converted `block_external_network` to a session-scoped autouse fixture.
- It now creates `pytest.MonkeyPatch()` directly, patches both socket methods
  for the full session, and calls `undo()` after `yield`; the function-scoped
  `monkeypatch` fixture is therefore not injected into a broader scope.
- Loopback and `localhost` handling remain unchanged.

### Ordering proof and verification

- `python -m pytest --setup-plan tests/api/test_api_smoke.py -q` reports:
  `SETUP S block_external_network` before `SETUP S app`, then tears down `app`
  before the network guard.
- Focused network regression: `7 passed in 0.08s`.
- API smoke: `2 passed, 1 xfailed, 7 warnings`; the sole xfail is P0-07.
- Full non-formal suite (with a worktree-local `--basetemp`, required because
  the sandbox cannot scan the system pytest temp directory):
  `42 passed, 2 deselected, 1 xfailed, 7 warnings in 6.12s`.
- Ruff: `ruff check conftest.py backend/core tests backend/tests alembic` ->
  `All checks passed!`.
