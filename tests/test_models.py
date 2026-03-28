"""Tests for quay.models — data classes and serialization."""
from __future__ import annotations


from quay.models import Tab, AXNode, ComparisonResult, Action, Recording


class TestTab:
    def test_create_basic(self):
        tab = Tab(id="123", url="https://example.com", title="Example", type="page", web_socket_debugger_url="ws://localhost:9222/devtools/page/123")
        assert tab.id == "123"
        assert tab.url == "https://example.com"
        assert tab.title == "Example"
        assert tab.type == "page"

    def test_from_dict(self):
        data = {"id": "456", "url": "https://test.com", "title": "Test", "type": "page", "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/456"}
        tab = Tab.from_dict(data)
        assert tab.id == "456"
        assert tab.url == "https://test.com"
        assert tab.title == "Test"

    def test_from_dict_defaults(self):
        data = {"id": "789"}
        tab = Tab.from_dict(data)
        assert tab.id == "789"
        assert tab.url == ""
        assert tab.title == ""
        assert tab.type == "page"

    def test_repr_truncation(self):
        tab = Tab(id="very-long-id-12345678", url="https://example.com/very/long/path", title="A Very Long Title That Should Be Truncated", type="page", web_socket_debugger_url="ws://localhost:9222")
        r = repr(tab)
        assert "Tab(" in r
        assert "..." in r


class TestAXNode:
    def test_create_basic(self):
        node = AXNode(ref="1", role="button", name="Click me")
        assert node.ref == "1"
        assert node.role == "button"
        assert node.name == "Click me"

    def test_create_with_children(self):
        parent = AXNode(ref="1", role="root", name="", children=[
            AXNode(ref="2", role="link", name="About"),
            AXNode(ref="3", role="link", name="Contact"),
        ])
        assert len(parent.children) == 2
        assert parent.children[0].name == "About"

    def test_find_exists(self):
        tree = AXNode(ref="1", role="RootWebArea", name="Page", children=[
            AXNode(ref="2", role="link", name="Click here"),
            AXNode(ref="3", role="button", name="Submit"),
        ])
        result = tree.find("2")
        assert result is not None
        assert result.name == "Click here"

    def test_find_not_found(self):
        tree = AXNode(ref="1", role="RootWebArea", name="Page")
        assert tree.find("999") is None

    def test_find_nested(self):
        tree = AXNode(ref="1", role="RootWebArea", name="", children=[
            AXNode(ref="2", role="group", name="", children=[
                AXNode(ref="3", role="link", name="Deep"),
            ]),
        ])
        result = tree.find("3")
        assert result is not None
        assert result.name == "Deep"

    def test_find_by_role(self):
        tree = AXNode(ref="1", role="RootWebArea", name="Page", children=[
            AXNode(ref="2", role="link", name="Home"),
            AXNode(ref="3", role="button", name="Submit"),
            AXNode(ref="4", role="link", name="About"),
        ])
        links = tree.find_by_role("link")
        assert len(links) == 2
        names = [n.name for n in links]
        assert "Home" in names
        assert "About" in names

    def test_find_by_name(self):
        tree = AXNode(ref="1", role="RootWebArea", name="Page", children=[
            AXNode(ref="2", role="link", name="Click here"),
            AXNode(ref="3", role="button", name="Click here"),
            AXNode(ref="4", role="link", name="Other"),
        ])
        matches = tree.find_by_name("Click here")
        assert len(matches) == 2

    def test_find_interactive(self):
        tree = AXNode(ref="1", role="RootWebArea", name="Page", children=[
            AXNode(ref="2", role="link", name="Home"),
            AXNode(ref="3", role="button", name="Submit"),
            AXNode(ref="4", role="textbox", name="Username"),
            AXNode(ref="5", role="checkbox", name="Remember"),
            AXNode(ref="6", role="heading", name="Title"),
        ])
        interactive = tree.find_interactive()
        roles = {n.role for n in interactive}
        assert "link" in roles
        assert "button" in roles
        assert "textbox" in roles
        assert "checkbox" in roles
        assert "heading" not in roles

    def test_to_tree_str(self):
        tree = AXNode(ref="1", role="RootWebArea", name="Page", children=[
            AXNode(ref="2", role="link", name="Home"),
        ])
        s = tree.to_tree_str()
        assert "RootWebArea" in s
        assert "link" in s
        assert "Home" in s


class TestComparisonResult:
    def test_match(self):
        result = ComparisonResult(
            match=True,
            diff_pixels=0,
            diff_percentage=0.0,
            baseline_size=(100, 100),
            current_size=(100, 100),
            diff_path=None,
            message="Identical"
        )
        assert result.match is True
        assert result.diff_pixels == 0

    def test_no_match(self):
        result = ComparisonResult(
            match=False,
            diff_pixels=100,
            diff_percentage=5.5,
            baseline_size=(100, 100),
            current_size=(100, 100),
            diff_path="/tmp/diff.png",
            message="Screenshots differ"
        )
        assert result.match is False
        assert result.diff_percentage == 5.5


class TestAction:
    def test_create(self):
        action = Action(type="click", timestamp=1.0, params={"x": 10, "y": 20})
        assert action.type == "click"
        assert action.timestamp == 1.0
        assert action.params["x"] == 10

    def test_from_dict(self):
        action = Action.from_dict({"type": "type", "timestamp": 0.5, "text": "hello"})
        assert action.type == "type"
        assert "text" in action.params


class TestRecording:
    def test_create_empty(self):
        rec = Recording()
        assert len(rec.actions) == 0

    def test_actions_append(self):
        rec = Recording()
        rec.start_time = 0.0
        action = Action(type="click", timestamp=0.5, params={"x": 10})
        rec.actions.append(action)
        assert len(rec.actions) == 1
        assert rec.actions[0].type == "click"

    def test_to_dict(self):
        rec = Recording()
        rec.start_time = 0.0
        action = Action(type="click", timestamp=0.5, params={"x": 10})
        rec.actions.append(action)
        d = rec.to_dict()
        assert "actions" in d
        assert len(d["actions"]) == 1