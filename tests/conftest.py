"""Shared pytest fixtures for quay tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from quay.models import Tab


@pytest.fixture
def mock_browser():
    """Create a mock Browser with common methods configured."""
    browser = MagicMock()
    browser.list_tabs = MagicMock(return_value=[
        Tab(id="TAB1", url="https://example.com", title="Example", type="page", web_socket_debugger_url="ws://localhost:9222/devtools/page/TAB1"),
        Tab(id="TAB2", url="https://google.com", title="Google", type="page", web_socket_debugger_url="ws://localhost:9222/devtools/page/TAB2"),
    ])
    browser.current_tab = None
    browser.connect = MagicMock()
    browser.close = MagicMock()
    browser.close_tab = MagicMock()
    browser.get_html = MagicMock(return_value="<html><body>test</body></html>")
    browser.navigate = MagicMock()
    browser.screenshot = MagicMock(return_value=b"fake_png_data")
    return browser


@pytest.fixture
def sample_tabs():
    """Sample tab data from Chrome DevTools Protocol."""
    return [
        {
            "id": "TAB1",
            "url": "https://example.com",
            "title": "Example",
            "type": "page",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/TAB1",
        },
        {
            "id": "TAB2",
            "url": "https://google.com",
            "title": "Google",
            "type": "page",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/TAB2",
        },
        {
            "id": "EXT1",
            "url": "chrome-extension://abc",
            "title": "Extension",
            "type": "background_page",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/EXT1",
        },
    ]


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    ws.__aiter__ = AsyncMock(return_value=iter([]))
    return ws