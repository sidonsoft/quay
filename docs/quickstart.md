# Quick Start

## 1. Connect to Chrome

```python
from quay import Browser

browser = Browser()
```

Chrome must be running with `--remote-debugging-port=9222`. See [Installation](installation.md).

## 2. Navigate Pages

```python
# Open a new tab and navigate
tab = browser.new_tab("https://example.com")

# Navigate current tab
browser.navigate("https://github.com")

# Or use goto (creates tab + navigates + waits)
tab = browser.goto("https://example.com")

# Wait for page load
browser.wait_for_load_state("load")
```

## 3. Use the Accessibility Tree

```python
tree = browser.accessibility_tree()
print(tree.to_tree_str())

# Find elements by role
links = tree.find_by_role("link")
buttons = tree.find_by_role("button")

# Search by name (case-insensitive substring)
submit = tree.find_by_name("Submit")

# Find by ref ID
node = tree.find("42")

# All interactive elements
interactive = tree.find_interactive()
```

## 4. Interact with Pages

```python
# Click by visible text
browser.click_by_text("Sign in")
browser.click_by_text("Submit")

# Double-click
browser.click_by_text("Edit", double=True)

# Right-click
browser.click_by_text("Options", button="right")

# Type into the focused element
browser.click_by_text("Search")
browser.type_text("hello world")

# Type slowly
browser.type_text("slow typing", slowly=True)

# Execute JavaScript
browser.evaluate("document.querySelector('#btn').click()")
```

## 5. Wait for Conditions

```python
# Wait for element
browser.wait_for(selector="#results")

# Wait for text
browser.wait_for(text="Welcome back")

# Wait for exact URL
browser.wait_for_url(url="https://example.com/dashboard")

# Wait for URL pattern (regex)
browser.wait_for_url(pattern=r"/users/\d+")

# Wait for element visible
browser.wait_for_selector_visible("#modal")

# Wait for element hidden
browser.wait_for_selector_hidden("#loading")

# Wait for JS condition
browser.wait_for_function("window.dataLoaded === true")

# Wait for page load
browser.wait_for_load_state("load")
```

## 6. Extract Content

```python
# Page HTML
html = browser.get_html()

# JavaScript results
title = browser.evaluate("document.title")
url = browser.evaluate("window.location.href")

# Screenshot
browser.screenshot("/tmp/page.png")
browser.screenshot("/tmp/full.png", full_page=True)
```

## 7. Work with Tabs

```python
# List tabs
tabs = browser.list_tabs()

# New tab
new_tab = browser.new_tab("https://github.com")

# Switch tabs (returns previous)
previous = browser.switch_to_tab(new_tab)
browser.switch_to_tab(previous)

# Temporary tab (auto-closes)
with browser.temp_tab("https://example.com") as tab:
    tree = browser.accessibility_tree()

# Close tab
browser.close_tab(new_tab)
```

## 8. Record and Replay

```python
browser.start_recording()

browser.goto("https://example.com")
browser.click_by_text("Login")
browser.type_text("user@example.com")

path = browser.stop_recording()
browser.playback(path, speed=2.0, verify=True)
```

## 9. Handle Disconnections

```python
# Default: auto-reconnect enabled
browser = Browser()

# Customize
browser = Browser(
    reconnect=True,
    reconnect_max_retries=5,
    reconnect_backoff=0.5,
    reconnect_callback=lambda msg: print(f"Reconnection: {msg}"),
)

# Check connection
if browser.is_connected():
    print("Ready")
```

## 10. Error Handling

```python
from quay.errors import BrowserError, ConnectionError, TimeoutError

try:
    browser.goto("https://example.com")
except ConnectionError as e:
    print(f"Connection failed: {e}")
    print(f"Details: {e.context}")  # Dict with url, tab_id, etc.
except TimeoutError as e:
    print(f"Operation timed out after {e.timeout}s")
except BrowserError as e:
    print(f"Browser error: {e}")
```

## 11. Advanced: Direct CDP Access

```python
# Send raw CDP commands
result = browser.send_cdp(
    "Page.navigate",
    {"url": "https://example.com"}
)

# Low-level connection access
conn = await browser._get_connection(tab)
await conn.send("Runtime.evaluate", {"expression": "1 + 1"})
```

## Next Steps

- [API Reference](api/browser.md) — Full method documentation
- [Accessibility Tree](guides/accessibility.md) — Deep dive on AXNode
- [Wait Conditions](guides/wait-conditions.md) — All wait methods
- [Recording](guides/recording.md) — Session recording details