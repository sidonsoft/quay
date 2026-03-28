from __future__ import annotations

from ._browser_accessibility import BrowserAccessibilityMixin
from ._browser_actions import BrowserActionsMixin
from ._browser_cdp import BrowserCDPMixin
from ._browser_core import BrowserCoreMixin
from ._browser_navigation import BrowserNavigationMixin
from ._browser_recording import BrowserRecordingMixin
from ._browser_tabs import BrowserTabsMixin
from ._browser_wait import BrowserWaitMixin
from .errors import BrowserError, CDPError, ConnectionError, TabError, TimeoutError
from .models import Action, AXNode, BrowserInfo, ComparisonResult, Recording, Tab


class Browser(
    BrowserCoreMixin,
    BrowserTabsMixin,
    BrowserCDPMixin,
    BrowserRecordingMixin,
    BrowserNavigationMixin,
    BrowserWaitMixin,
    BrowserAccessibilityMixin,
    BrowserActionsMixin,
):
    pass


__all__ = [
    "Browser",
    "Tab",
    "AXNode",
    "BrowserInfo",
    "Action",
    "Recording",
    "ComparisonResult",
    "BrowserError",
    "ConnectionError",
    "TabError",
    "TimeoutError",
    "CDPError",
]
