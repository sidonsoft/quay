# Quay Architecture

Quay is a **monolithic** single-package module with a flat file structure.

## Module Structure

```
quay/
├── __init__.py       # Public exports
├── __main__.py       # CLI entry point
├── browser.py        # Browser class (all methods)
├── cli.py            # CLI commands
├── connection.py     # WebSocket connection pool
├── models.py         # Data models (Tab, AXNode, Recording, etc.)
├── errors.py         # Exception classes
├── evals.py          # Eval framework
└── _version.py       # Version number
```

## Architecture

`Browser` is a single ~4,800-line class. All functionality lives in `browser.py`:

- **Tab management** — `new_tab`, `close_tab`, `list_tabs`, `activate_tab`, `temp_tab`
- **Navigation** — `navigate`, `goto`
- **CDP layer** — `_send_cdp`, `_get_connection`, `_run_async`
- **Accessibility** — `accessibility_tree`, `find_by_ref`, `find_by_role`, `find_by_name`
- **Actions** — `click`, `click_by_text`, `type_text`, `fill_form`, `press_key`, `hover`
- **Content** — `screenshot`, `get_html`, `evaluate`
- **Wait conditions** — `wait_for`, `wait_for_url`, `wait_for_load_state`, `wait_for_selector_*`
- **Cookies** — `get_cookies`, `set_cookies`, `delete_cookies`
- **Network** — `on_request`, `on_response`, `on_request_failed`
- **Recording** — `start_recording`, `stop_recording`, `playback`
- **Stealth/spoofing** — `stealth`, `webrtc_spoof`, `media_spoof`, `webgl_spoof`, `font_spoof`

## Why Flat?

- Single class means no method resolution order (MRO) complexity
- No circular import risk between mixins
- All internal methods accessible without `# type: ignore`
- Simpler to trace bugs — everything in one file
- Python's `dir()` gives complete API surface at a glance

The `quay/` directory previously contained dead mixin stub files (`_browser_core.py`, `_browser_tabs.py`, `_browser_navigation.py`, etc.) that were an incomplete architectural experiment. They were removed in v0.2.8.

## Layers

Quay is organized into three layers:

1. **Python API** (`browser.py`) and CLI (`cli.py`)
2. **CDP Client Layer** — HTTP for tab management (`urllib`), WebSocket for commands (`websockets`)
3. **Chrome DevTools Protocol** — your Chrome instance via `--remote-debugging-port=9222`

## Key Design Decisions

### Why accessibility tree for element targeting?
Semantic targeting (by `role`, `name`, `label`) instead of CSS selectors. Stable across page restructuring — CSS selectors break when developers restructure the DOM.

### Why WebSockets for commands?
CDP commands (`Page.navigate`, `Accessibility.getFullAXTree`, `Runtime.evaluate`) require bidirectional communication. HTTP alone can't handle this.

### Why stdlib + websockets only?
Minimal dependency surface. One package, one import.

### Why monolithic?
The Browser class is complex but its methods don't have conflicting dependencies. Splitting into mixins that reference each other via `TYPE_CHECKING` creates as many problems as it solves.

Last updated: 2026-03-31
