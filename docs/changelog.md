# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.6] - 2026-03-24

### Fixed

**Critical JavaScript Binding Fix**
- `Runtime.callFunctionOn` binds the resolved object to `this`, not as function argument
- Changed all JavaScript from `(function(el) {...})` to `function() {...this...}`
- Affected methods: `click()`, `type_text()`, `hover()`
- **Impact**: These methods now work correctly instead of silently returning `False`

**CDP Field Name Fix**
- Chrome CDP returns `backendDOMNodeId`, not `backendNodeId` or `backend_node_id`
- Fixed field name in 4 locations where accessibility node data is accessed

**Runtime.evaluate Result Parsing**
- CDP `Runtime.evaluate` returns `{"result": {"value": ...}}`, not `{"value": ...}`
- Fixed `wait_for_load_state`, `click_by_text`, `type_by_name`, `fill_form`

**Nested Async Fix**
- `click()` and `type_text()` now properly `await` Tasks returned by `click_by_text()`/`type_by_name()`
- Previously returned `Task` objects instead of `bool` when loop was running

**Tests Updated**
- Unit tests now use correct mock response structure
- Live tests use correct API (`type_text` not `type`)
- All 133 unit tests pass, all 21 live tests pass

## [0.2.5] - 2026-03-23

### Fixed

- **Ref validation**: Chrome CDP returns plain numeric IDs like `"30"` but `_validate_ref()` expected `"axnode@123"` format. Changed `AX_REF_PATTERN` from `^axnode@\d+$` to `^(axnode@)?\d+$` to accept both formats.

## [0.2.4] - 2026-03-23

### Fixed

- **Input.enable not supported**: Wrapped `Input.enable` CDP command in try/except to handle targets that don't support the Input domain
- **Async cleanup warnings**: Added `CancelledError` handling and disabled reconnect before `close()` to prevent "Task was destroyed" warnings

## [0.2.3] - 2026-03-23

### Added

**Automatic Reconnection**
- WebSocket reconnection: browser automatically recovers from connection drops
- Configurable retry strategy: `reconnect_max_retries` and `reconnect_backoff` parameters
- Reconnection monitoring: `reconnect_callback` for status updates
- State preservation: operations are queued during reconnection and replayed after recovery

### Fixed

- Resource safety: background reconnection tasks are cancelled and awaited in `Browser.close()`
- Pending task warnings: eliminated `Task was destroyed but it is pending` in tests

## [0.2.2] - 2026-03-23

### Added

**Keyboard Input**
- `press_key(key, modifiers=)` — Press a key with optional modifiers (Ctrl, Shift, Alt, Meta)
- `type_slowly(ref, text, delay=)` — Type text character by character with configurable delay

**Mouse Actions**
- `hover(ref)` — Hover over element by accessibility ref
- `click(ref, double=True)` — Double-click support
- `click(ref, button="right")` — Right-click (context menu) support

### Fixed

- CI/CD: All lint (ruff), type (mypy), and test checks passing
- Tests: Added `mock_check_connection` fixture for CI (Chrome not running)
- Tests: `real_connection_check` marker for tests that need real connection behavior

## [0.2.1] - 2026-03-23

### Fixed

**Cookie Operations**
- `set_cookies()`: Now auto-derives URL from current tab when neither `url` nor `domain` provided
- `delete_cookies()`: Derives URL from current tab when only `name` specified (CDP requires url/domain)
- `close_tab()`: Now accepts both `Tab` object and tab ID string

### Improved

- Simplified cookie handling - no need to specify URL/domain when setting cookies for current page
- Better test coverage for cookie derivation logic

## [0.2.0] - 2026-03-23

### Added

**Wait Conditions API**
- `wait_for_url(url=, pattern=)` — Wait for exact URL or regex pattern match
- `wait_for_selector_visible(selector)` — Wait for element to be visible
- `wait_for_selector_hidden(selector)` — Wait for element to be hidden/removed
- `wait_for_function(js_function)` — Wait for custom JavaScript predicate
- `wait_for_navigation(timeout, wait_until)` — Convenience for page loads

**Cookie Management API**
- `get_cookies(urls=)` — Get all cookies, optionally filtered by URLs
- `set_cookies(cookies)` — Set cookies with validation (name/value required)
- `delete_cookies(name=, url=, domain=, path=)` — Delete specific or all cookies

**Network Interception API**
- `on_request(callback)` — Monitor outgoing requests
- `on_response(callback)` — Monitor incoming responses
- `on_request_failed(callback)` — Handle failed requests
- `clear_interceptors()` — Remove all registered handlers

**Connection Event System**
- `Connection.on_event(method, callback)` — Register CDP event listener
- `Connection.off_event(method, callback)` — Unregister listener
- Event dispatch in `_receive_loop()` for async event handling

### Fixed

- Timeout boundary: changed `<` to `<=` in all wait methods for full timeout window
- Regex compilation: `wait_for_url()` compiles pattern once outside loop
- Event listeners: cleared on connection disconnect to prevent stale callbacks
- Thread safety: `_network_handlers` uses `setdefault` for atomic dict access
- Cookie validation: `set_cookies()` validates `name` and `value` keys

### Tests

- 25 new tests added (106 total, 20 skipped)
- Wait conditions: 13 tests
- Cookie management: 9 tests (including validation)
- Network interception: 7 tests

## [0.1.1] - 2026-03-23

### Fixed

**Critical Fixes**
- `type_text()` KeyError on `objectId` — DOM.resolveNode returns `{"object": {"objectId": ...}}`, not `{"node": {"nodeId": ...}}` (Round 3)
- `click()` silently no-op — Chrome accessibility tree has no `[data-ax-id]` attributes; fixed with proper CDP object targeting (Round 3)

**Medium Fixes**
- Connection pool limits with LRU eviction — added `max_connections=32` default with `ConnectionPool._evict_oldest()` (Round 2)
- Rate limiting for CDP calls — configurable `rate_limit` parameter prevents message flooding (Round 2)
- Rate limit race condition — moved `_last_send_time` assignment before sleep (Round 3)
- `wait_for_chrome_async` timeout boundary — changed `<` to `<=` for full timeout window (Round 4)
- `wait_for` raises on transient errors — wrapped `evaluate()` in try/except for resilience (Round 4)
- Accessibility tree caching — `cache_accessibility=True` with `refresh=True` to invalidate (Round 2)
- Multiple windows documentation — documented single-window limitation with workaround (Round 2)
- `to_dict()`/`to_json()` output methods — added to `AXNode` for structured output (Round 2)
- Python 3.9 compatibility — `from __future__ import annotations` + proper typing imports (Round 3)

**Low Fixes**
- Logging in `_http_put` — added debug logging for HTTP operations (Round 2)
- `__repr__` on `BrowserError` — added string representation for debugging (Round 2)
- CLI argparse + standard exit codes — `EXIT_SUCCESS=0`, `EXIT_ERROR=1`, `EXIT_USAGE=2`, `EXIT_INTERRUPT=130` (Round 2)
- `format` parameter shadows built-in — renamed to `fmt` in `AXNode.to_tree_str()` (Round 3)
- Eviction disconnect fire-and-forget — documented acceptable behavior (Round 3)

**Test Coverage**
- Improved test coverage to 84% (Round 2)

### Dependencies
- Python >= 3.9 (compatibility fix)

## [0.1.0] - 2024-03-22

### Added
- Initial release
- Browser class for Chrome DevTools Protocol integration
- Tab management (list, new, activate, close)
- Accessibility tree parsing (`Accessibility.getFullAXTree`)
- Element targeting by role and name
- Click by text functionality
- Form filling
- Screenshot capture
- JavaScript execution
- CLI interface
- Comprehensive type hints
- Documentation and examples

### Features
- **Your authenticated sessions**: Use Gmail, banking, SSO without re-auth
- **Accessibility tree**: Target elements like agent-browser (`[ref=e1]`)
- **Simple API**: Python class + CLI
- **Zero dependencies**: Only websockets package required

### Breaking Changes
- None (initial release)

### Dependencies
- Python
