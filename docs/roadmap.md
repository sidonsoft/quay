# Roadmap

Quay development timeline.

## v0.1.0 — Core ✅

**Goal**: Working browser automation with accessibility tree

- [x] Tab management (HTTP API)
- [x] Navigation
- [x] Accessibility tree parsing
- [x] Click/type by ref
- [x] Click by text
- [x] Form filling
- [x] Screenshot capture
- [x] JavaScript execution
- [x] CLI interface
- [x] Type hints
- [x] Unit tests
- [x] Documentation

## v0.2.0 — Polish ✅

**Goal**: Production-ready package

- [x] Better error handling
  - [x] Custom exception hierarchy (ConnectionError, TabError, TimeoutError, CDPError)
  - [x] Timeout handling (per-operation)
  - [x] WebSocket reconnection
- [x] Wait conditions
  - [x] `wait_for(selector=...)`
  - [x] `wait_for(text=...)`
  - [x] `wait_for(url=...)`
  - [x] `wait_until(condition=...)`
- [x] Cookies
  - [x] `get_cookies()`
  - [x] `set_cookies()`
  - [x] `delete_cookies()`
- [x] Network interception
  - [x] `on_request()`
  - [x] `on_response()`
  - [x] `on_request_failed()`
- [x] Keyboard input
  - [x] `press_key()` - Key press with modifiers (Ctrl+C, etc.)
  - [x] `type_slowly()` - Character-by-character typing
- [x] Mouse actions
  - [x] `hover()` - Hover over element
  - [x] Double-click (`click(ref, double=True)`)
  - [x] Right-click (`click(ref, button="right")`)
- [x] CI/CD (GitHub Actions)
  - [x] ruff linting
  - [x] mypy type checking
  - [x] pytest across Python 3.10-3.12
- [ ] Improved form detection
  - [ ] Label/for associations
  - [ ] Placeholder matching
  - [ ] ARIA labels

## v0.3.0 — Package ✅

**Goal**: Distributable package

- [x] PyPI upload
- [x] GitHub release automation
- [ ] Documentation site (MkDocs)
- [ ] Example scripts
- [ ] Comparison benchmarks

## v0.4.0 — Advanced

**Goal**: Enterprise features

- [ ] PDF generation — **Not implemented**
- [ ] Multi-tab coordination — **Not implemented**
- [x] Recording/Playback — Implemented (see known bugs in changelog)
- [x] Screenshot comparison — Basic byte comparison implemented

---

## Priority Matrix

| Feature | Priority | Status |
|---------|----------|--------|
| ~~PyPI publish~~ | ~~P0~~ | ✅ Done |
| ~~WebSocket reconnection~~ | ~~P1~~ | ✅ Done |
| Documentation site | P2 | Pending |
| Improved form detection | P2 | Pending |
| PDF generation | P3 | *Not implemented* |

## Effort Legend

- **Low**: < 100 lines, no new dependencies
- **Medium**: < 500 lines, minor complexity
- **High**: > 500 lines, complex CDP handling
