from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._browser_core import BrowserCoreMixin
    from ._browser_tabs import BrowserTabsMixin

from .connection import Connection
from .errors import CDPError, TimeoutError


class BrowserCDPMixin:
    """CDP (Chrome DevTools Protocol) low-level methods for Browser.
    
    Requires: BrowserCoreMixin, BrowserTabsMixin
    """

    async def _send_cdp(
        self: "BrowserCoreMixin | BrowserCDPMixin",
        conn: Connection,
        method: str,
        params: dict[str, Any] | None = None,
        domains: list[str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        if domains:
            for domain in domains:
                try:
                    await conn.send(f"{domain}.enable", timeout=self._resolve_timeout(timeout))
                except Exception:
                    pass
        try:
            return await conn.send(method, params, timeout=self._resolve_timeout(timeout))
        except Exception as e:
            if isinstance(e, TimeoutError):
                raise
            raise CDPError(str(e))

    def _get_current_tab(self: "BrowserCoreMixin | BrowserTabsMixin | BrowserCDPMixin"):
        if self._current_tab:
            return self._current_tab
        tabs = self.list_tabs()
        if tabs:
            self._current_tab = tabs[0]
        return self._current_tab