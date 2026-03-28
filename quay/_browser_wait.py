from __future__ import annotations

import asyncio
import re
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from ._browser_core import escape_js_string
from .errors import BrowserError, ConnectionError, TimeoutError


class BrowserWaitMixin:
    """Wait methods for Browser.
    
    Requires: BrowserCoreMixin, BrowserActionsMixin (for evaluate)
    """

    def wait_for_load_state(self, state="load", tab=None, timeout=10.0) -> bool:
        resolved_tab = self._resolve_tab(tab)  # type: ignore[attr-defined]
        async def _wait():
            conn = await self._get_connection(resolved_tab)  # type: ignore[attr-defined]
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    result = await self._send_cdp(conn, "Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True}, domains=["Runtime"])  # type: ignore[attr-defined]
                    ready_state = result.get("result", {}).get("value")
                    if state == "load" and ready_state == "complete":
                        return True
                    if state == "DOMContentLoaded" and ready_state in ["interactive", "complete"]:
                        return True
                except Exception:
                    pass
                await asyncio.sleep(0.1)
            raise TimeoutError(f"Wait for load state '{state}' timed out after {timeout}s", timeout=timeout, operation="wait_for_load_state")
        return self._run_async(_wait())  # type: ignore[attr-defined]

    def wait_for(self, selector=None, text=None, tab=None, timeout=10.0) -> bool:
        resolved_tab = self._resolve_tab(tab)  # type: ignore[attr-defined]
        start = time.time()
        while time.time() - start <= timeout:
            try:
                if selector and self.evaluate(f"document.querySelector({escape_js_string(selector)}) !== null", tab=resolved_tab):  # type: ignore[attr-defined]
                    return True
                if text and self.evaluate(f"document.body.innerText.includes({escape_js_string(text)})", tab=resolved_tab):  # type: ignore[attr-defined]
                    return True
            except (ConnectionError, TimeoutError, BrowserError):
                pass
            time.sleep(0.2)
        return False

    def wait_for_url(self, url=None, pattern=None, tab=None, timeout=10.0) -> bool:
        if url and pattern:
            raise ValueError("Provide either url or pattern, not both")
        if not url and not pattern:
            raise ValueError("Either url or pattern must be provided")
        resolved_tab = self._resolve_tab(tab)  # type: ignore[attr-defined]
        compiled_pattern = re.compile(pattern) if pattern else None
        start = time.time()
        while time.time() - start <= timeout:
            try:
                current_url = self.evaluate("window.location.href", tab=resolved_tab)  # type: ignore[attr-defined]
                if url and current_url == url:
                    return True
                if compiled_pattern and compiled_pattern.search(current_url):
                    return True
            except (ConnectionError, TimeoutError, BrowserError):
                pass
            time.sleep(0.2)
        return False

    def wait_for_selector_visible(self, selector: str, timeout: float = 10.0) -> bool:
        start = time.time()
        escaped = escape_js_string(selector)
        while time.time() - start <= timeout:
            try:
                if self.evaluate(f"(function() {{ const el = document.querySelector({escaped}); if (!el) return false; const style = window.getComputedStyle(el); return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetParent !== null; }})()"):  # type: ignore[attr-defined]
                    return True
            except (ConnectionError, TimeoutError, BrowserError):
                pass
            time.sleep(0.2)
        return False

    def wait_for_selector_hidden(self, selector: str, timeout: float = 10.0) -> bool:
        start = time.time()
        escaped = escape_js_string(selector)
        while time.time() - start <= timeout:
            try:
                if self.evaluate(f"(function() {{ const el = document.querySelector({escaped}); if (!el) return true; const style = window.getComputedStyle(el); return style.display === 'none' || style.visibility === 'hidden' || el.offsetParent === null; }})()"):  # type: ignore[attr-defined]
                    return True
            except (ConnectionError, TimeoutError, BrowserError):
                pass
            time.sleep(0.2)
        return False

    def wait_for_function(self, js_function: str, timeout: float = 10.0, polling_interval: float = 0.2) -> bool:
        start = time.time()
        while time.time() - start <= timeout:
            try:
                if self.evaluate(js_function):  # type: ignore[attr-defined]
                    return True
            except (ConnectionError, TimeoutError, BrowserError):
                pass
            time.sleep(polling_interval)
        return False

    def wait_for_navigation(self, tab=None, timeout: float = 10.0, wait_until: str = "load") -> bool:
        return self.wait_for_load_state(state=wait_until, tab=self._resolve_tab(tab), timeout=timeout)  # type: ignore[attr-defined]