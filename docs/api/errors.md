# Error Handling

Quay provides a custom exception hierarchy.

## Exception Hierarchy

```
BrowserError (base)
├── ConnectionError   # WebSocket connection issues
├── TimeoutError      # Operation timeout
├── TabError          # Tab management errors
└── CDPError          # Chrome DevTools Protocol errors
```

## BrowserError

Base exception for all Quay errors.

```python
from quay.errors import BrowserError

try:
    browser.navigate("https://example.com")
except BrowserError as e:
    print(f"Browser error: {e}")
```

## ConnectionError

Raised when WebSocket connection fails.

```python
from quay.errors import ConnectionError

try:
    browser = Browser()
    browser.navigate("https://example.com")
except ConnectionError as e:
    print(f"Cannot connect to Chrome: {e}")
    print("Make sure Chrome is running with --remote-debugging-port=9222")
```

## TimeoutError

Raised when an operation exceeds its timeout.

```python
from quay.errors import TimeoutError

try:
    browser.wait_for(text="Done", timeout=5.0)
except TimeoutError as e:
    print(f"Timed out waiting: {e}")
```

## TabError

Raised for tab management errors.

```python
from quay.errors import TabError

try:
    browser.close_tab(tab)
except TabError as e:
    print(f"Tab error: {e}")
```

## CDPError

Raised for Chrome DevTools Protocol errors.

```python
from quay.errors import CDPError

try:
    browser.evaluate("invalid javascript")
except CDPError as e:
    print(f"CDP error: {e}")
    print(f"Error code: {e.code}")
    print(f"Error message: {e.message}")
```

## Best Practices

1. **Always close browser in finally**

```python
browser = Browser()
try:
    browser.navigate("https://example.com")
finally:
    browser.close()
```

2. **Handle specific errors**

```python
try:
    browser.wait_for(text="Done")
except TimeoutError:
    print("Timeout")
except ConnectionError:
    print("Disconnected")
```
