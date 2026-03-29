"""
Browser Hybrid - Chrome DevTools with accessibility-tree semantics.

A Python library combining Chrome DevTools Protocol with accessibility semantics
for browser automation using your authenticated Chrome sessions.

Example:
    from quay import Browser

    browser = Browser()
    browser.goto("https://gmail.com")  # Uses your logged-in session

    tree = browser.accessibility_tree()
    print(tree.to_tree_str())

    browser.click_by_text("Sign in")
    browser.fill_form({"Email": "user@example.com"})
"""

from __future__ import annotations

import logging

from ._version import __version__
from .browser import Browser
from .browser import BrowserError
from .browser import CDPError
from .browser import ConnectionError
from .browser import TabError
from .browser import TimeoutError
from .models import AXNode
from .models import BrowserInfo
from .models import ComparisonResult
from .models import Tab

# Configure default logging for the package
logging.basicConfig(level=logging.WARNING)

__all__ = [
    "Browser",
    "Tab",
    "AXNode",
    "BrowserInfo",
    "ComparisonResult",
    "BrowserError",
    "CDPError",
    "ConnectionError",
    "TabError",
    "TimeoutError",
    "__version__",
]
