# Quay

**Chrome DevTools with accessibility-tree semantics for browser automation.**

Use your authenticated Chrome sessions with agent-browser-style element targeting.

[![PyPI version](https://badge.fury.io/py/quay.svg)](https://badge.fury.io/py/quay)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](https://github.com/sidonsoft/quay/blob/main/LICENSE)

## Why Quay?

| Tool | Your Sessions | Accessibility Tree | Performance |
|------|---------------|---------------------|-------------|
| agent-browser | ❌ Fresh browser | ✅ Full CDP tree + refs | Fast |
| Playwright | ❌ Fresh browser | ⚠️ Simplified snapshot | Medium |
| Chrome DevTools | ✅ Your Chrome | ❌ Raw protocol only | Fast |
| **Quay** | ✅ Your Chrome | ✅ Full CDP tree + refs | Fast |

**Key advantage:** Use your Gmail, banking, SSO sessions without re-authenticating. Full Chrome accessibility tree for semantic element targeting with `ref` IDs.

## Installation

```bash
pip install quay
```

## Quick Start

```python
from quay import Browser

# Connect to your Chrome (must be running with --remote-debugging-port=9222)
browser = Browser()

# Navigate
browser.goto("https://github.com")
# Or: browser.navigate("https://github.com")

# Get accessibility tree (like agent-browser)
tree = browser.accessibility_tree()
print(tree.to_tree_str())

# Find elements by role
buttons = tree.find_by_role("button")

# Click by visible text
browser.click_by_text("Sign in")

# Type into focused element
browser.click_by_text("Email")
browser.type_text("user@example.com")

# Screenshot
browser.screenshot("/tmp/page.png")

# Wait for conditions
browser.wait_for(text="Welcome")
browser.wait_for_url(pattern=r"/dashboard")
```

## Features

- ✅ **Your authenticated sessions** — Use Chrome you're already logged into
- ✅ **Accessibility tree** — Full CDP accessibility tree with ref targeting
- ✅ **Click by text** — Click elements by visible text
- ✅ **Wait conditions** — `wait_for(selector=)`, `wait_for(text=)`, `wait_for(url=)`
- ✅ **Multi-tab support** — List, create, activate, close tabs
- ✅ **Recording & playback** — Record sessions for replay
- ✅ **Screenshot comparison** — Basic byte-by-byte comparison
- ✅ **Automatic reconnection** — Recovers from WebSocket disconnects
- ✅ **Type hints** — Full type hint coverage
- ✅ **Python 3.10+** — Modern async/await

## Prerequisites

Chrome must be running with remote debugging enabled:

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 &

# Linux
google-chrome --remote-debugging-port=9222 &

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

## Documentation

- [Installation Guide](installation.md)
- [Quick Start](quickstart.md)
- [API Reference](api/browser.md)
- [Changelog](changelog.md)
- [Roadmap](roadmap.md)

## License

Apache-2.0 — see [LICENSE](https://github.com/sidonsoft/quay/blob/main/LICENSE)
