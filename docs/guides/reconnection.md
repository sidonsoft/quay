# Automatic Reconnection

Quay automatically recovers from WebSocket disconnections.

## How It Works

When the WebSocket connection to Chrome drops:

1. Quay detects the disconnection
2. Background task attempts to reconnect
3. Operations are queued during reconnection
4. Queued operations execute after connection restores
5. Operations fail if max retries exceeded

## Configuration

```python
from quay import Browser

# Default (reconnect enabled)
browser = Browser()

# Disable auto-reconnection
browser = Browser(reconnect=False)

# Customize reconnection
browser = Browser(
    reconnect=True,
    reconnect_max_retries=5,
    reconnect_backoff=0.5,
)

# With callback for status updates
def on_reconnect(message):
    print(f"Reconnection: {message}")

browser = Browser(
    reconnect=True,
    reconnect_callback=on_reconnect
)
```

## Behavior

### During Reconnection

```python
# Operations queue during disconnect
browser.navigate("https://example.com")
browser.click("42")

# Operations execute after reconnection
```

### Connection State

```python
from quay.connection import ConnectionState

state = browser.state
if state == ConnectionState.CONNECTED:
    print("Ready to go")
elif state == ConnectionState.DISCONNECTED:
    print("Reconnecting...")
elif state == ConnectionState.RECONNECTING:
    print("Attempting to reconnect")
```

## Reconnection Backoff

Exponential backoff: Wait time = base_backoff * (2 ^ attempt_number)

```
- Attempt 1: 0.5s
- Attempt 2: 1.0s
- Attempt 3: 2.0s
- Attempt 4: 4.0s
- Attempt 5: 8.0s
```

## Best Practices

1. **Use callbacks for monitoring**

```python
def log_reconnect(msg):
    logger.warning(f"Reconnection: {msg}")

browser = Browser(reconnect_callback=log_reconnect)
```

2. **Set appropriate max_retries**

```python
# Quick fail for short tasks
browser = Browser(reconnect_max_retries=3)

# More patient for long tasks
browser = Browser(reconnect_max_retries=10)
```
