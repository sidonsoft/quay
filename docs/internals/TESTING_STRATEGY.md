# Quay — Testing Strategy

## Overview

Quay requires a browser with remote debugging enabled. This creates unique testing challenges.

## Test Categories

### 1. Unit Tests (Mocked)

Purpose: Test internal logic without Chrome.
Location: tests/test_*.py
Run: pytest tests/ -v
Status: All passing (46 tests)
Coverage: AXNode parsing, error classes, connection pool logic, HTTP API client

### 2. Integration Tests (Real Chrome)

Purpose: Test against actual Chrome DevTools Protocol.
Location: tests with @pytest.mark.integration
Run: pytest tests/ -m integration
Requirement: Chrome with --remote-debugging-port=9222
Status: Skipped by default

### 3. Smoke Tests (Quick Validation)

Purpose: Fast check that core functionality works.
Location: tests/test_smoke.py
Run: pytest tests/test_smoke.py -v

### 4. Live Tests (Full Workflow)

Purpose: End-to-end scenarios.
Location: tests/test_live.py
Run: pytest tests/test_live.py -v --live

---

## Running Tests

### Unit Tests Only (No Chrome)
pytest tests/ -v -m "not integration"

### With Chrome
~/scripts/chrome-debug.sh
pytest tests/ -v

---

## Test Fixtures

Chrome Fixture (tests/conftest.py):

```python
@pytest.fixture
def chrome():
    try:
        browser = Browser()
        yield browser
    except ConnectionError:
        pytest.skip("Chrome not running with --remote-debugging-port=9222")
    finally:
        browser.close()
```

---

## Current Gaps

| Gap | Priority | Solution |
|-----|----------|----------|
| No live tests | High | Create test_live.py |
| No smoke tests | High | Create test_smoke.py |
| No performance tests | Medium | Create test_perf.py |
