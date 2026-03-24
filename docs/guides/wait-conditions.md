# Wait Conditions

Quay provides flexible wait conditions for handling dynamic content.

## Basic Wait Methods

### wait_for()

The most versatile wait method. Accepts multiple keyword arguments:

```python
# Wait for element to exist
browser.wait_for(selector="#loading")

# Wait for text to appear
browser.wait_for(text="Welcome")

# Wait for URL
browser.wait_for(url="https://example.com/success")
```

### wait_for_load_state()

Wait for specific page load states:

```python
# Wait for page to fully load
browser.wait_for_load_state("complete")

# Wait for DOM ready
browser.wait_for_load_state("DOMContentLoaded")

# Wait for network idle
browser.wait_for_load_state("networkidle")
```

### wait_until()

Wait for custom condition:

```python
# Wait for JavaScript condition
browser.wait_until(lambda: browser.evaluate("document.readyState") == "complete")

# Wait for element count
browser.wait_until(lambda: len(browser.accessibility_tree().find_by_role("button")) > 3)
```

## Timeout Configuration

```python
# Default: 30 seconds
browser = Browser(timeout=30.0)

# Per-operation timeout
browser.wait_for(text="Done", timeout=5.0)
browser.wait_for(url="https://success", timeout=60.0)
```

## Error Handling

```python
from quay.errors import TimeoutError

try:
    browser.wait_for(text="Success", timeout=10.0)
except TimeoutError:
    print("Timed out waiting for Success")
```

## Examples

### Wait for Page Load

```python
browser.navigate("https://example.com")
browser.wait_for_load_state("complete")
```

### Wait for Element

```python
browser.click("Load More")
browser.wait_for(selector=".results .item:nth-child(10)")
```

### Wait for Navigation

```python
browser.click_by_text("Submit")
browser.wait_for(url="https://example.com/dashboard")
```

### Wait for AJAX

```python
browser.click("Refresh")
browser.wait_for(text="Updated: ")
```
