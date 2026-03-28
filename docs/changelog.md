# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.7] - 2026-03-29

### Fixed

- **Fix 01: ConnectionPool eviction closes WebSocket** — `_evict_oldest()` now properly awaits `conn.disconnect()` instead of just marking disconnected, preventing socket file descriptor leaks.
- **Fix 05: Screenshot comparison documentation** — Clarified byte-level comparison limitations, removed misleading threshold usage, added note about Pillow for pixel-level diffing.
- **Fix 07: Wait methods use async evaluate** — Added `_evaluate_async()` for use from async contexts. Fixed `RuntimeError` when sync `evaluate()` called from within `_poll_until()`.
- **Fix 08: Eager WeakKeyDictionary init** — `_enabled_domains` now initialized via `_init_cdp_mixin()` called from `BrowserCoreMixin.__init__`, preventing race conditions in concurrent access.
- **Fix 09: find_by_name word-boundary matching** — Added `exact` and `interactive_only` parameters. Substring matches now use word boundaries (e.g., "Sign" no longer matches "Design"). `click_by_text` defaults to `interactive_only=True`.
- **Fix 10: type_text clears content** — Added `clear=True` parameter (default). Now sends Ctrl+A + Backspace before typing, matching Playwright's `fill()` behavior for intuitive replacement.
- **Fix 12: CLI context manager** — All CLI commands now use `browser_context()` context manager for proper Browser cleanup and connection pool release.
- **Fix 13: Consistent CDP parsing** — Fixed `wait_for_load_state()` to use correct `result.result.value` nesting, matching `evaluate()` and `get_html()`.

## [0.2.6] - 2026-03-29

### Fixed

- **CRITICAL: evaluate() return value parsing** — CDP `Runtime.evaluate` returns `{"result": {"result": {"value": ...}}}`. The wrong nesting level caused `evaluate()` to always return `None`. Now correctly extracts `result.result.value`.
- **HIGH: click_by_text(0,0) fallback removed** — When an AXNode has no bounding box (e.g., `<title>`, `<meta>`), the code silently clicked at viewport origin (0,0), causing unpredictable behavior. Now raises `BrowserError` with helpful message.
- **Issue #6: Exception swallowing without logging** — All `except Exception: pass` blocks now log at DEBUG level for observability. WebSocket close errors, message parsing errors, callback errors, and health check failures are now logged.

## [Unreleased]

### Fixed

- **DES-1**: `wait_for*` methods now use async polling (`asyncio.sleep`) instead of blocking `time.sleep`
- **DES-2**: `_evict_oldest` no longer uses fire-and-forget `asyncio.create_task`
- **DES-3**: Age-based cleanup for stale pending futures (30s threshold)
- **DES-4**: CDP domain caching prevents redundant `Domain.enable` calls
- **DES-5**: `get_existing()` now checks connection state before returning
- **DES-6**: Recording playback uses action whitelist for security

## [0.2.5] - 2026-03-29

### Added

- 17 new tests for design issue fixes (DES-1 through DES-6)
- `PLAYBACK_ALLOWED_ACTIONS` whitelist for secure recording playback

### Changed

- `_poll_until()` async helper added to `BrowserWaitMixin`
- Domain cache via `WeakKeyDictionary` in `BrowserCDPMixin`
- `_pending_timestamps` tracking in `Connection` class

## [0.2.4] - 2026-03-29

### Added

- Comprehensive test suite: 105 tests across 12 modules
- `tests/test_design_fixes.py` — Tests for design issue fixes
- Full coverage: models, errors, escape, actions, accessibility, connection, wait, browser, navigation, recording, CLI

## [0.2.3] - 2026-03-29

### Fixed

- **BUG-1**: Added missing `get_html()` method to `BrowserActionsMixin`
- **BUG-2**: Fixed `click_by_text()` passing AXNode instead of Tab to `_get_connection()`
- **BUG-3**: Fixed `_parse_ax_nodes` field names (`id` → `ref`, removed `ignored`)
- **BUG-4**: Fixed `compare_screenshots` `ComparisonResult` field names
- **BUG-5**: Fixed `pyproject.toml` version to load dynamically from `_version.py`
- **Security**: `escape_js_string()` now returns properly quoted JSON strings

## [0.2.2] - 2026-03-28

### Added

- `py.typed` marker for PEP 561 type hint support
- Expanded `_KEY_MAP` with all common keys
- Cross-platform temp directory resolution in CLI

### Fixed

- `_run_async` RuntimeError in async contexts
- Eval path resolution for installed packages
- Safer JavaScript string escaping via `json.dumps()`

### Changed

- **Architecture**: Split monolithic `browser.py` into 8 mixin modules
- All public APIs unchanged — backward compatible

## [0.2.1] - 2026-03-27

### Fixed

- Cookie operations auto-derive URL from current tab
- `close_tab()` accepts both Tab object and tab ID string

## [0.2.0] - 2026-03-26

### Added

- Wait conditions: `wait_for_url`, `wait_for_selector_visible`, `wait_for_selector_hidden`, `wait_for_function`
- Cookie management: `get_cookies`, `set_cookies`, `delete_cookies`
- Network interception: `on_request`, `on_response`, `on_request_failed`
- Connection event system for CDP events

### Fixed

- Timeout boundary conditions in all wait methods
- Thread safety for network handlers
- Cookie validation

## [0.1.1] - 2026-03-25

### Fixed

- `type_text()` KeyError on `objectId`
- `click()` silently no-op fixed with proper CDP object targeting
- Connection pool LRU eviction
- Rate limiting for CDP calls
- Accessibility tree caching

## [0.1.0] - 2024-03-22

### Added

- Initial release
- Browser class for Chrome DevTools Protocol integration
- Tab management (list, new, activate, close)
- Accessibility tree parsing
- Element targeting by role and name
- Click by text functionality
- Screenshot capture
- JavaScript execution
- CLI interface
- Type hints and documentation