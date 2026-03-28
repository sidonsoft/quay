# Connection API Reference

Low-level WebSocket connection management.

## Connection Class

```python
from quay.connection import Connection, ConnectionState
```

### Constructor

```python
conn = Connection(
    ws_url="ws://localhost:9222/devtools/page/abc123",
    tab_id="abc123"
)
```

### Methods

#### connect()

Establish WebSocket connection.

```python
await conn.connect()
```

#### send()

Send CDP command.

```python
result = await conn.send("Page.navigate", {"url": "https://example.com"})
```

Parameters:
- `method` (str): CDP method name
- `params` (dict, optional): Method parameters
- `timeout` (float, optional): Operation timeout

Returns: `dict[str, Any]`

#### close()

Close connection.

```python
await conn.close()
```

#### reconnect()

Reconnect after disconnect.

```python
success = await conn.reconnect(
    max_retries=5,
    base_backoff=0.5
)
```

Returns: `bool`

### Properties

#### state

Connection state.

```python
if conn.state == ConnectionState.CONNECTED:
    print("Ready")
```

States:
- `ConnectionState.DISCONNECTED`
- `ConnectionState.CONNECTED`
- `ConnectionState.RECONNECTING`

#### is_connected

Check if connected.

```python
if conn.is_connected:
    print("Ready")
```

## ConnectionPool

Manage multiple tab connections.

```python
from quay.connection import ConnectionPool

pool = ConnectionPool()

# Get or create connection
### get_connection(ws_url, tab_id)

Get or create a connection for a tab.

```python
conn = await pool.get_connection(ws_url, tab_id)

# Close all connections
await pool.close_all()
```

## Exceptions

```python
from quay.errors import (
    BrowserError,
    ConnectionError,
    TimeoutError,
    TabError,
    CDPError,
)
```

### BrowserError

Base exception for all quay errors.

### ConnectionError

WebSocket connection errors.

```python
try:
    browser.navigate("https://example.com")
except ConnectionError as e:
    print(f"Connection failed: {e}")
```

### TimeoutError

Operation timeout errors.

```python
try:
    browser.wait_for(text="Done", timeout=5.0)
except TimeoutError as e:
    print(f"Timed out: {e}")
```

### TabError

Tab management errors.

```python
try:
    browser.close_tab(tab)
except TabError as e:
    print(f"Tab error: {e}")
```

### CDPError

Chrome DevTools Protocol errors.

```python
try:
    browser.navigate("invalid-url")
except CDPError as e:
    print(f"CDP error: {e}")
    # e.code contains the CDP error code
    print(f"Error code: {e.code}")
```
