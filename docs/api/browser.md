# Browser API Reference

The main entry point for browser automation.

## Constructor

```python
from quay import Browser

browser = Browser(
    host="localhost",
    port=9222,
    timeout=10.0,
    retry_attempts=0,
    retry_delay=1.0,
    pool_rate_limit=None,
    cache_accessibility=False,
    reconnect=True,
    reconnect_max_retries=3,
    reconnect_backoff=1.0,
    reconnect_callback=None,
)
```

Raises `ConnectionError` if Chrome is not reachable.

## Tab Management

### list_tabs()
List all open page-type tabs. Returns `list[Tab]`.

### new_tab(url="about:blank")
Create a new tab. Navigates to URL if provided. Returns `Tab`.

### activate_tab(tab_id)
Bring tab to front. Returns `bool`.

### close_tab(tab=None)
Close a tab. Accepts `Tab`, tab ID string, or `None` (current tab). Returns `bool`.

### temp_tab(url="about:blank", close_on_exit=True)
Context manager for isolated tab workflows. Auto-closes on exit.

### switch_to_tab(tab, focus=True)
Switch to a tab. Returns the previous tab for switching back.

### get_version()
Returns `BrowserInfo` with Chrome version and protocol info.

## Navigation

### navigate(url, tab=None, timeout=None)
Navigate to URL. Returns `str` (frameId).

### goto(url, timeout=None, page_load_timeout=None)
Creates new tab, navigates, waits for page load. Returns `Tab`.

## Accessibility Tree

### accessibility_tree(tab=None, timeout=None, refresh=False, cache=None)
Get the full Chrome AX tree. Returns `AXNode`.

```python
tree = browser.accessibility_tree()
tree.find("42")              # By ref
tree.find_by_role("button")  # By role
tree.find_by_name("Submit")  # By name (case-insensitive)
tree.find_interactive()      # All interactive elements
```

## Actions

### click_by_text(text, tab=None, timeout=None, *, double=False, button="left")
Click element matching visible text. Returns `bool`.

### type_text(text, tab=None, timeout=None, *, slowly=False)
Type text into the focused element. Returns `bool`.

### evaluate(script, tab=None, timeout=None)
Execute JavaScript. Returns `Any`.

```python
title = browser.evaluate("document.title")
```

### screenshot(path=None, tab=None, timeout=None, full_page=False)
Capture screenshot. Returns `bytes` or `str` (file path if `path` provided).

```python
# Save to file
browser.screenshot("/tmp/page.png")

# Get as bytes
data = browser.screenshot()

# Full page
browser.screenshot("/tmp/full.png", full_page=True)
```

### compare_screenshots(baseline, current, threshold=0.01)
Compare two screenshots. Returns `ComparisonResult`.

```python
result = browser.compare_screenshots("baseline.png", "current.png")
if not result.match:
    print(f"Diff: {result.diff_percentage:.2f}%")
```

### get_html(tab=None, timeout=None)
Get page HTML. Returns `str`.

## Wait Conditions

### wait_for_load_state(state="load", tab=None, timeout=10.0)
Wait for page load. States: `"load"`, `"DOMContentLoaded"`. Returns `bool`.

### wait_for(selector=None, text=None, tab=None, timeout=10.0)
Wait for element or text. Returns `bool`.

```python
browser.wait_for(selector="#results")
browser.wait_for(text="Welcome")
```

### wait_for_url(url=None, pattern=None, tab=None, timeout=10.0)
Wait for URL. `url` for exact match, `pattern` for regex. Returns `bool`.

```python
browser.wait_for_url(url="https://example.com/dashboard")
browser.wait_for_url(pattern=r"/users/\d+")
```

### wait_for_selector_visible(selector, timeout=10.0)
Wait for element visibility. Returns `bool`.

### wait_for_selector_hidden(selector, timeout=10.0)
Wait for element to be hidden. Returns `bool`.

### wait_for_function(js_function, timeout=10.0, polling_interval=0.2)
Wait for JS condition. Returns `bool`.

```python
browser.wait_for_function("window.dataLoaded === true")
```

### wait_for_navigation(tab=None, timeout=10.0, wait_until="load")
Convenience for `wait_for_load_state`. Returns `bool`.

## Recording & Playback

### start_recording(path=None)
Start recording. Returns `Recording`.

### stop_recording()
Stop and save. Returns `str` (file path).

### pause_recording() / resume_recording()
Pause/resume action capture.

### get_recording()
Get current `Recording` or `None`.

### playback(recording, speed=1.0, verify=False)
Replay session. `recording` is `Recording` or file path. Returns `bool`.

**Whitelisted actions**: `open`, `navigate`, `navigate_back`, `close`, `tabs`, `new_tab`, `close_tab`, `click`, `type`, `press_key`, `eval`, `evaluate`, `screenshot`, `scroll`, `hover`, `drag`, `select_option`, `fill_form`, `file_upload`, `snapshot`, `wait_for`, `wait_for_url`, `wait_for_load_state`, `wait_for_selector_visible`, `wait_for_selector_hidden`, `wait_for_function`, `wait_for_navigation`.

## Connection

### is_connected()
Check Chrome reachability. Returns `bool`.

### close()
Close connections and clean up.

Context manager:
```python
with Browser() as browser:
    browser.navigate("https://example.com")
```

## Error Handling

```python
from quay.errors import BrowserError, ConnectionError, TimeoutError, CDPError

try:
    browser.navigate("https://example.com")
except ConnectionError as e:
    print(f"Chrome not reachable: {e}")
    print(f"Context: {e.context}")  # Dict with url, tab_id, etc.
except TimeoutError as e:
    print(f"Timed out after {e.timeout}s: {e.operation}")
except CDPError as e:
    print(f"CDP protocol error: {e}")
except BrowserError as e:
    print(f"Browser error: {e}")
```

See [Error Handling](errors.md) for full error hierarchy.