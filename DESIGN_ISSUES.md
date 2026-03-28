# Quay Design Issue Fixes

**Repo:** https://github.com/sidonsoft/quay  
**Status:** Completed (v0.2.5)  
**Created:** 2026-03-29

---

## Summary

6 design issues systematically resolved:

| Issue | File | Status |
|-------|------|--------|
| DES-1 | `_browser_wait.py` | ✅ Fixed |
| DES-2 | `connection.py` | ✅ Fixed |
| DES-3 | `connection.py` | ✅ Fixed |
| DES-4 | `_browser_cdp.py` | ✅ Fixed |
| DES-5 | `connection.py` | ✅ Fixed |
| DES-6 | `_browser_recording.py` | ✅ Fixed |

---

## DES-1: Blocking `wait_for` polls with `time.sleep` and re-enters the event loop

**File:** `quay/_browser_wait.py`  
**Severity:** High  
**Status:** ✅ Fixed

**Problem:** 
- `wait_for`, `wait_for_url`, `wait_for_selector_visible`, `wait_for_selector_hidden`, `wait_for_function` use `time.sleep()` in loops
- Each iteration calls `self.evaluate()` which does `_run_async()` — spinning up/capturing event loop
- In async contexts this crashes (loop already running) or wastes time

**Solution:**
✅ Added `_poll_until()` async helper with `asyncio.sleep()`
✅ Converted all 6 wait methods to use async polling
✅ Added `poll_interval` parameter for configurability

---

## DES-2: `_evict_oldest` uses fire-and-forget `asyncio.create_task`

**File:** `quay/connection.py`  
**Severity:** Medium  
**Status:** ✅ Fixed

**Problem:**
- `_evict_oldest` creates tasks with `asyncio.create_task(conn.close())` but never awaits them
- Socket may still be open when `get_connection` returns
- Resource leak with no backpressure

**Solution:**
✅ Remove fire-and-forget `asyncio.create_task(conn.disconnect())`
✅ Synchronously mark connections as DISCONNECTED
✅ Actual cleanup happens on `close_all()` or GC

---

## DES-3: `_cleanup_stale_messages` checks by count, not age

**File:** `quay/connection.py`  
**Severity:** Medium  
**Status:** ✅ Fixed

**Problem:**
- Counts messages, doesn't track how long they've been pending
- Timed-out futures accumulate if receive loop dies

**Solution:**
✅ Added `_pending_timestamps` dict to track when each message was added
✅ Added `_STALE_AGE_SECONDS = 30.0` threshold
✅ Age-based cleanup removes futures older than threshold
✅ Sets exception on stale futures before removal

---

## DES-4: `_send_cdp` re-enables CDP domains on every call

**File:** `quay/_browser_cdp.py`  
**Severity:** Low  
**Status:** ✅ Fixed

**Problem:**
- Every `send_cdp()` call sends `Domain.enable` again
- Wastes round trips and clutters protocol logs

**Solution:**
✅ Added `_enabled_domains` WeakKeyDictionary (lazy init)
✅ Caches enabled domains per connection
✅ Only sends `Domain.enable` once per domain per connection
✅ Added `_clear_domain_cache()` for reconnection scenarios

---

## DES-5: `get_existing` returns disconnected connections

**File:** `quay/connection.py`  
**Severity:** Low  
**Status:** ✅ Fixed

**Problem:**
- Returns connections regardless of state
- Callers get dead sockets

**Solution:**
✅ Check `conn.state == ConnectionState.CONNECTED` before returning
✅ Return `None` for disconnected connections

---

## DES-6: Recording playback uses `getattr(self, action.type)`

**File:** `quay/_browser_recording.py`  
**Severity:** High  
**Status:** ✅ Fixed

**Problem:**
- Arbitrary method invocation via `getattr(self, action.type)`
- If recording contains `type: "_close_all"` it calls `self._close_all()`

**Solution:**
✅ Added `PLAYBACK_ALLOWED_ACTIONS` frozenset whitelist
✅ Only public browser actions allowed (no `_` prefix methods)
✅ Raises `BrowserError` for disallowed action types with clear message
✅ Documents security rationale in code comment