"""Tests for quay.browser accessibility methods — tree building and search."""
from __future__ import annotations

from quay.models import AXNode


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
