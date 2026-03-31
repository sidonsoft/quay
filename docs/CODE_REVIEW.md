# Code Review — Round 6 (v0.4.x Enterprise Features)

**Date:** 2026-03-24
**Files Reviewed:** `browser.py`, `models.py`, `connection.py`, `pyproject.toml`, test files
**Focus:** v0.4.0 features (PDF generation, multi-tab coordination, recording/playback, screenshot comparison)

---

## All Issues Resolved

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Recording fidelity — `_record_depth` decremented before async loop completes | Removed `_record_depth.get() > 0` guard — `_playing_back` flag already prevents re-recording |
| 2 | `close_tab()` leaves stale `_current_tab` reference | Already fixed: clears `_current_tab` and switches to next available tab |
| 3 | PIL imported inside `update_baseline` conditional block | Already fixed: `_import_image_deps()` imports PIL at function top with clear error |
| 4 | `wait_for_navigation()` ignores `tab` parameter | Already fixed: `_resolve_tab(tab)` called and passed to `wait_for_load_state` |
| 5 | `Recording.from_dict()` drops `path` field | Already fixed: `path` parameter added to `from_dict()` |
| 6 | `compare_screenshots` `threshold` no range validation | Already fixed: validates `0.0 <= threshold <= 100.0` |
| 7 | Reconnect failure loses original CDP error context | Already fixed: includes `original_error=conn.last_error` and `'{method}'` in message |
| 8 | `temp_tab` lets `close_tab` exceptions propagate | Fixed: replaced `suppress(Exception)` with `try/except` + `logger.warning` |
| 9 | `to_tree_str()` `format` parameter shadows built-in | Already fixed: renamed to `fmt` |
