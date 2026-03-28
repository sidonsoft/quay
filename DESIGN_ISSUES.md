# Quay Design Issue Fixes

**Repo:** https://github.com/sidonsoft/quay  
**Status:** In Progress  
**Created:** 2026-03-29

---

## Summary

6 design issues identified for systematic resolution:

| Issue | File | Status |
|-------|------|--------|
| DES-1 | `_browser_wait.py` | Pending |
| DES-2 | `connection.py` | Pending |
| DES-3 | `connection.py` | Pending |
| DES-4 | `_browser_cdp.py` | Pending |
| DES-5 | `connection.py` | Pending |
| DES-6 | `_browser_recording.py` | Pending |

---

## DES-1: Blocking `wait_for` polls with `time.sleep` and re-enters the event loop

**File:** `quay/_browser_wait.py`  
**Severity:** High  
**Status:** Pending

**Problem:** 
- `wait_for`, `wait_for_url`, `wait_for_selector_visible`, `wait_for_selector_hidden`, `wait_for_function` use `time.sleep()` in loops
- Each iteration calls `self.evaluate()` which does `_run_async()` — spinning up/capturing event loop
- In async contexts this crashes (loop already running) or wastes time

**Solution:**
Convert all polling methods to use a single `_poll_until()` async helper with `asyncio.sleep()`.

---

## DES-2: `_evict_oldest` uses fire-and-forget `asyncio.create_task`

**File:** `quay/connection.py`  
**Severity:** Medium  
**Status:** Pending

**Problem:**
- `_evict_oldest` creates tasks with `asyncio.create_task(conn.close())` but never awaits them
- Socket may still be open when `get_connection` returns
- Resource leak with no backpressure

**Solution:**
- Use synchronous close in `_evict_oldest` via `asyncio.run_coroutine_threadsafe` or track closures

---

## DES-3: `_cleanup_stale_messages` checks by count, not age

**File:** `quay/connection.py`  
**Severity:** Medium  
**Status:** Pending

**Problem:**
- Counts messages, doesn't track how long they've been pending
- Timed-out futures accumulate if receive loop dies

**Solution:**
- Add `_pending_timestamps` dict to track when each message was added
- Age-based cleanup: remove pending futures older than 30 seconds

---

## DES-4: `_send_cdp` re-enables CDP domains on every call

**File:** `quay/_browser_cdp.py`  
**Severity:** Low  
**Status:** Pending

**Problem:**
- Every `send_cdp()` call sends `Domain.enable` again
- Wastes round trips and clutters protocol logs

**Solution:**
- Add `_enabled_domains` per-connection cache
- Only send `Domain.enable` once per domain per connection

---

## DES-5: `get_existing` returns disconnected connections

**File:** `quay/connection.py`  
**Severity:** Low  
**Status:** Pending

**Problem:**
- Returns connections regardless of state
- Callers get dead sockets

**Solution:**
- Check `conn.state == ConnectionState.CONNECTED` before returning

---

## DES-6: Recording playback uses `getattr(self, action.type)`

**File:** `quay/_browser_recording.py`  
**Severity:** High  
**Status:** Pending

**Problem:**
- Arbitrary method invocation via `getattr(self, action.type)`
- If recording contains `type: "_close_all"` it calls `self._close_all()`

**Solution:**
- Whitelist allowed action types
- Map action types to methods explicitly