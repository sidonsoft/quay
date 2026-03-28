from __future__ import annotations

import asyncio
import atexit
import contextvars
import logging
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

import json

from .connection import Connection, ConnectionPool, ConnectionState
from .errors import ConnectionError
from .models import AXNode, Tab

logger = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9222
DEFAULT_TIMEOUT = 10.0


def escape_js_string(text: str) -> str:
    """Safely escape string for JavaScript injection using json.dumps.
    
    This properly handles Unicode, special characters, and edge cases
    that manual escaping misses. Returns the string without surrounding
    quotes for inline use in JavaScript expressions.
    
    Args:
        text: String to escape
        
    Returns:
        Escaped string safe for JavaScript string literals
        
    Example:
        >>> escape_js_string('Hello "world"')
        'Hello \\\\"world\\\\"'
        >>> escape_js_string("Line\\nbreak")
        'Line\\\\nbreak'
    """
    return json.dumps(text)[1:-1]  # Remove surrounding quotes


class BrowserCoreMixin:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = 0,
        retry_delay: float = 1.0,
        pool_rate_limit: float | None = None,
        cache_accessibility: bool = False,
        reconnect: bool = True,
        reconnect_max_retries: int = 3,
        reconnect_backoff: float = 1.0,
        reconnect_callback: Callable[[str], None] | None = None,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.pool_rate_limit = pool_rate_limit
        self.cache_accessibility = cache_accessibility
        self.reconnect_enabled = reconnect
        self.reconnect_max_retries = reconnect_max_retries
        self.reconnect_backoff = reconnect_backoff
        self.reconnect_callback = reconnect_callback
        self._interceptors: dict[str, list[Callable[[dict], None]]] = {}
        self._interceptor_filters: dict[str, dict] = {}
        self._accessibility_cache: dict[str, AXNode] = {}
        self._reconnect_tasks: set[asyncio.Task[Any]] = set()
        self.base_url = f"http://{host}:{port}"
        self._current_tab: Tab | None = None
        self._pool: ConnectionPool | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_lock = threading.Lock()
        self._recording = None
        self._playing_back = False
        self._record_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
            "record_depth", default=0
        )

        if not self._check_connection():
            connected = False
            if retry_attempts > 0:
                for _ in range(retry_attempts):
                    time.sleep(retry_delay)
                    if self._check_connection():
                        connected = True
                        break
            if not connected:
                raise ConnectionError(
                    f"Chrome DevTools not reachable at {self.base_url}",
                    host=host,
                    port=port,
                )
        atexit.register(self._cleanup)

    def _check_connection(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.base_url}/json/version", timeout=2)
            return True
        except (urllib.error.URLError, urllib.error.HTTPError):
            return False

    def _get_pool(self) -> ConnectionPool:
        if self._pool is None:
            with self._loop_lock:
                if self._pool is None:
                    self._pool = ConnectionPool(
                        timeout=self.timeout, rate_limit=self.pool_rate_limit
                    )
        return self._pool

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            with self._loop_lock:
                if self._loop is None or self._loop.is_closed():
                    self._loop = asyncio.new_event_loop()
                return self._loop

    def _run_async(self, coro: Any) -> Any:
        """Execute a coroutine synchronously, returning its result.
        
        Raises:
            RuntimeError: If called from within an already-running async context.
                Use async variants (e.g., navigate_async) or call from sync context.
        """
        loop = self._get_loop()
        if threading.current_thread() is threading.main_thread():
            if loop.is_running():
                # Get coroutine name for better error message
                coro_name = getattr(coro, '__name__', getattr(coro, '__class__', type(coro)).__name__)
                raise RuntimeError(
                    f"Cannot call synchronous method from async context. "
                    f"Method '{coro_name}' was called from an already-running event loop. "
                    f"Use async variants (e.g., navigate_async) or call from a synchronous context."
                )
            return loop.run_until_complete(coro)
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    def _resolve_tab(self, tab: Tab | str | None) -> Tab | None:
        if tab is None:
            return None
        if isinstance(tab, Tab):
            return tab
        for t in self.list_tabs():
            if t.id == tab:
                return t
        return None

    async def _get_connection(self, tab: Tab | None = None) -> Connection:
        tab_to_use = tab or self._get_current_tab()
        pool = self._get_pool()
        conn = await pool.get_connection(tab_to_use.id, tab_to_use.web_socket_debugger_url)
        if self.reconnect_enabled and not conn.on_state_change:
            def handle_state_change(state: ConnectionState):
                if state == ConnectionState.DISCONNECTED:
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(self._handle_disconnect(conn))
                    self._reconnect_tasks.add(task)
                    task.add_done_callback(self._reconnect_tasks.discard)

            conn.on_state_change = handle_state_change
        return conn

    async def _handle_disconnect(self, conn: Connection) -> None:
        if not self.reconnect_enabled:
            return
        try:
            msg = f"Connection to tab {conn.tab_id} lost. Attempting automatic reconnection..."
            logger.info(msg)
            if self.reconnect_callback:
                self.reconnect_callback(msg)
            success = await conn.reconnect(
                max_retries=self.reconnect_max_retries, base_backoff=self.reconnect_backoff
            )
            if success:
                msg = f"Automatic reconnection to tab {conn.tab_id} successful."
                logger.info(msg)
                if self.reconnect_callback:
                    self.reconnect_callback(msg)
                await self._reregister_interceptors(conn)
        except asyncio.CancelledError:
            logger.debug("Reconnection task cancelled")

    def _resolve_timeout(self, timeout: float | None) -> float:
        return timeout if timeout is not None else self.timeout

    def is_connected(self) -> bool:
        return self._check_connection()

    def wait_for_chrome(self, timeout: float = 30.0) -> bool:
        start = time.time()
        while time.time() - start <= timeout:
            if self._check_connection():
                return True
            time.sleep(0.5)
        return False

    async def wait_for_chrome_async(self, timeout: float = 30.0) -> bool:
        start = time.time()
        while time.time() - start <= timeout:
            if self._check_connection():
                return True
            await asyncio.sleep(0.5)
        return False

    @property
    def current_tab(self) -> Tab | None:
        return self._current_tab

    @current_tab.setter
    def current_tab(self, tab: Tab | None) -> None:
        self._current_tab = tab

    def _cleanup(self) -> None:
        if self._pool:
            self.close()

    def close(self) -> None:
        self._interceptors.clear()
        self._interceptor_filters.clear()
        self.reconnect_enabled = False
        if self._reconnect_tasks:
            for task in list(self._reconnect_tasks):
                if not task.done():
                    task.cancel()
            self._reconnect_tasks.clear()
        if self._pool and self._loop:
            try:
                self._run_async(self._pool.close_all())
            except RuntimeError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
