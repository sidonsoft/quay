"""
Browser Hybrid - WebSocket connection management.

Provides a connection pool for Chrome DevTools Protocol tabs.
Each tab gets one persistent WebSocket, reused across operations.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

# websockets is a required dependency
from websockets.asyncio.client import ClientConnection, connect

from .errors import ConnectionError, TimeoutError, parse_cdp_error


@dataclass
class PendingOperation:
    """A CDP operation waiting for reconnection."""

    request_id: int
    method: str
    params: dict[str, Any] | None
    future: asyncio.Future[Any]


class OperationQueue:
    """Thread-safe queue for CDP operations during reconnection."""

    def __init__(self):
        self._pending: dict[int, PendingOperation] = {}
        self._lock = threading.Lock()

    def queue(
        self, request_id: int, method: str, params: dict[str, Any] | None
    ) -> asyncio.Future[Any]:
        """Queue operation for later execution."""
        future: asyncio.Future[Any] = asyncio.Future()
        op = PendingOperation(request_id, method, params, future)
        with self._lock:
            self._pending[request_id] = op
        return future

    def get_all(self) -> list[PendingOperation]:
        """Get all pending operations and clear queue."""
        with self._lock:
            ops = list(self._pending.values())
            self._pending.clear()
            return ops

    def clear(self) -> None:
        """Clear all pending operations."""
        with self._lock:
            self._pending.clear()


class ConnectionState(Enum):
    """WebSocket connection states."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()


class Connection:
    """
    Manages a single WebSocket connection to a Chrome tab.

    Thread-safe for concurrent use. Maintains persistent connection
    with automatic reconnection on failure.
    """

    _CLEANUP_THRESHOLD = 100  # Clean up stale messages every N messages

    def __init__(
        self,
        ws_url: str,
        tab_id: str | None = None,
        timeout: float = 10.0,
        rate_limit: float | None = None,
    ):
        """
        Initialize connection.

        Args:
            ws_url: WebSocket URL from Chrome DevTools
            tab_id: Chrome tab ID (required for reconnection)
            timeout: Default timeout for operations (seconds)
            rate_limit: Minimum seconds between subsequent CDP calls
        """
        self.ws_url = ws_url
        self.tab_id = tab_id
        self.timeout = timeout
        self._rate_limit = rate_limit
        self._last_send_time = 0.0

        self._ws: ClientConnection | None = None
        self._lock = asyncio.Lock()
        self._thread_lock = threading.Lock()
        self._message_id = 0
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._pending_timestamps: dict[int, float] = {}  # Track when messages were added
        self._receive_task: asyncio.Task[None] | None = None
        self._connected = False
        self._state = ConnectionState.DISCONNECTED
        self.last_used = time.time()
        self.on_state_change: Callable[[ConnectionState], None] | None = None
        self._queue = OperationQueue()
        self.last_error: Exception | None = None

        # Event listeners: method name -> list of callbacks
        self._event_listeners: dict[str, list[Callable[[dict], None]]] = {}

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    def _set_state(self, new_state: ConnectionState) -> None:
        """Update state and trigger callback."""
        if self._state != new_state:
            self._state = new_state
            if self.on_state_change:
                try:
                    self.on_state_change(new_state)
                except Exception:
                    # Don't let callback crash the library
                    pass  # Callback errors are intentionally suppressed

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected and self._ws is not None

    def is_healthy(self) -> bool:
        """Check if WebSocket connection is healthy."""
        return self.is_connected

    def check_health(self) -> None:
        """Raise ConnectionError if not healthy."""
        if not self.is_healthy():
            raise ConnectionError("Connection not healthy")

    async def connect(self) -> None:
        """
        Establish WebSocket connection to Chrome tab.

        Raises:
            ConnectionError: If connection fails
        """
        async with self._lock:
            if self.is_connected:
                return

            self._set_state(ConnectionState.CONNECTING)
            try:
                self._ws = await asyncio.wait_for(
                    connect(self.ws_url),
                    timeout=self.timeout,
                )
                self._connected = True
                self._set_state(ConnectionState.CONNECTED)
                # Start receiving messages
                self._receive_task = asyncio.create_task(self._receive_loop())
            except Exception as e:
                self._set_state(ConnectionState.DISCONNECTED)
                if isinstance(e, asyncio.TimeoutError):
                    raise TimeoutError(
                        "WebSocket connection timed out",
                        timeout=self.timeout,
                        operation="connect",
                    )
                raise ConnectionError(
                    "Failed to connect to Chrome tab",
                    original_error=e,
                )

    async def disconnect(self) -> None:
        """Close WebSocket connection gracefully."""
        async with self._lock:
            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass
                self._receive_task = None

            if self._ws:
                try:
                    await self._ws.close()
                except Exception:
                    pass
                self._ws = None

            self._connected = False
            self._set_state(ConnectionState.DISCONNECTED)
            self._pending.clear()

    async def reconnect(self, max_retries: int = 3, base_backoff: float = 1.0) -> bool:
        """
        Reconnect with exponential backoff.

        Args:
            max_retries: Maximum reconnection attempts
            base_backoff: Base backoff time in seconds

        Returns:
            True if reconnected, False if max retries exceeded
        """
        self._set_state(ConnectionState.RECONNECTING)
        await self.disconnect()
        self.last_error = None

        for attempt in range(max_retries):
            try:
                # Re-resolve URL if possible
                if self.tab_id:
                    new_url = await self._resolve_ws_url()
                    if new_url:
                        self.ws_url = new_url

                await self.connect()
                if self.is_connected:
                    # Replay queued operations
                    for op in self._queue.get_all():
                        try:
                            # Re-send and resolve the future
                            res = await self.send(op.method, op.params)
                            if not op.future.done():
                                op.future.set_result(res)
                        except Exception as e:
                            if not op.future.done():
                                op.future.set_exception(e)
                    return True
            except Exception as e:
                self.last_error = e

            # Exponential backoff
            if attempt < max_retries - 1:
                delay = base_backoff * (2**attempt)
                await asyncio.sleep(delay)

        self._set_state(ConnectionState.DISCONNECTED)
        return False

    async def _resolve_ws_url(self) -> str | None:
        """Re-resolve WebSocket URL from HTTP /json endpoint."""
        if not self.tab_id:
            return None

        try:
            # Parse host/port from current URL
            parsed = urllib.parse.urlparse(self.ws_url)
            host_port = parsed.netloc
            json_url = f"http://{host_port}/json"

            # Use thread to avoid blocking loop with urllib
            def fetch_json():
                with urllib.request.urlopen(json_url, timeout=2.0) as response:
                    return json.loads(response.read().decode())

            tabs = await asyncio.to_thread(fetch_json)
            for tab in tabs:
                if tab.get("id") == self.tab_id:
                    return tab.get("webSocketDebuggerUrl")
        except Exception:
            pass
        return None

    def _next_id(self) -> int:
        """Get next message ID (thread-safe)."""
        with self._thread_lock:
            self._message_id += 1
            return self._message_id

    async def send(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Send CDP command and await response.

        Args:
            method: CDP method name (e.g., "Page.navigate")
            params: Method parameters
            timeout: Timeout for this operation (falls back to self.timeout)

        Returns:
            CDP response result

        Raises:
            TimeoutError: If operation times out
            CDPError: If CDP returns an error
            ConnectionError: If not connected
        """
        if self._rate_limit:
            now = time.time()
            elapsed = now - self._last_send_time
            if elapsed < self._rate_limit:
                # Reserve the slot BEFORE sleeping to prevent race condition
                self._last_send_time = now + self._rate_limit
                await asyncio.sleep(self._rate_limit - elapsed)
            else:
                self._last_send_time = now

        self.last_used = time.time()
        if self.state == ConnectionState.DISCONNECTED:
            raise ConnectionError("WebSocket not connected")
        elif self.state == ConnectionState.RECONNECTING:
            # Queue operation for later
            return await self._queue.queue(self._next_id(), method, params)

        if not self.is_connected:
            raise ConnectionError("WebSocket is in an invalid state")

        timeout_val = timeout or self.timeout
        message_id = self._next_id()

        message = {
            "id": message_id,
            "method": method,
            "params": params or {},
        }

        # Create future for response
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[message_id] = future
        self._pending_timestamps[message_id] = time.time()

        try:
            # Send with timeout
            assert self._ws is not None
            await asyncio.wait_for(
                self._ws.send(json.dumps(message)),
                timeout=timeout_val,
            )

            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=timeout_val)

            # Check for CDP error
            if isinstance(result, dict):
                if error := parse_cdp_error(result, method):
                    raise error

            return result

        except asyncio.TimeoutError:
            raise TimeoutError(
                f"CDP command timed out: {method}",
                timeout=timeout_val,
                operation=method,
            )
        finally:
            self._pending.pop(message_id, None)
            self._pending_timestamps.pop(message_id, None)

    async def _receive_loop(self) -> None:
        """Continuously receive messages from WebSocket."""
        try:
            assert self._ws is not None
            async for message in self._ws:
                # Periodically clean up stale pending messages
                if len(self._pending) > self._CLEANUP_THRESHOLD:
                    self._cleanup_stale_messages()

                try:
                    data = json.loads(message)
                    msg_id = data.get("id")
                    if msg_id is not None and msg_id in self._pending:
                        # This is a response to a pending request
                        future = self._pending[msg_id]
                        if not future.done():
                            future.set_result(data)
                    elif "method" in data:
                        # This is an event - dispatch to listeners
                        self._dispatch_event(data["method"], data.get("params", {}))
                except json.JSONDecodeError:
                    # Ignore non-JSON messages (events)
                    pass
                except Exception:
                    # Ignore errors in message parsing
                    pass
        except (asyncio.CancelledError, StopAsyncIteration):
            self._connected = False
        except Exception:
            self._connected = False
        finally:
            self._connected = False
            self._set_state(ConnectionState.DISCONNECTED)
            self._ws = None
            # Cleanup pending futures
            for future in self._pending.values():
                if not future.done():
                    future.cancel()
            self._pending.clear()
            # Clear event listeners on disconnect
            self._event_listeners.clear()

    def _dispatch_event(self, method: str, params: dict[str, Any]) -> None:
        """Dispatch CDP event to registered listeners."""
        if method in self._event_listeners:
            for callback in self._event_listeners[method]:
                try:
                    callback(params)
                except Exception:
                    # Don't let listener errors break the receive loop
                    pass

    def on_event(self, method: str, callback: Callable[[dict], None]) -> None:
        """
        Register a callback for a CDP event.

        Args:
            method: CDP event name (e.g., "Network.requestWillBeSent")
            callback: Function to call with event params

        Example:
            def on_request(params):
                print(f"Request: {params['request']['url']}")

            conn.on_event("Network.requestWillBeSent", on_request)
        """
        if method not in self._event_listeners:
            self._event_listeners[method] = []
        self._event_listeners[method].append(callback)

    def off_event(self, method: str, callback: Callable[[dict], None] | None = None) -> None:
        """
        Unregister callback(s) for a CDP event.

        Args:
            method: CDP event name
            callback: Specific callback to remove, or None to remove all
        """
        if method not in self._event_listeners:
            return
        if callback is None:
            # Remove all listeners for this method
            self._event_listeners[method] = []
        else:
            # Remove specific callback
            try:
                self._event_listeners[method].remove(callback)
            except ValueError:
                pass

    _STALE_AGE_SECONDS = 30.0  # Futures pending longer than this are stale
    _CLEANUP_INTERVAL = 50     # Run cleanup every N messages in receive loop
    _receive_msg_count = 0     # New counter

    def _cleanup_stale_messages(self) -> None:
        """Remove stale pending messages by age, not just count.
        
        Uses _STALE_AGE_SECONDS threshold to catch timed-out futures
        that accumulated due to receive loop death or other issues.
        """
        now = time.time()
        stale_ids = []

        for msg_id, fut in self._pending.items():
            if fut.done():
                stale_ids.append(msg_id)
            elif msg_id in self._pending_timestamps:
                age = now - self._pending_timestamps[msg_id]
                if age > self._STALE_AGE_SECONDS:
                    stale_ids.append(msg_id)

        for msg_id in stale_ids:
            try:
                fut = self._pending.pop(msg_id, None)
                self._pending_timestamps.pop(msg_id, None)
                if fut and not fut.done():
                    fut.set_exception(TimeoutError(
                        f"Stale message (age > {self._STALE_AGE_SECONDS}s)",
                        timeout=self._STALE_AGE_SECONDS
                    ))
            except KeyError:
                pass

    async def health_check(self, timeout: float = 2.0) -> bool:
        """
        Check if connection is healthy.

        Sends a lightweight CDP command to verify responsiveness.

        Args:
            timeout: Time to wait for response

        Returns:
            True if healthy, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            # Use Target.getTargetInfo as lightweight check
            result = await self.send("Target.getTargetInfo", timeout=timeout)
            return "result" in result
        except (TimeoutError, ConnectionError):
            return False
        except Exception:
            return False

    async def ensure_connected(self) -> None:
        """
        Ensure connection is healthy, reconnecting if needed.

        Raises:
            ConnectionError: If reconnection fails
        """
        if self.is_connected and await self.health_check():
            return

        # Reconnect
        await self.reconnect()

    def __repr__(self) -> str:
        status = "connected" if self.is_connected else "disconnected"
        return f"<Connection {status} ws={self.ws_url[:50]}...>"


class ConnectionPool:
    """
    Pool of WebSocket connections to Chrome tabs.

    Manages connections per-tab, reusing across operations.
    Has a maximum connection limit and evicts oldest unused connections (LRU).
    """

    def __init__(
        self,
        timeout: float = 10.0,
        max_connections: int = 32,
        rate_limit: float | None = None,
    ):
        """
        Initialize pool.

        Args:
            timeout: Default timeout for connections
            max_connections: Maximum concurrent WebSocket connections
            rate_limit: Default rate limit to apply to connections
        """
        self.timeout = timeout
        self._max_connections = max_connections
        self._rate_limit = rate_limit
        self._connections: dict[str, Connection] = {}
        self._lock = asyncio.Lock()

    async def get_connection(self, tab_id: str, ws_url: str) -> Connection:
        """
        Get or create connection for a tab.

        Args:
            tab_id: Chrome tab ID
            ws_url: WebSocket URL for tab

        Returns:
            Connection for the tab
        """
        # First check without lock for efficiency
        conn = self._connections.get(tab_id)
        if conn and conn.is_connected:
            return conn

        async with self._lock:
            # Double-check after acquiring lock
            conn = self._connections.get(tab_id)
            if conn and conn.is_connected:
                return conn

            # Check if we need to evict oldest (LRU)
            if len(self._connections) >= self._max_connections:
                self._evict_oldest()

            conn = Connection(
                ws_url, tab_id=tab_id, timeout=self.timeout, rate_limit=self._rate_limit
            )
            await conn.connect()
            self._connections[tab_id] = conn
            return conn

    def _evict_oldest(self) -> None:
        """Remove oldest connection to make room (LRU).
        
        Synchronously marks connection for cleanup. The actual WebSocket
        close happens when the connection is garbage collected or explicitly
        closed via close_all().
        """
        if not self._connections:
            return

        # Find connection with oldest last_used timestamp
        oldest_id = min(self._connections.keys(), key=lambda k: self._connections[k].last_used)
        conn = self._connections.pop(oldest_id)

        # Mark as disconnected - the connection will be cleaned up when
        # the event loop gets a chance or when close_all() is called.
        # This avoids fire-and-forget asyncio.create_task which can leak sockets.
        conn._state = ConnectionState.DISCONNECTED
        conn._connected = False

    async def get_existing(self, tab_id: str) -> Connection | None:
        """
        Get existing connection without creating.

        Args:
            tab_id: Chrome tab ID

        Returns:
            Connection if exists and connected, None otherwise
        """
        conn = self._connections.get(tab_id)
        if conn and conn.state == ConnectionState.CONNECTED:
            return conn
        return None

    async def remove(self, tab_id: str) -> None:
        """
        Remove and close connection for a tab.

        Args:
            tab_id: Chrome tab ID
        """
        async with self._lock:
            conn = self._connections.pop(tab_id, None)
            if conn:
                await conn.disconnect()

    async def close_all(self) -> None:
        """Close all connections."""
        async with self._lock:
            for conn in self._connections.values():
                await conn.disconnect()
            self._connections.clear()

    @property
    def active_count(self) -> int:
        """Number of active connections."""
        return sum(1 for c in self._connections.values() if c.is_connected)

    def __repr__(self) -> str:
        return f"<ConnectionPool active={self.active_count} total={len(self._connections)}>"
