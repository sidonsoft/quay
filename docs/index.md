# Quay

**Chrome DevTools with accessibility-tree semantics for browser automation.**

Use your authenticated Chrome sessions with agent-browser-style element targeting.

[![PyPI version](https://badge.fury.io/py/quay.svg)](https://badge.fury.io/py/quay)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](https://github.com/sidonsoft/quay/blob/main/LICENSE)

## Why Quay?

| Tool | Your Sessions | Accessibility Tree | Performance |
|------|---------------|---------------------|-------------|
| agent-browser | ❌ Fresh browser | ✅ Built-in refs | Fast |
| Playwright | ❌ Fresh browser | ❌ CSS selectors | Medium |
| Chrome DevTools | ✅ Your Chrome | ❌ Raw DOM | Fast |
| **Quay** | ✅ Your Chrome | ✅ Accessibility refs | Fast |

**Key advantage:** Use your Gmail, banking, SSO sessions without re-authenticating.

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
browser.navigate("https://github.com")

# Get accessibility tree (like agent-browser)
tree = browser.accessibility_tree()
print(tree.to_tree_str())

# Click by accessibility ref
browser.click("42")

# Or click by text
browser.click_by_text("Sign in")

# Fill form
browser.fill_form({"Email": "user@example.com", "Password": "secret"})

# Screenshot
browser.screenshot("/tmp/page.png")

# Execute JavaScript
title = browser.evaluate("document.title")
```

## Features

- ✅ **Your authenticated sessions** — Use Chrome you're already logged into
- ✅ **Accessibility tree** — Parse pages like agent-browser
- ✅ **Click by ref or text** — No brittle CSS selectors
- ✅ **Form filling** — Label association, name/id, placeholder
- ✅ **Wait conditions** — `wait_for(selector=)`, `wait_for(text=)`, `wait_for(url=)`
- ✅ **Cookies** — Get, set, delete cookies
- ✅ **Network interception** — Monitor requests/responses
- ✅ **Keyboard & mouse** — `press_key()`, `type_slowly()`, `hover()`
- ✅ **Automatic reconnection** — Recovers from WebSocket disconnects
- ✅ **Multi-tab support** — List, create, activate, close tabs
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
