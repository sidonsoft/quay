> **⚠️ Planned — Not Yet Implemented**
>
> The cookie management API (`get_cookies`, `set_cookies`, `delete_cookies`) is planned for a future release. This page documents the intended design. Track progress: [Roadmap](../roadmap.md)

# Cookies

Manage browser cookies for authentication and session handling.

## Get Cookies

```python
# Get all cookies
cookies = browser.get_cookies()
for cookie in cookies:
    print(f"{cookie['name']}: {cookie['value']}")

# Get cookies for a specific URL
cookies = browser.get_cookies(urls=["https://example.com"])
```

## Set Cookies

```python
# Set a single cookie
browser.set_cookies([{
    "name": "session",
    "value": "abc123",
    "domain": ".example.com"
}])

# Set multiple cookies
browser.set_cookies([
    {"name": "token", "value": "xyz789", "domain": ".example.com"},
    {"name": "preferences", "value": "{\"theme\":\"dark\"}", "domain": ".example.com"}
])

# Set with full options
browser.set_cookies([{
    "name": "session",
    "value": "abc123",
    "domain": ".example.com",
    "path": "/",
    "secure": True,
    "httpOnly": True,
    "expires": 1735689600
}])
```

## Delete Cookies

```python
# Delete specific cookie
browser.delete_cookies("session")

# Delete all cookies
browser.delete_cookies()
```

## Use Case: Transfer Session

```python
# Login in one browser
browser = Browser()
browser.navigate("https://example.com/login")
browser.fill_form({"Username": "user", "Password": "pass"})
browser.press_key("Enter")

# Extract session cookies
cookies = browser.get_cookies()
session_cookies = [c for c in cookies if "session" in c["name"]]

# Transfer to another browser instance
browser2 = Browser()
browser2.new_tab("https://example.com")
browser2.set_cookies(session_cookies)
# Now browser2 is logged in!
```

## Use Case: Restore Session

```python
import json

# Save cookies
cookies = browser.get_cookies()
with open("cookies.json", "w") as f:
    json.dump(cookies, f)

# Later... restore cookies
with open("cookies.json", "r") as f:
    cookies = json.load(f)
browser.set_cookies(cookies)
```
