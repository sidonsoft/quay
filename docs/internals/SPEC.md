# Quay — Specification

Chrome DevTools with accessibility-tree semantics for browser automation.

---

## Overview

Quay connects to Chrome via the Chrome DevTools Protocol (CDP), enabling browser automation that preserves your logged-in sessions (Gmail, GitHub, banking, SSO). Unlike Selenium/Playwright which spin up fresh browser instances, Quay uses Chrome you already have running with `--remote-debugging-port=9222`.

### Key Properties

| Property | Value |
|---|---|
| Language | Python >=3.10 |
| Dependencies | `websockets >= 12.0` only (stdlib + websockets) |
| Package | `quay/` |
| Entry point | `quay` CLI / `from quay import Browser` |
| License | MIT |

### Architecture

Quay is a single-package module:

```
quay/
├── __init__.py       # Public exports
├── __main__.py       # CLI entry point
├── browser.py        # Browser class (~4800 lines, all methods)
├── cli.py            # CLI commands
├── connection.py     # WebSocket connection pool
├── models.py         # Data models (Tab, AXNode, Recording, etc.)
├── errors.py         # Exception classes
├── evals.py          # Eval framework
└── _version.py       # Version number
```

The Browser class is monolithic — all functionality lives in `browser.py`. This avoids MRO complexity, circular import risk, and `# type: ignore` overhead that mixins introduce.

---

## Browser Lifecycle

### Constructor

```python
browser = Browser(host="localhost", port=9222, timeout=10.0)
```

Raises `ConnectionError` if Chrome is not reachable at the specified port.

### Launch (convenience)

```python
b = Browser.launch(
    headless=True,           # Run Chrome in headless mode
    stealth=True,            # Hide automation signals
    stealth_mode="basic",    # "basic" | "balanced" | "aggressive"
    block_trackers=True,     # Block known bot-detection domains
    port=9222,
    profile_path=None,       # Persistent profile dir (None = temp)
)
```

### Context Manager

```python
with Browser() as b:
    b.goto("https://example.com")
```

---

## Tab Management

### list_tabs() -> list[Tab]
Returns all open tabs.

### new_tab(url="about:blank") -> Tab
Opens a new tab. Navigates to `url` if provided and not `about:blank`.

### activate_tab(tab_id: str) -> bool
Brings tab to front.

### close_tab(tab: Tab | str | None = None) -> bool
Closes specified tab or current tab if None.

### temp_tab(url="about:blank", close_on_exit=True)
Context manager. Opens temp tab, yields it, closes on exit.

### switch_to_tab(tab: Tab | str, focus=True) -> Tab | None
Switches to tab, returns previous tab.

### current_tab -> Tab | None
Property. Gets/sets the current active tab.

### get_version() -> BrowserInfo
Returns Chrome version and protocol info.

---

## Navigation

### navigate(url: str, tab: Tab | None = None, timeout: float | None = None) -> str
Navigates tab to URL. Returns frame ID. Fires and returns immediately — use `goto()` to wait for load.

### goto(url: str) -> Tab
Creates new tab, navigates to URL, waits 0.5s for initial load. Returns the new tab.

---

## Wait Conditions

### wait_for(selector=None, text=None, tab=None, timeout=10.0, poll_interval=0.2) -> bool
Polls until `selector` (CSS) or `text` content appears. Use `wait_for_url()` for URL matching.

### wait_for_url(url=None, pattern=None, tab=None, timeout=10.0, poll_interval=0.2) -> bool
Waits until URL equals `url` or matches `pattern` (regex). Use `pattern` for partial/regex matching.

### wait_for_load_state(state="load", tab=None, timeout=10.0) -> bool
Waits for `document.readyState` to be "complete" ("load") or "interactive" ("DOMContentLoaded").

### wait_for_selector_visible(selector: str, timeout=10.0, poll_interval=0.2) -> bool
Waits until element is visible (display != none, visibility != hidden, offsetParent != null).

### wait_for_selector_hidden(selector: str, timeout=10.0, poll_interval=0.2) -> bool
Waits until element is hidden or removed.

### wait_for_function(js_function: str, timeout=10.0, polling_interval=0.2) -> bool
Polls until `js_function` returns truthy.

### wait_for_navigation(tab=None, timeout=10.0, wait_until="load") -> bool
Alias for `wait_for_load_state`. Waits for page to finish navigating.

---

## Accessibility Tree

### accessibility_tree(tab=None, timeout=None, refresh=False, cache=None) -> AXNode
Returns the full accessibility tree for the page. Uses Chrome's `Accessibility.getFullAXTree`.

```python
tree = browser.accessibility_tree()
links = tree.find_by_role("link")
buttons = tree.find_by_role("button")
node = tree.find("42")  # by ref (nodeId)
```

### AXNode

Properties: `ref`, `role`, `name`, `value`, `url`, `level`, `focused`, `description`, `children`, `bounding_box`

Methods:
- `find(ref: str) -> AXNode | None` — find by ref
- `find_by_role(role: str) -> list[AXNode]` — find all nodes with role
- `find_by_name(name: str, exact=False, interactive_only=False) -> list[AXNode]` — find by accessible name
- `find_by_value(value: str) -> list[AXNode]` — find by value substring
- `find_interactive() -> list[AXNode]` — find all interactive elements
- `to_tree_str(fmt="text") -> str` — render tree as string

### find_by_ref(ref: str, tab=None) -> AXNode | None
Convenience wrapper around `accessibility_tree().find()`.

### find_by_name(name: str, tab=None, timeout=None, *, exact=False, interactive_only=False) -> list[AXNode]
Find nodes by accessible name. `exact=True` for full string match. `interactive_only=True` skips non-interactive nodes.

### find_by_value(value: str, tab=None) -> list[AXNode]
Find nodes whose value contains the given string.

### get_links(tab=None) -> list[dict]
Returns all links as dicts with `{href, text, ref}`.

### get_text(ref=None, tab=None) -> str
Get text content of a node or the full page text.

### find_links(tab=None) -> list[dict]
Alias for `get_links()`.

### snapshot(tab=None) -> str
Returns formatted accessibility tree string for debugging.

---

## Click

### click(ref: str, tab=None, timeout=None, *, double=False, button="left") -> bool
Click element by accessibility `ref` (nodeId). Use `double=True` for double-click, `button="right"` for context menu.

### click_by_text(text: str, tab=None, timeout=None, *, double=False, button="left") -> bool
Click first element matching visible `text`. Uses accessibility tree — finds interactive elements with matching accessible name. `interactive_only=True` by default.

---

## Type

### type_text(text: str, tab=None, timeout=None, *, slowly=False, clear=True) -> bool
Types into the currently focused element. Sends Ctrl+A then Backspace before typing if `clear=True` (default). Use `slowly=True` for character-by-character with 50ms delay.

### type_by_name(name: str, text: str, tab=None, timeout=None) -> bool
Types into the first form element matching `name` (label, placeholder, aria-label, or name attribute).

### type_slowly(text: str | None = None, tab=None, timeout=None, **kwargs) -> bool
Character-by-character typing. Delegates to `type_text(slowly=True, ...)`.

### press_key(key: str, modifiers=0, tab=None, timeout=None) -> bool
Press a keyboard key. Supports named keys ("Enter", "Tab", "Escape", "ArrowDown", etc.) and single characters. `modifiers` is a bitmask: Ctrl=2, Alt=1, Shift=4, Meta=8.

---

## Mouse

### hover(ref: str, tab=None, timeout=None) -> bool
Move mouse to center of element's bounding box.

---

## Form Filling

### fill_form(fields: dict, tab=None, timeout=None) -> bool
Fill multiple form fields at once. `fields` maps names/labels/placeholders to values. Supports text inputs, checkboxes, radio buttons, selects, and textareas.

---

## Device Emulation

### emulate_device(device: str | dict, tab=None, viewport=None, user_agent=None) -> bool
Emulate a device. Pass a device name string ("iPhone 11", "iPad", "Nexus 6") or a full device descriptor dict. Optionally override viewport and user agent independently.

### get_emulated_device(tab=None) -> dict | None
Returns the currently emulated device descriptor or None.

---

## Content

### screenshot(path=None, tab=None, timeout=None, full_page=False) -> bytes | str
Capture PNG screenshot. If `path` is provided, saves to file and returns path. Otherwise returns raw bytes.

### compare_screenshots(baseline, current, threshold=0.01) -> ComparisonResult
Byte-level comparison of two screenshots. Returns `ComparisonResult` with `match`, `diff_percentage`, `message`. NOTE: byte-level only — for pixel diffing, install Pillow.

### screenshot_and_compare(baseline: str, path=None, tab=None, threshold=0.01, full_page=False) -> ComparisonResult
Captures current screenshot and compares to `baseline`. Saves current to `path` if provided.

### assert_visual_match(baseline: str, path=None, tab=None, threshold=0.01, full_page=False) -> bool
Like `screenshot_and_compare()` but raises `BrowserError` if screenshots don't match.

### pdf(path: str, tab=None, timeout=None, landscape=False, paper_width=8.5, paper_height=11.0, margin_top=0.4, margin_bottom=0.4, margin_left=0.4, margin_right=0.4, print_background=False, scale=1.0, page_ranges=None, header_template=None, footer_template=None, prefer_css_page_size=False) -> str
Generate PDF from page. Uses Chrome's Page.printToPDF.

### get_html(tab=None, timeout=None) -> str
Returns `document.documentElement.outerHTML`.

### evaluate(script: str, tab=None, timeout=None) -> Any
Execute JavaScript synchronously and return the result. `returnByValue=True` is used — return values are serialized via JSON.

---

## Cookies

### get_cookies(urls: list[str] | None = None, tab=None) -> list[dict]
Get all cookies, optionally filtered by URL list.

### set_cookies(cookies: dict | list[dict], tab=None) -> bool
Set one or more cookies. Accepts a single dict or list of dicts.

### delete_cookies(name: str | None = None, url: str | None = None, tab=None) -> bool
Delete cookies by name (and optionally URL). If `name` is None, deletes all cookies for URL.

### export_cookies(file_path: str, tab=None) -> None
Export cookies to JSON file (Netscape format).

### import_cookies(file_path: str, tab=None) -> None
Import cookies from JSON file (Netscape format).

---

## Network Interception

### on_request(callback: Callable, tab=None)
Register a callback for `Network.requestWillBeSent` events.

### on_response(callback: Callable, tab=None)
Register a callback for `Network.responseReceived` events.

### on_request_failed(callback: Callable, tab=None)
Register a callback for `Network.requestFailed` events.

### clear_interceptors(tab=None)
Clear all registered network callbacks.

---

## Session Recording & Playback

### start_recording(path=None) -> Recording
Start recording browser actions. Optional path for the recording file.

### stop_recording() -> str
Stop recording and return the JSON file path.

### pause_recording() / resume_recording()
Pause/resume the current recording.

### get_recording() -> Recording | None
Get the current recording object without stopping.

### playback(recording: Recording | str, speed=1.0, verify=False) -> bool
Play back a recorded session from a `Recording` object or JSON file path. `speed` multiplies playback rate. `verify=True` raises on failed actions.

---

## Stealth Mode

Stealth mode hides automation signals to prevent bot detection.

### get_stealth_mode() -> str
Returns current stealth level: "basic", "balanced", or "aggressive".

### is_stealth(tab=None) -> dict[str, Any]
Check if stealth mode is active by evaluating common detection signals:
- `navigator.webdriver` (should be undefined/false)
- `window.webdriver`
- `chrome.runtime`
- CDP marker (`cdc_adoQpoasnfa76pfcZLmcfl_Chart`)
- Puppeteer overlay objects

### Browser.__init__() also accepts:
- `stealth: bool` — enable/disable stealth mode
- `stealth_mode: str` — "basic", "balanced", "aggressive"
- `block_trackers: bool` — block known bot-detection domains via host blocklist

Stealth features: WebRTC leak prevention, media device spoofing, WebGL fingerprint randomization, font spoofing.

---

## Exception Hierarchy

```
BrowserError (base)
├── ConnectionError
├── TimeoutError
├── TabError
└── CDPError
```

---

## CLI Reference

```
quay [--browser=BROWSER] [--timeout=SECONDS] command [args]
```

| Command | Args | Description |
|---|---|---|
| `list` | — | List all open tabs |
| `new` | url | Open new tab |
| `snapshot` | — | Print accessibility tree |
| `screenshot` | path | Save screenshot |
| `html` | — | Print page HTML |
| `eval` | js | Execute JavaScript |
| `click` | text | Click element by text |
| `navigate` | url | Navigate current tab |
| `close` | id | Close tab by ID |
| `version` | — | Show Chrome version |
| `run-evals` | — | Run eval suite |

---

## Connection & Pooling

Browser maintains a `ConnectionPool` of WebSocket connections, one per tab. Connections are reused across CDP calls and automatically reconnected on disconnect.

- `is_connected() -> bool` — ping the CDP endpoint
- `wait_for_chrome(timeout=30.0) -> bool` — poll until Chrome is available
- `wait_for_chrome_async(timeout=30.0) -> bool` — async version
- `close() / aclose()` — close all connections and cleanup

---

## Implementation Status (v0.2.8)

All features implemented. No missing APIs.

---

## Security Considerations

1. **Localhost only** — CDP debugging on 9222 is localhost-only by default
2. **Arbitrary JS execution** — `evaluate()` runs whatever you pass
3. **No sandbox** — Quay uses your real Chrome session
4. **No authentication** — Anyone with localhost CDP access can automate your browser

---

Last updated: 2026-03-31
