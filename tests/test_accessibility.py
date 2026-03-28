"""Tests for quay._browser_accessibility — AXNode parsing and search."""
from __future__ import annotations


from quay.models import AXNode


class TestAXNodeParsing:
    def test_parse_simple_node(self):
        """Parsing a simple accessibility node should create AXNode."""
        from quay._browser_accessibility import BrowserAccessibilityMixin
        
        mixin = BrowserAccessibilityMixin()
        
        cdp_nodes = [{
            "nodeId": "42",
            "role": {"value": "button"},
            "name": {"value": "Click me"},
        }]
        
        result = mixin._parse_ax_nodes(cdp_nodes)
        assert result.ref == "42"
        assert result.role == "button"
        assert result.name == "Click me"

    def test_parse_with_children(self):
        """Parsing should recursively handle children."""
        from quay._browser_accessibility import BrowserAccessibilityMixin
        
        mixin = BrowserAccessibilityMixin()
        
        cdp_nodes = [{
            "nodeId": "1",
            "role": {"value": "RootWebArea"},
            "name": {"value": "Page"},
            "children": [
                {
                    "nodeId": "2",
                    "role": {"value": "link"},
                    "name": {"value": "Home"},
                },
                {
                    "nodeId": "3",
                    "role": {"value": "button"},
                    "name": {"value": "Submit"},
                },
            ],
        }]
        
        result = mixin._parse_ax_nodes(cdp_nodes)
        assert result.ref == "1"
        assert len(result.children) == 2
        assert result.children[0].name == "Home"
        assert result.children[1].name == "Submit"

    def test_parse_uses_ref_not_id(self):
        """Parsing should set 'ref' field, not 'id' (AXNode uses ref)."""
        from quay._browser_accessibility import BrowserAccessibilityMixin
        
        mixin = BrowserAccessibilityMixin()
        
        cdp_nodes = [{
            "nodeId": "123",
            "role": {"value": "textbox"},
            "name": {"value": "Username"},
        }]
        
        result = mixin._parse_ax_nodes(cdp_nodes)
        assert hasattr(result, "ref")
        assert result.ref == "123"
        # Should NOT have 'id' or 'ignored' fields
        assert not hasattr(result, "id")


class TestAXNodeMethods:
    def test_find_interactive_includes_links_buttons(self):
        """find_interactive should return actionable elements."""
        tree = AXNode(ref="1", role="RootWebArea", name="Page", children=[
            AXNode(ref="2", role="link", name="Home"),
            AXNode(ref="3", role="button", name="Submit"),
            AXNode(ref="4", role="textbox", name="Email"),
            AXNode(ref="5", role="checkbox", name="Remember me"),
            AXNode(ref="6", role="heading", name="Welcome"),
        ])
        
        interactive = tree.find_interactive()
        roles = {n.role for n in interactive}
        
        assert "link" in roles
        assert "button" in roles
        assert "textbox" in roles
        assert "checkbox" in roles
        # Non-interactive should not be included
        assert "heading" not in roles

    def test_axnode_parent_reference(self):
        """Children should have parent references."""
        parent = AXNode(ref="1", role="group", name="", children=[
            AXNode(ref="2", role="button", name="OK"),
        ])
        
        # Set parent references
        for child in parent.children:
            child.parent = parent
        
        assert parent.children[0].parent is parent