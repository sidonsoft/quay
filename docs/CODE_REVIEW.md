# Code Review — Round 6 (v0.4.x Enterprise Features)

**Date:** 2026-03-24
**Files Reviewed:** `browser.py`, `models.py`, `connection.py`, `pyproject.toml`, test files
**Focus:** v0.4.0 features (PDF generation, multi-tab coordination, recording/playback, screenshot comparison)

---

## Open Issues

### 1. Recording fidelity broken — `_record_depth` scope issue in compound async methods

**File:** `browser.py` → `wait_for_load_state()`

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

**File:** `browser.py` → `close_tab()`

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

### 3. PIL imported inside `update_baseline` conditional block

**File:** `browser.py` → `assert_visual_match()`

```python
if update_baseline:
    shutil.copy(current_path, baseline)
    from PIL import Image  # <- Only imported if update_baseline=True
```

If Pillow is not installed and `update_baseline=True`, this raises `ModuleNotFoundError` inside an exception handler, producing a confusing traceback. Should be imported at the top of the function (alongside the existing numpy import guard) or with a clear error message.

---

### 4. `wait_for_navigation()` ignores `tab` parameter

**File:** `browser.py` → `wait_for_navigation()`

```python
def wait_for_navigation(self, timeout: float = 10.0, wait_until: str = "load") -> bool:
    return self.wait_for_load_state(state=wait_until, timeout=timeout)
```

The docstring and method signature include `tab: Tab | None = None`, but it is not passed to `wait_for_load_state`. Calling `browser.wait_for_navigation(tab=some_tab)` waits on the *current* tab, not `some_tab`.

---

### 5. `Recording.from_dict()` silently drops `path` field

**File:** `models.py` → `Recording.from_dict()`

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

### 6. `threshold` parameter has no range validation

**File:** `browser.py` → `compare_screenshots()`

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

### 7. Reconnect failure loses original CDP error context

**File:** `browser.py` → `_send_cdp()`

```python
success = await conn.reconnect(...)
if not success:
    raise ConnectionError("Failed to reconnect...")  # Original error not included
```

If reconnect fails, the original CDP error (the *reason* reconnect was needed) is lost. The `ConnectionError` only says "failed to reconnect" without indicating which command failed or why. Should include the method name and/or preserve the original error.

---

### 8. `temp_tab` context manager lets `close_tab` exceptions propagate

**File:** `browser.py` → `temp_tab()`

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

### 9. `to_tree_str()` — `format` parameter shadows built-in

**File:** `models.py` → `AXNode.to_tree_str()`

```python
def to_tree_str(self, indent: int = 0, format: str = "text") -> str:
```

`format` shadows Python's built-in. Minor style issue — `fmt` or `output_format` would be clearer.

---

## Resolved

These issues were fixed in the Round 6 follow-up PR:

| # | Issue | Fix |
|---|-------|-----|
| 3 | `click(double=True)` silently fired single click | Fixed double-click dispatch to send two complete press/release cycles (clickCount=1 then 2) |
| CR-1 | Rate limit race (`_last_send_time` set before sleep) | Set after `asyncio.sleep()` |
| CR-2 | `call_soon(lambda: ensure_future(...))` dropped coroutine | Use `ensure_future()` directly |
| CR-3 | Tab leak on spoofing injection (unawaited `pool.remove`) | Now awaited |
| CR-4 | Stale futures not cancelled on timeout | Now cancelled before setting `TimeoutError` |
| CR-5 | `get_running_loop()` in network interceptor callback | Use stored `self._loop` |
| CR-6 | `OperationQueue` used `threading.Lock` in async code | Replaced with `asyncio.Lock` |
| CR-7 | Chrome subprocess `PIPE` deadlock risk | Redirect to `DEVNULL` |

---

## Summary Table

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | High | Recording fidelity broken — `_record_depth` decremented before async loop completes | Open |
| 2 | High | `close_tab` leaves stale `_current_tab` reference | Open |
| 3 | High | PIL imported inside `update_baseline` conditional block | Open |
| 4 | Medium | `wait_for_navigation` ignores `tab` parameter | Open |
| 5 | Low | `Recording.from_dict` drops `path` field | Open |
| 6 | Medium | `threshold` has no range validation | Open |
| 7 | Medium | Reconnect failure loses original error context | Open |
| 8 | Low | `temp_tab` context manager lets `close_tab` exceptions propagate | Open |
| 9 | Low | `format` parameter shadows built-in | Open |
