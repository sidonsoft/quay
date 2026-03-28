from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._browser_core import BrowserCoreMixin
    from ._browser_tabs import BrowserTabsMixin
    from ._browser_wait import BrowserWaitMixin

from .errors import TimeoutError


class BrowserNavigationMixin:
    """Navigation methods for Browser.
    
    Requires: BrowserCoreMixin, BrowserTabsMixin, BrowserWaitMixin
    """

    def navigate(self: "BrowserCoreMixin | BrowserNavigationMixin", url: str, tab=None, timeout=None) -> str:
        async def _navigate():
            conn = await self._get_connection(tab)
            result = await self._send_cdp(conn, "Page.navigate", {"url": url}, domains=["Page"], timeout=timeout)
            return result.get("frameId", "")
        return self._run_async(_navigate())

    def goto(self: "BrowserCoreMixin | BrowserTabsMixin | BrowserNavigationMixin | BrowserWaitMixin", url: str, timeout=None, page_load_timeout=None):
        cdp_timeout = self._resolve_timeout(timeout)
        load_timeout = page_load_timeout if page_load_timeout is not None else cdp_timeout
        tab = self.new_tab(url)
        try:
            self.wait_for_load_state(tab=tab, timeout=load_timeout)
        except TimeoutError:
            pass
        return tab