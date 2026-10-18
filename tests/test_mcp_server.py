"""Tests for quay.mcp_server — MCP tool surface (no live Chrome required)."""

from __future__ import annotations

import asyncio

import pytest

from quay.models import AXNode
from quay.models import BrowserInfo
from quay.models import Tab


class FakeBrowser:
    """Minimal browser double implementing the surface used by MCP tools."""

    def __init__(self):
        self.current_tab = None
        self.calls: list[tuple] = []
        self._tabs = [
            Tab(
                id="TABID12345678",
                url="https://example.com/",
                title="Example",
                type="page",
                web_socket_debugger_url="ws://localhost:9222/devtools/page/TABID12345678",
            ),
            Tab(
                id="CHROME12345678",
                url="chrome://settings/",
                title="Settings",
                type="page",
                web_socket_debugger_url="ws://localhost:9222/devtools/page/CHROME12345678",
            ),
        ]

    def get_version(self) -> BrowserInfo:
        self.calls.append(("get_version",))
        return BrowserInfo(
            browser="Chrome/155.0",
            protocol_version="1.3",
            user_agent="UA" * 20,
            v8_version="15.5",
            webkit_version="537.36",
            web_socket_debugger_url="ws://localhost:9222/devtools/browser/X",
        )

    def list_tabs(self) -> list[Tab]:
        self.calls.append(("list_tabs",))
        return list(self._tabs)

    def new_tab(self, url: str = "about:blank") -> Tab:
        self.calls.append(("new_tab", url))
        return Tab(
            id="NEWTAB12345678",
            url=url,
            title="New",
            type="page",
            web_socket_debugger_url="ws://localhost:9222/devtools/page/NEWTAB12345678",
        )

    def navigate(self, url: str) -> str:
        self.calls.append(("navigate", url))
        return "FRAMEID"

    def accessibility_tree(self) -> AXNode:
        self.calls.append(("accessibility_tree",))
        root = AXNode(ref="axnode@1", role="RootWebArea", name="Example")
        link = AXNode(ref="axnode@2", role="link", name="More information", url="https://x.test")
        link.parent = root
        root.children = [link]
        return root

    def click_by_text(self, text: str) -> bool:
        self.calls.append(("click_by_text", text))
        return True

    def click(self, ref: str) -> bool:
        self.calls.append(("click", ref))
        return True

    def fill_form(self, fields: dict) -> dict:
        self.calls.append(("fill_form", fields))
        return {k: (i != 1) for i, k in enumerate(fields)}

    def evaluate(self, script: str):
        self.calls.append(("evaluate", script))
        return 42

    def screenshot(self, path: str) -> str:
        self.calls.append(("screenshot", path))
        return path

    def close_tab(self, tab) -> bool:
        self.calls.append(("close_tab", tab))
        return True


def _server(fake: FakeBrowser):
    from quay.mcp_server import create_server

    return create_server(browser=fake)


def _run(coro):
    return asyncio.run(coro)


class TestMCPServerSurface:
    """create_server exposes the documented tool set."""

    def test_server_has_all_tools(self):
        server = _server(FakeBrowser())
        names = [t.name for t in _run(server.list_tools())]
        assert names == [
            "browser_status",
            "open_tab",
            "navigate",
            "snapshot",
            "click_text",
            "click_ref",
            "fill_form",
            "evaluate",
            "screenshot",
            "close_tabs",
        ]

    def test_server_instructions_set(self):
        server = _server(FakeBrowser())
        assert "logged-in" in (server.instructions or "")


class TestMCPToolCalls:
    """Tool calls route to the browser and format results."""

    def test_browser_status_lists_tabs(self):
        fake = FakeBrowser()
        server = _server(fake)
        res = _run(server.call_tool("browser_status", {}))
        text = res.content[0].text
        assert "Chrome/155.0" in text
        assert "Tabs: 2" in text
        assert "Example" in text

    def test_open_tab(self):
        fake = FakeBrowser()
        server = _server(fake)
        res = _run(server.call_tool("open_tab", {"url": "https://example.com"}))
        assert "Opened tab" in res.content[0].text
        assert ("new_tab", "https://example.com") in fake.calls

    def test_navigate_sets_current_tab(self):
        fake = FakeBrowser()
        server = _server(fake)
        res = _run(server.call_tool("navigate", {"url": "https://x.test"}))
        assert "Navigated to" in res.content[0].text
        assert fake.current_tab is fake._tabs[0]
        assert ("navigate", "https://x.test") in fake.calls

    def test_snapshot_returns_tree(self):
        server = _server(FakeBrowser())
        res = _run(server.call_tool("snapshot", {}))
        text = res.content[0].text
        assert "RootWebArea" in text
        assert "More information" in text

    def test_click_text_and_click_ref(self):
        fake = FakeBrowser()
        server = _server(fake)
        r1 = _run(server.call_tool("click_text", {"text": "More information"}))
        assert "Clicked: True" in r1.content[0].text
        r2 = _run(server.call_tool("click_ref", {"ref": "axnode@2"}))
        assert "Clicked: True" in r2.content[0].text
        assert ("click", "axnode@2") in fake.calls

    def test_fill_form_reports_per_field(self):
        fake = FakeBrowser()
        server = _server(fake)
        res = _run(server.call_tool("fill_form", {"fields": {"Email": "a@b.c", "Pass": "x"}}))
        text = res.content[0].text
        assert "Email: ok" in text
        assert "Pass: FAILED" in text

    def test_evaluate(self):
        server = _server(FakeBrowser())
        res = _run(server.call_tool("evaluate", {"script": "1+1+40"}))
        assert res.content[0].text == "42"

    def test_screenshot_uses_given_path(self):
        fake = FakeBrowser()
        server = _server(fake)
        res = _run(server.call_tool("screenshot", {"path": "/tmp/shot.png"}))
        assert "Saved: /tmp/shot.png" in res.content[0].text
        assert ("screenshot", "/tmp/shot.png") in fake.calls

    def test_close_tabs_skips_chrome_urls(self):
        fake = FakeBrowser()
        server = _server(fake)
        res = _run(server.call_tool("close_tabs", {}))
        assert "Closed 1 tab" in res.content[0].text
        closed = [c for c in fake.calls if c[0] == "close_tab"]
        assert len(closed) == 1  # only the non-chrome:// tab


class TestMCPErrorHandling:
    """Errors return 'Error: ...' text instead of raising."""

    def test_tool_errors_become_error_text(self):
        class Broken(FakeBrowser):
            def get_version(self):
                raise RuntimeError("Chrome DevTools not reachable at http://localhost:9222")

        server = _server(Broken())
        res = _run(server.call_tool("browser_status", {}))
        assert res.content[0].text.startswith("Error:")
        assert "not reachable" in res.content[0].text

    def test_unknown_tool_raises_tool_error(self):
        from mcp.server.mcpserver.exceptions import ToolError

        server = _server(FakeBrowser())
        with pytest.raises(ToolError):
            _run(server.call_tool("does_not_exist", {}))


class TestMCPCliWiring:
    """quay mcp is registered in the CLI."""

    def test_mcp_command_registered(self):
        from quay.cli import COMMANDS

        assert "mcp" in COMMANDS

    def test_cmd_mcp_calls_run_server(self, monkeypatch):
        from quay import mcp_server
        from quay.cli import cmd_mcp

        called = {}

        def fake_run(host, port):
            called["args"] = (host, port)

        monkeypatch.setattr(mcp_server, "run_server", fake_run)

        class Args:
            host = "localhost"
            port = 9222

        assert cmd_mcp(Args()) == 0
        assert called["args"] == ("localhost", 9222)
