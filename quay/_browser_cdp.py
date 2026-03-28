from __future__ import annotations

from typing import TYPE_CHECKING, Any
import weakref

if TYPE_CHECKING:
    from ._browser_core import BrowserCoreMixin
    from ._browser_tabs import BrowserTabsMixin

from .connection import Connection
from .errors import CDPError, TimeoutError


class BrowserCDPMixin:
    """CDP (Chrome DevTools Protocol) low-level methods for Browser.
    
    Requires: BrowserCoreMixin, BrowserTabsMixin
    """

    # Cache of enabled domains per connection.
    # Uses WeakKeyDictionary so cache entries are cleared when connections are GC'd.
    # Lazy initialization via hasattr to avoid MRO __init__ conflicts.
    _enabled_domains: weakref.WeakKeyDictionary  # type: ignore[assignment]

    async def _send_cdp(
        self: "BrowserCoreMixin | BrowserCDPMixin",
        conn: Connection,
        method: str,
        params: dict[str, Any] | None = None,
        domains: list[str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        # Initialize domain cache lazily
        if not hasattr(self, '_enabled_domains'):
            self._enabled_domains = weakref.WeakKeyDictionary()
        
        # Get or create enabled set for this connection
        enabled = self._enabled_domains.setdefault(conn, set())
        
        if domains:
            for domain in domains:
                # Only send Domain.enable once per connection
                if domain not in enabled:
                    try:
                        await conn.send(f"{domain}.enable", timeout=self._resolve_timeout(timeout))
                        enabled.add(domain)
                    except Exception:
                        pass
        try:
            return await conn.send(method, params, timeout=self._resolve_timeout(timeout))
        except Exception as e:
            if isinstance(e, TimeoutError):
                raise
            raise CDPError(str(e))

    def _clear_domain_cache(self, conn: Connection) -> None:
        """Clear the enabled domains cache for a connection.
        
        Call this after reconnection since CDP state is lost on disconnect.
        """
        if hasattr(self, '_enabled_domains'):
            self._enabled_domains.pop(conn, None)

    def _get_current_tab(self: "BrowserCoreMixin | BrowserTabsMixin | BrowserCDPMixin"):
        if self._current_tab:
            return self._current_tab
        tabs = self.list_tabs()
        if tabs:
            self._current_tab = tabs[0]
        return self._current_tab