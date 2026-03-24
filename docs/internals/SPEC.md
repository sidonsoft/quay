# Quay — Specification

Chrome DevTools with accessibility-tree semantics for browser automation.

---

## Overview

Quay connects to Chrome via the Chrome DevTools Protocol (CDP), enabling browser automation that preserves your logged-in sessions (Gmail, GitHub, banking, SSO). Unlike Selenium/Playwright which spin up fresh browser instances, Quay uses Chrome you already have running with --remote-debugging-port=9222.

### Key Properties

| Property | Value |
|---|---|
| Language | Python >=3.10 |
| Dependencies | websockets >= 12.0 only (stdlib + websockets) |
| Package | src/quay/ |
| Entry point | quay CLI / from quay import Browser |
| License | MIT |

---

## Architecture

Quay is organized into layers:

- Python API (browser.py) and CLI (cli.py)
- CDP Client Layer (HTTP for tab management, WebSocket for commands)
- Chrome DevTools Protocol (your Chrome instance)

---

## API Reference

### Browser(host, port, timeout)

Main browser automation class. Raises ConnectionError if Chrome is not reachable.

```python
from quay import Browser

browser = Browser()
browser = Browser(port=9223)
```

---

## Tab Management

### list_tabs()
Returns list of all open tabs.

### new_tab(url)
Opens a new tab and navigates to URL.

### activate_tab(tab_id)
Brings tab to front.

### close_tab(tab_id)
Closes specified tab or current tab.

### current_tab()
Returns the currently active tab.

### get_version()
Returns Chrome version and protocol info.

---

## Navigation

### navigate(url, tab=None)
Navigates current tab (or specified tab) to URL.

### goto(url)
Convenience: creates new tab, navigates, waits 0.5s for initial load.

---

## Wait Conditions

### wait_for(selector, text, url, timeout)
Polls until element selector, text content, or URL appears.

### wait_for_load_state(state)
Wait for page load state: "load", "DOMContentLoaded", "networkidle".

### wait_for_function(script)
Wait for JavaScript expression to return truthy value.

---

## Accessibility Tree

### accessibility_tree(tab=None)
Returns AXNode tree. Tree uses Chrome nodeId as ref for element targeting.

```python
tree = browser.accessibility_tree()
links = tree.find_by_role("link")
buttons = tree.find_by_role("button")
node = tree.find("42")
```

---

## Click

### click(ref, tab, timeout, double, button)
Click element by accessibility ref.

### click_by_text(text, tab, timeout)
Click first element matching visible text.

---

## Type

### type_text(ref, text, tab, timeout)
Type text into element by ref.

### type_by_name(name, text, tab, timeout)
Type by accessible name (label, placeholder, aria-label).

### type_slowly(ref, text, delay, tab, timeout)
Type character by character.

### press_key(key, modifiers, tab, timeout)
Press key or key combination.

---

## Mouse

### hover(ref, tab, timeout)
Hover over element by ref.

---

## Form Filling

### fill_form(fields, tab, timeout)
Fill multiple form fields by label/placeholder/name.

---

## Content

### screenshot(path, tab, timeout)
Capture PNG screenshot.

### get_html(tab)
Returns page outerHTML.

### evaluate(script, tab, timeout)
Execute JavaScript and return result.

---

## Cookies

### get_cookies(urls, tab)
Get all cookies or filtered by URLs.

### set_cookies(cookies, tab)
Set one or more cookies.

### delete_cookies(name, url, tab)
Delete specific or all cookies.

---

## Network Interception

### on_request(callback, tab)
Register callback for network requests.

### on_response(callback, tab)
Register callback for network responses.

### on_request_failed(callback, tab)
Register callback for failed requests.

### clear_interceptors(tab)
Clear all registered handlers.

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

Usage: quay command [args]

| Command | Args | Description |
|---|---|---|
| list | - | List all open tabs |
| new | url | Open new tab |
| snapshot | - | Print accessibility tree |
| screenshot | path | Save screenshot |
| html | - | Print page HTML |
| eval | js | Execute JavaScript |
| click | text | Click element by text |
| navigate | url | Navigate current tab |
| close | id | Close tabs |
| version | - | Show Chrome version info |

---

## Implementation Status (v0.2.6)

All core features implemented: tab management, navigation, accessibility tree, click/type, forms, cookies, network interception, CLI, type hints, tests.

---

## Security Considerations

1. Localhost only — CDP debugging on 9222 is localhost-only by default
2. Arbitrary JS execution — evaluate() runs whatever you pass
3. No sandbox — Quay uses your real Chrome session
4. No authentication — Anyone with localhost CDP access can automate your browser

---

## Design Decisions

### Why accessibility tree?
Semantic targeting (by role, name, label) instead of CSS selectors. Stable across page restructuring.

### Why WebSockets for commands?
CDP commands (Page.navigate, Accessibility.getFullAXTree, Runtime.evaluate) require bidirectional communication.

### Why stdlib + websockets only?
Minimal dependency surface.

---

Last updated: 2026-03-24
