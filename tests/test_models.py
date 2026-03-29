"""Tests for quay.models."""

import time

import pytest

from quay.models import Action
from quay.models import AXNode
from quay.models import BrowserInfo
from quay.models import ComparisonResult
from quay.models import Recording
from quay.models import Tab


class TestTab:
    """Tests for Tab model."""

    def test_from_dict_full(self):
        """Tab parses full Chrome response."""
        data = {
            "id": "tab123",
            "url": "https://example.com",
            "title": "Example",
            "type": "page",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/tab123",
        }
        tab = Tab.from_dict(data)
        assert tab.id == "tab123"
        assert tab.url == "https://example.com"
        assert tab.title == "Example"
        assert tab.type == "page"
        assert tab.web_socket_debugger_url == "ws://localhost:9222/devtools/page/tab123"

    def test_from_dict_partial(self):
        """Tab handles missing fields gracefully."""
        data = {"id": "tab456"}
        tab = Tab.from_dict(data)
        assert tab.id == "tab456"
        assert tab.url == ""
        assert tab.title == ""
        assert tab.type == "page"
        assert tab.web_socket_debugger_url == ""

    def test_repr(self):
        """Tab repr is readable."""
        tab = Tab(
            id="abcdefghijkl",
            url="https://example.com/very/long/path",
            title="A Very Long Title Here",
            type="page",
            web_socket_debugger_url="ws://localhost:9222/devtools/page/abcdefghijkl",
        )
        r = repr(tab)
        assert "abcdefgh" in r
        assert "A Very" in r


class TestAXNode:
    """Tests for AXNode model."""

    def test_minimal(self):
        """AXNode creates with minimal fields."""
        node = AXNode(ref="ref1", role="link", name="Click here")
        assert node.ref == "ref1"
        assert node.role == "link"
        assert node.name == "Click here"
        assert node.value is None
        assert node.focused is False
        assert node.children == []

    def test_with_children(self):
        """AXNode creates with children."""
        child = AXNode(ref="c1", role="link", name="Child")
        root = AXNode(ref="r2", role="root", name="Root", children=[child])
        assert len(root.children) == 1
        assert root.children[0].ref == "c1"

    def test_find(self):
        """AXNode.find locates node by ref."""
        child = AXNode(ref="c1", role="link", name="Child")
        root = AXNode(ref="r1", role="root", name="Root", children=[child])
        assert root.find("r1") is root
        assert root.find("c1") is child
        assert root.find("nonexistent") is None

    def test_find_by_role(self):
        """AXNode.find_by_role finds all matching roles."""
        root = AXNode(
            ref="r1",
            role="root",
            name="Root",
            children=[
                AXNode(ref="r2", role="link", name="Link 1"),
                AXNode(ref="r3", role="heading", name="Heading"),
                AXNode(ref="r4", role="link", name="Link 2"),
            ],
        )
        links = root.find_by_role("link")
        assert len(links) == 2
        assert links[0].name == "Link 1"
        assert links[1].name == "Link 2"

    def test_find_by_name(self):
        """AXNode.find_by_name is case-insensitive."""
        root = AXNode(
            ref="r1",
            role="root",
            name="Root",
            children=[
                AXNode(ref="r2", role="link", name="Search Button"),
                AXNode(ref="r3", role="button", name="Cancel"),
            ],
        )
        results = root.find_by_name("search")
        assert len(results) == 1
        assert results[0].name == "Search Button"

    def test_find_by_name_empty(self):
        """AXNode.find_by_name returns empty for None/empty."""
        node = AXNode(ref="r1", role="link", name="Test")
        assert node.find_by_name(None) == []
        assert node.find_by_name("") == []

    def test_find_interactive(self):
        """AXNode.find_interactive finds interactive elements."""
        root = AXNode(
            ref="r1",
            role="root",
            name="Root",
            children=[
                AXNode(ref="r2", role="link", name="Link"),
                AXNode(ref="r3", role="heading", name="Heading"),
                AXNode(ref="r4", role="button", name="Button"),
                AXNode(ref="r5", role="textbox", name="Input"),
            ],
        )
        interactive = root.find_interactive()
        assert len(interactive) == 3
        roles = {n.role for n in interactive}
        assert "link" in roles
        assert "button" in roles
        assert "textbox" in roles

    def test_to_tree_str(self):
        """AXNode.to_tree_str formats as tree."""
        child = AXNode(ref="c1", role="link", name="Child link")
        root = AXNode(ref="r1", role="root", name="Root", children=[child])
        output = root.to_tree_str()
        assert "Root" in output
        assert "Child link" in output
        assert "root" in output
        assert "link" in output

    def test_to_tree_str_compact(self):
        """AXNode.to_tree_str compact format."""
        node = AXNode(ref="r1", role="link", name="Test")
        output = node.to_tree_str(fmt="compact")
        assert "link" in output
        assert "r1" in output

    def test_to_dict(self):
        """AXNode.to_dict serializes to dict."""
        node = AXNode(ref="r1", role="link", name="Test")
        d = node.to_dict()
        assert d["ref"] == "r1"
        assert d["role"] == "link"
        assert d["name"] == "Test"
        assert d["children"] == []


class TestBrowserInfo:
    """Tests for BrowserInfo model."""

    def test_from_dict(self):
        """BrowserInfo parses Chrome /json/version response."""
        data = {
            "Browser": "Chrome/120.0.0.0",
            "Protocol-Version": "1.3",
            "User-Agent": "Mozilla/5.0 ...",
            "V8-Version": "12.0.0.0",
            "WebKit-Version": "537.36",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser",
        }
        info = BrowserInfo.from_dict(data)
        assert "Chrome" in info.browser
        assert info.protocol_version == "1.3"
        assert info.v8_version == "12.0.0.0"

    def test_from_dict_partial(self):
        """BrowserInfo handles missing fields."""
        data = {}
        info = BrowserInfo.from_dict(data)
        assert info.browser == ""
        assert info.protocol_version == ""


class TestAction:
    """Tests for Action model."""

    def test_action_creation(self):
        """Action dataclass creates correctly."""
        action = Action(type="click", timestamp=time.time(), params={"ref": "r1"})
        assert action.type == "click"
        assert "ref" in action.params

    def test_action_to_dict(self):
        """Action serializes to dict with params flattened."""
        action = Action(
            type="fill", timestamp=1000.0, params={"ref": "r1", "value": "hi"}
        )
        d = action.to_dict()
        assert d["type"] == "fill"
        assert d["timestamp"] == 1000.0
        assert d["ref"] == "r1"
        assert d["value"] == "hi"


class TestComparisonResult:
    """Tests for ComparisonResult model."""

    def test_pass(self):
        """ComparisonResult with passed checks."""
        result = ComparisonResult(
            match=True,
            diff_pixels=0,
            diff_percentage=0.0,
            baseline_size=(1920, 1080),
            current_size=(1920, 1080),
        )
        assert result.match is True
        assert result.diff_pixels == 0

    def test_fail(self):
        """ComparisonResult with failures."""
        result = ComparisonResult(
            match=False,
            diff_pixels=1500,
            diff_percentage=0.05,
            baseline_size=(1920, 1080),
            current_size=(1920, 1080),
            diff_path="/tmp/diff.png",
            message="Images differ",
        )
        assert result.match is False
        assert result.diff_pixels == 1500
        assert result.diff_path == "/tmp/diff.png"
        assert result.message == "Images differ"
