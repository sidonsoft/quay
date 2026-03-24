# Reconnection Design

This document defines the strategy for WebSocket reconnection and command retry logic.

## Reconnection Requirements

### 1. Trigger Events
- WebSocket Close/Error: connection drops or error event
- Send/Recv Timeout: command exceeds timeout without response
- Health Check Failure: periodic health_check fails

### 2. State Preservation
During reconnection:
- Active Tab References: tab_id and metadata persist
- Pending Operations: commands not timed out should be retried
- Registered Interceptors: must be re-registered on new socket

### 3. Connection Behavior
- Queueing: new calls to _send_cdp() queue while reconnecting
- Retry Logic: failed commands retried automatically once
- Configurability: max_retries and reconnect_delay user-configurable

---

## State Machine

```
[CONNECTING] --(Success)--> [HEALTHY] <--(Command Send)
     ^                         |  ^
     |                         |  +------------+
  (Retry)                      |
     |                   (Error/Timeout/Close)
     |                         |
     +------- [RECONNECTING] <--+
                    |
               (Max Retries)
                    |
              [FAILED/CLOSED]
```

---

## API Design

### Connection Updates
- ensure_connected(retry_count): orchestrate reconnection
- reconnect(): close socket and call connect()

### Browser Updates
- reconnect_retries: int = 3
- reconnect_delay: float = 1.0

### New Error Handling
- ReconnectionError: raised when max_retries exceeded
- PermanentFailure: raised when Chrome unreachable

---

## Strategy for Retrying Operations

1. If Connection.send() fails with network exception or timeout:
2. Mark Connection as RECONNECTING
3. Perform reconnection sequence (disconnect, connect, health-check)
4. If successful, re-send original command with original id
5. If reconnect fails after max_retries, cancel pending Future with original exception
