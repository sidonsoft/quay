from __future__ import annotations

import json
import urllib.error
import urllib.request
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._browser_core import BrowserCoreMixin
    from ._browser_navigation import BrowserNavigationMixin

from .errors import BrowserError, ConnectionError
from .models import BrowserInfo, Tab


class BrowserTabsMixin:
    """Tab management methods for Browser.
    
    Requires: BrowserCoreMixin
    Optional: BrowserNavigationMixin (for navigate in new_tab)
    """

    def _http_get(self: "BrowserCoreMixin | BrowserTabsMixin", path: str, timeout: float | None = None) -> Any:
        url = f"{self.base_url}{path}"
        timeout_val = self._resolve_timeout(timeout)
        try:
            with urllib.request.urlopen(url, timeout=timeout_val) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            raise BrowserError(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise ConnectionError("Failed to connect", host=self.host, port=self.port, original_error=e)

    def _http_put(self: "BrowserCoreMixin | BrowserTabsMixin", path: str, timeout: float | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        timeout_val = self._resolve_timeout(timeout)
        req = urllib.request.Request(url, method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=timeout_val) as response:
                data = response.read().decode()
                if not data:
                    return {"success": True}
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return {"result": data.strip()}
        except urllib.error.HTTPError as e:
            if e.code in (200, 204):
                return {"success": True}
            raise BrowserError(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise ConnectionError("Failed to connect", host=self.host, port=self.port, original_error=e)

    def list_tabs(self) -> list[Tab]:
        return [Tab.from_dict(t) for t in self._http_get("/json/list") if t.get("type") == "page"]

    def new_tab(self: "BrowserCoreMixin | BrowserTabsMixin | BrowserNavigationMixin", url: str = "about:blank") -> Tab:
        tab = Tab.from_dict(self._http_put("/json/new"))
        self._current_tab = tab
        if url and url != "about:blank":
            self.navigate(url, tab=tab)
        return tab

    def activate_tab(self: "BrowserCoreMixin | BrowserTabsMixin", tab_id: str) -> bool:
        self._http_put(f"/json/activate/{tab_id}")
        return True

    def close_tab(self: "BrowserCoreMixin | BrowserTabsMixin", tab: Tab | str | None = None) -> bool:
        tab_id = self._current_tab.id if tab is None and self._current_tab else tab.id if isinstance(tab, Tab) else tab
        if tab_id:
            self._http_put(f"/json/close/{tab_id}")
            if self._pool:
                self._run_async(self._pool.remove(tab_id))
            if self._current_tab and self._current_tab.id == tab_id:
                tabs = self.list_tabs()
                self._current_tab = tabs[0] if tabs else None
            return True
        return False

    def get_version(self) -> BrowserInfo:
        return BrowserInfo.from_dict(self._http_get("/json/version"))

    @contextmanager
    def temp_tab(self: "BrowserCoreMixin | BrowserTabsMixin | BrowserNavigationMixin", url: str = "about:blank", close_on_exit: bool = True):
        tab = self.new_tab(url)
        try:
            yield tab
        finally:
            if close_on_exit:
                try:
                    self.close_tab(tab)
                except Exception:
                    pass

    def switch_to_tab(self: "BrowserCoreMixin | BrowserTabsMixin", tab: Tab | str, focus: bool = True) -> Tab | None:
        prev = self.current_tab
        tab_id = tab.id if isinstance(tab, Tab) else tab
        if focus:
            self.activate_tab(tab_id)
        self.current_tab = tab if isinstance(tab, Tab) else next((t for t in self.list_tabs() if t.id == tab_id), None)
        return prev