from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Callable, Coroutine, Any

if TYPE_CHECKING:
    pass

from ._browser_core import escape_js_string
from .errors import BrowserError, ConnectionError, TimeoutError


class BrowserWaitMixin:
    """Wait methods for Browser.
    
    Requires: BrowserCoreMixin, BrowserActionsMixin (for evaluate)
    """

    async def _poll_until(
        self,
        check_fn: Callable[[], Coroutine[Any, Any, bool]],
        timeout: float,
        poll_interval: float = 0.2
    ) -> bool:
        """Async polling loop helper.
        
        Polls check_fn until it returns True or timeout is reached.
        Uses asyncio.sleep() instead of time.sleep() for async compatibility.
        """
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                if await check_fn():
                    return True
            except (ConnectionError, TimeoutError, BrowserError):
                pass
            await asyncio.sleep(poll_interval)
        return False

    def wait_for_load_state(self, state="load", tab=None, timeout=10.0) -> bool:
        resolved_tab = self._resolve_tab(tab)  # type: ignore[attr-defined]
        async def _wait():
            conn = await self._get_connection(resolved_tab)  # type: ignore[attr-defined]
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    result = await self._send_cdp(conn, "Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True}, domains=["Runtime"])  # type: ignore[attr-defined]
                    # CDP Runtime.evaluate returns {"result": {"result": {"value": ...}}}
                    ready_state = result.get("result", {}).get("result", {}).get("value")
                    if state == "load" and ready_state == "complete":
                        return True
                    if state == "DOMContentLoaded" and ready_state in ["interactive", "complete"]:
                        return True
                except Exception:
                    pass
                await asyncio.sleep(0.1)
            raise TimeoutError(f"Wait for load state '{state}' timed out after {timeout}s", timeout=timeout, operation="wait_for_load_state")
        return self._run_async(_wait())  # type: ignore[attr-defined]

    def wait_for(self, selector=None, text=None, tab=None, timeout=10.0, poll_interval: float = 0.2) -> bool:
        resolved_tab = self._resolve_tab(tab)  # type: ignore[attr-defined]
        
        async def _check():
            if selector:
                result = self.evaluate(f"document.querySelector({escape_js_string(selector)}) !== null", tab=resolved_tab)  # type: ignore[attr-defined]
                if result:
                    return True
            if text:
                result = self.evaluate(f"document.body.innerText.includes({escape_js_string(text)})", tab=resolved_tab)  # type: ignore[attr-defined]
                if result:
                    return True
            return False

        async def _poll():
            return await self._poll_until(_check, timeout=timeout, poll_interval=poll_interval)

        return self._run_async(_poll())  # type: ignore[attr-defined]

    def wait_for_url(self, url=None, pattern=None, tab=None, timeout=10.0, poll_interval: float = 0.2) -> bool:
        if url and pattern:
            raise ValueError("Provide either url or pattern, not both")
        if not url and not pattern:
            raise ValueError("Either url or pattern must be provided")
        resolved_tab = self._resolve_tab(tab)  # type: ignore[attr-defined]
        compiled_pattern = re.compile(pattern) if pattern else None

        async def _check():
            try:
                current_url = self.evaluate("window.location.href", tab=resolved_tab)  # type: ignore[attr-defined]
                if url and current_url == url:
                    return True
                if compiled_pattern and compiled_pattern.search(current_url):
                    return True
            except (ConnectionError, TimeoutError, BrowserError):
                pass
            return False

        async def _poll():
            return await self._poll_until(_check, timeout=timeout, poll_interval=poll_interval)

        return self._run_async(_poll())  # type: ignore[attr-defined]

    def wait_for_selector_visible(self, selector: str, timeout: float = 10.0, poll_interval: float = 0.2) -> bool:
        escaped = escape_js_string(selector)
        check_script = f"(function() {{ const el = document.querySelector({escaped}); if (!el) return false; const style = window.getComputedStyle(el); return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetParent !== null; }})()"

        async def _check(self):
            return bool(self.evaluate(check_script))  # type: ignore[attr-defined]

        async def _poll():
            return await self._poll_until(lambda: _check(self), timeout=timeout, poll_interval=poll_interval)

        return self._run_async(_poll())  # type: ignore[attr-defined]

    def wait_for_selector_hidden(self, selector: str, timeout: float = 10.0, poll_interval: float = 0.2) -> bool:
        escaped = escape_js_string(selector)
        check_script = f"(function() {{ const el = document.querySelector({escaped}); if (!el) return true; const style = window.getComputedStyle(el); return style.display === 'none' || style.visibility === 'hidden' || el.offsetParent === null; }})()"

        async def _check(self):
            return bool(self.evaluate(check_script))  # type: ignore[attr-defined]

        async def _poll():
            return await self._poll_until(lambda: _check(self), timeout=timeout, poll_interval=poll_interval)

        return self._run_async(_poll())  # type: ignore[attr-defined]

    def wait_for_function(self, js_function: str, timeout: float = 10.0, polling_interval: float = 0.2) -> bool:
        async def _check(self):
            return bool(self.evaluate(js_function))  # type: ignore[attr-defined]

        async def _poll():
            return await self._poll_until(lambda: _check(self), timeout=timeout, poll_interval=polling_interval)

        return self._run_async(_poll())  # type: ignore[attr-defined]

    def wait_for_navigation(self, tab=None, timeout: float = 10.0, wait_until: str = "load") -> bool:
        return self.wait_for_load_state(state=wait_until, tab=self._resolve_tab(tab), timeout=timeout)  # type: ignore[attr-defined]