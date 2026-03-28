# Quay — Testing Strategy

## Overview

Quay requires a browser with remote debugging enabled. This creates unique testing challenges.

## Test Categories

### 1. Unit Tests (Mocked)

Purpose: Test internal logic without Chrome.
Location: `tests/test_*.py`
Run: `pytest tests/ -v`
Status: **All passing (105 tests)**
Coverage: AXNode parsing, error classes, connection pool logic, wait methods, recording, design fix tests

Test modules:
- `tests/test_models.py` — Tab, AXNode, Action, Recording, ComparisonResult
- `tests/test_errors.py` — BrowserError hierarchy and context
- `tests/test_escape.py` — JavaScript string escaping security
- `tests/test_actions.py` — Key definitions and input handling
- `tests/test_accessibility.py` — AXNode parsing and search
- `tests/test_connection.py` — OperationQueue, ConnectionState
- `tests/test_wait.py` — Wait method signatures and async polling
- `tests/test_browser.py` — Browser composition tests
- `tests/test_navigation.py` — Navigation and tab methods
- `tests/test_recording.py` — Recording save/load and playback whitelist
- `tests/test_cli.py` — CLI command tests
- `tests/test_design_fixes.py` — Tests for design issue fixes (DES-1 through DES-6)

### 2. Integration Tests (Real Chrome)

Purpose: Test against actual Chrome DevTools Protocol.
Location: Tests with `@pytest.mark.integration`
Run: `pytest tests/ -m integration`
Requirement: Chrome with `--remote-debugging-port=9222`
Status: Skipped by default

### 3. Smoke Tests (Quick Validation)

Purpose: Fast check that core functionality works.
Location: `tests/test_smoke.py`
Run: `pytest tests/test_smoke.py -v`

### 4. Live Tests (Full Workflow)

Purpose: End-to-end scenarios.
Location: `tests/test_live.py`
Run: `pytest tests/test_live.py -v --live`

---

## Running Tests

### Unit Tests Only (No Chrome)
```bash
pytest tests/ -v -m "not integration"
```

### With Chrome
```bash
# Start Chrome with debugging
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 &

# Run all tests
pytest tests/ -v
```

---

## Test Fixtures

Common fixtures in `tests/conftest.py`:

| Fixture | Purpose |
|---------|---------|
| `make_tab` | Factory for Tab objects |
| `make_ax_node` | Factory for AXNode objects |
| `sample_ax_tree` | Realistic 10-node tree for traversal tests |
| `chrome_version_response` | Mock `/json/version` response dict |
| `chrome_tabs_response` | Mock `/json/list` response list |
| `mock_websocket` | AsyncMock WebSocket connection |

## CI

GitHub Actions runs unit tests on Python 3.10, 3.11, 3.12. Integration tests run on push to main only (require Chrome installation in CI).

---

## Current Gaps

| Gap | Priority | Solution |
|-----|----------|----------|
| No live tests | High | Create `test_live.py` |
| No smoke tests | High | Create `test_smoke.py` |
| No performance tests | Medium | Create `test_perf.py` |