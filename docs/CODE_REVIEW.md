# Code Review — Round 6 (v0.4.x Enterprise Features)

**Date:** 2026-03-24
**Files Reviewed:** `browser.py`, `models.py`, `connection.py`, `pyproject.toml`, test files
**Focus:** v0.4.0 features (PDF generation, multi-tab coordination, recording/playback, screenshot comparison)

---

## Critical / High

### 1. Recording fidelity broken — `_record_depth` scope issue in compound async methods

**File:** `browser.py` \u2192 `wait_for_load_state()`

Compound async methods use this pattern:

```python
try:
    self._record_depth += 1
    return self._run_async(_wait())  # _wait() may still have pending CDP calls
finally:
    self._record_depth -= 1  # Decremented BEFORE async _wait() loop completes
```

The `finally` runs when `_wait()` *returns*, but `_wait()` is an async loop that may still be executing CDP operations. When those CDP calls complete and trigger `_record_action()`, `_record_depth` is already 0, so the guard `not _record_depth > 0` evaluates to True and recording proceeds.

**Impact:** Compound actions like `goto` and `wait_for_load_state` record their internal CDP steps as separate actions. A single `goto("https://example.com")` in a recording may produce multiple sub-actions (new_tab, accessibility tree, load state). Playback then replays each sub-action with its own timing and no compound semantics, breaking recording fidelity.

**Fix approach:** Remove the `_record_depth` guard entirely. The `_playing_back` flag already prevents re-recording during playback. Alternatively, scope `_record_depth` to truly synchronous call-stack depth, not async operation boundaries.

---

### 2. `close_tab()` leaves stale `_current_tab` reference

**File:** `browser.py` \u2192 `close_tab()`

```python
if tab_id:
    self._http_put(f"/json/close/{tab_id}")
    if self._pool:
        self._run_async(self._pool.remove(tab_id))
    return True
```

If the closed tab was `self._current_tab`, the reference is never cleared. Subsequent calls to `_get_current_tab()` return the stale closed tab. Should clear the reference when closing the active tab:

```python
if tab_id == self._current_tab?.id:
    self._current_tab = None
```

---

### 3. `click(double=True)` — parameter accepted but silently ignored

**Status: FIXED** (`browser.py`)

**File:** `browser.py` → `click()`

```python
def click(self, ref: str, ..., double: bool = False, ...) -> bool:
    self._record_action("click", ref=ref, ..., double=double, ...)
    # `double` and `button` are recorded but never passed to _click_async
    return self._click_async(ref, tab=tab, timeout=timeout)
```

`double=True` always fires a single left-click. The parameter should either work or not be recorded.

**Fix applied:** `Input.dispatchMouseEvent` now sends two complete press/release cycles — first with `clickCount=1`, second with `clickCount=2` — matching Chrome's expected double-click protocol.

---

### 4. PIL imported inside `update_baseline` conditional block

**File:** `browser.py` \u2192 `assert_visual_match()`

```python
if update_baseline:
    shutil.copy(current_path, baseline)
    from PIL import Image  # <- Only imported if update_baseline=True
```

If Pillow is not installed and `update_baseline=True`, this raises `ModuleNotFoundError` inside an exception handler, producing a confusing traceback. Should be imported at the top of the function (alongside the existing numpy import guard) or with a clear error message.

---

## Medium

### 5. `wait_for_navigation()` ignores `tab` parameter

**File:** `browser.py` \u2192 `wait_for_navigation()`

```python
def wait_for_navigation(self, timeout: float = 10.0, wait_until: str = "load") -> bool:
    return self.wait_for_load_state(state=wait_until, timeout=timeout)
```

The docstring and method signature include `tab: Tab | None = None`, but it is not passed to `wait_for_load_state`. Calling `browser.wait_for_navigation(tab=some_tab)` waits on the *current* tab, not `some_tab`.

---

### 6. `Recording.from_dict()` silently drops `path` field

**File:** `models.py` \u2192 `Recording.from_dict()`

```python
@classmethod
def from_dict(cls, data: dict) -> Recording:
    actions = [Action.from_dict(a) for a in data.get("actions", [])]
    return cls(
        actions=actions,
        version=data.get("version", "1.0"),
        # 'path' field from data is never restored
    )
```

The `path` field is not restored from saved recordings. If you load a recording with `Recording.from_dict()` and call `save()`, it writes to a temp file. Minor — not how the API is typically used.

---

### 7. `threshold` parameter has no range validation

**File:** `browser.py` \u2192 `compare_screenshots()`

```python
def compare_screenshots(self, baseline: str, current: str,
                        threshold: float = 0.0, ...) -> ComparisonResult:
```

`threshold` accepts any float. Negative values silently work (all comparisons return `False`), and values > 100 always return `match=True`. Should validate `0.0 <= threshold <= 100.0`:

```python
if not 0.0 <= threshold <= 100.0:
    raise ValueError("threshold must be between 0.0 and 100.0")
```

---

### 8. Reconnect failure loses original CDP error context

**File:** `browser.py` \u2192 `_send_cdp()`

```python
success = await conn.reconnect(...)
if not success:
    raise ConnectionError("Failed to reconnect...")  # Original error not included
```

If reconnect fails, the original CDP error (the *reason* reconnect was needed) is lost. The `ConnectionError` only says "failed to reconnect" without indicating which command failed or why. Should include the method name and/or preserve the original error.

---

## Low / Info

### 9. `temp_tab` context manager lets `close_tab` exceptions propagate

**File:** `browser.py` \u2192 `temp_tab()`

```python
@contextmanager
def temp_tab(self, url: str = "about:blank", close_on_exit: bool = True):
    tab = self.new_tab(url)
    try:
        yield tab
    finally:
        if close_on_exit:
            self.close_tab(tab)  # Exceptions here propagate to caller
```

If `close_tab` raises (e.g., `_http_put` fails), the exception propagates out of the context manager. This may be unexpected if the workflow succeeded but cleanup failed. Consider wrapping and logging instead of propagating cleanup failures.

---

### 10. `to_tree_str()` — `format` parameter shadows built-in

**File:** `models.py` \u2192 `AXNode.to_tree_str()`

```python
def to_tree_str(self, indent: int = 0, format: str = "text") -> str:
```

`format` shadows Python's built-in. Minor style issue — `fmt` or `output_format` would be clearer.

---

## What's Solid

| Area | Assessment |
|------|-----------|
| JS injection (`escape_js_string`) | Still correct — comprehensive escaping (backslash, quotes, backtick, newline, CR) |
| CDP error handling (`parse_cdp_error`) | Robust error extraction from CDP error responses |
| Connection pool reconnection | Well-implemented with backoff, callbacks, interceptor re-registration |
| PDF generation | `Page.printToPDF` with full parameter set, base64 encoding |
| Screenshot comparison | NumPy pixel diff with region crop, threshold, diff image generation |
| `type_by_name` / `_find_form_element` | Multi-strategy (name, id, placeholder, ARIA, label/for) |
| `assert_visual_match` | Proper update_baseline + verify flow |
| Test coverage | Good unit test coverage for all v0.4.x features (test_multitab, test_recording, test_compare, test_pdf) |
| Optional deps | `[compare]` extra properly defined with Pillow + numpy |

---

## Summary Table

| # | Severity | Issue |
|---|----------|-------|
| 1 | High | Recording fidelity broken — `_record_depth` decremented before async loop completes |
| 2 | High | `close_tab` leaves stale `_current_tab` reference |
| 3 | High | `click(double=True)` — `double` param recorded but never used |
| 4 | High | PIL imported inside `update_baseline` conditional block |
| 5 | Medium | `wait_for_navigation` ignores `tab` parameter |
| 6 | Low | `Recording.from_dict` drops `path` field |
| 7 | Medium | `threshold` has no range validation |
| 8 | Medium | Reconnect failure loses original error context |
| 9 | Low | `temp_tab` context manager lets `close_tab` exceptions propagate |
| 10 | Low | `format` parameter shadows built-in |
