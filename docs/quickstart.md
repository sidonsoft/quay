# Quick Start

## 5-Minute Tutorial

### 1. Connect to Chrome

```python
from quay import Browser

browser = Browser()
```

### 2. Navigate Pages

```python
# Open a new tab
tab = browser.new_tab("https://example.com")

# Navigate current tab
browser.navigate("https://github.com")

# Wait for page load
browser.wait_for_load_state("complete")
```

### 3. Use the Accessibility Tree

```python
# Get the accessibility tree
tree = browser.accessibility_tree()

# Print tree structure
print(tree.to_tree_str())

# Find elements
links = tree.find_by_role("link")
headings = tree.find_by_role("heading")
buttons = tree.find_interactive()

# Search by name or text
submit_btn = tree.find_by_name("Submit")
login_link = tree.find("42")  # By ref
```

### 4. Interact with Pages

```python
# Click by accessibility ref
browser.click("42")

# Click by visible text
browser.click_by_text("Sign in")

# Type into input
browser.type_text("email-input", "user@example.com")

# Fill multiple form fields
browser.fill_form({
    "Email": "user@example.com",
    "Password": "secret"
})

# Press keys
browser.press_key("Enter")
browser.press_key("c", modifiers=["Control"])  # Ctrl+C

# Hover over element
browser.hover("42")

# Double-click
browser.click("42", double=True)

# Right-click
browser.click("42", button="right")
```

### 5. Wait for Conditions

```python
# Wait for element to appear
browser.wait_for(selector="#loading")

# Wait for text to appear
browser.wait_for(text="Welcome")

# Wait for URL
browser.wait_for(url="https://example.com/success")

# Wait for page load state
browser.wait_for_load_state("complete")

# Custom condition
browser.wait_until(lambda: browser.evaluate("document.readyState") == "complete")
```

### 6. Extract Content

```python
# Get page HTML
html = browser.get_html()

# Execute JavaScript
title = browser.evaluate("document.title")
url = browser.evaluate("window.location.href")

# Take screenshot
browser.screenshot("/tmp/page.png")

# Get cookies
cookies = browser.get_cookies()

# Set cookies
browser.set_cookies([{"name": "session", "value": "abc123"}])
```

### 7. Work with Tabs

```python
# List all tabs
tabs = browser.list_tabs()

# Open new tab
new_tab = browser.new_tab("https://github.com")

# Switch tabs
browser.activate_tab(tabs[0])

# Close tab
browser.close_tab(new_tab)
```

### 8. Handle Disconnections

Quay automatically reconnects when the WebSocket connection drops:

```python
# Automatic reconnection (default)
browser = Browser()

# Customize reconnection
browser = Browser(
    reconnect=True,
    reconnect_max_retries=5,
    reconnect_backoff=0.5,  # seconds
)

# Get connection status
if browser.is_connected():
    print("Connected")
```

## Complete Example

```python
from quay import Browser

# Connect and navigate
browser = Browser()
browser.new_tab("https://example.com")

# Get accessibility tree
tree = browser.accessibility_tree()
print(tree.to_tree_str())

# Find and click a link
login_link = tree.find_by_name("Login")[0]
browser.click(login_link.ref)

# Wait for page
browser.wait_for(text="Sign In")

# Fill login form
browser.fill_form({
    "Username": "myuser",
    "Password": "mypassword"
})

# Submit
browser.press_key("Enter")

# Wait for redirect
browser.wait_for(url="dashboard")

# Take screenshot
browser.screenshot("/tmp/dashboard.png")

# Close
browser.close()
```

## Next Steps

- [Wait Conditions](guides/wait-conditions.md)
- [Cookies](guides/cookies.md)
- [Network Interception](guides/network.md)
- [API Reference](api/browser.md)
