from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .errors import TabError
from .models import AXNode


class BrowserAccessibilityMixin:
    """Accessibility tree parsing for Browser.
    
    Requires: BrowserCoreMixin, BrowserTabsMixin
    """

    def accessibility_tree(self, tab=None, timeout=None, refresh=False, cache=None) -> AXNode:
        target_tab = tab or self.current_tab
        if not target_tab:
            tabs = self.list_tabs()  # type: ignore[attr-defined]
            if not tabs:
                raise TabError("No tabs available")
            target_tab = tabs[0]
            self.current_tab = target_tab
        tab_id = target_tab.id
        use_cache = cache if cache is not None else self.cache_accessibility
        if use_cache and not refresh and tab_id in self._accessibility_cache:  # type: ignore[attr-defined]
            return self._accessibility_cache[tab_id]  # type: ignore[attr-defined]
        async def _get_tree():
            conn = await self._get_connection(target_tab)  # type: ignore[attr-defined]
            result = await self._send_cdp(conn, "Accessibility.getFullAXTree", domains=["Accessibility"], timeout=timeout)  # type: ignore[attr-defined]
            return self._parse_ax_nodes(result.get("nodes", []))
        return self._run_async(_get_tree())  # type: ignore[attr-defined]

    def _parse_ax_nodes(self, nodes: list[dict]) -> AXNode:
        def parse_node(node: dict) -> AXNode:
            return AXNode(
                ref=str(node.get("nodeId", "")),
                role=node.get("role", {}).get("value", ""),
                name=node.get("name", {}).get("value", ""),
                value=node.get("value", {}).get("value", ""),
                url=node.get("url"),
                level=node.get("hierarchicalLevel"),
                focused=node.get("focused", False),
                description=node.get("description", {}).get("value", ""),
                children=[parse_node(c) for c in node.get("children", [])],
            )
        root = nodes[0] if nodes else {}
        return parse_node(root)

    def accessibility_find(self, predicate, tab=None, timeout=None) -> list[AXNode]:
        tree = self.accessibility_tree(tab=tab, timeout=timeout)
        results = []
        def find_in_node(node: AXNode):
            if predicate(node):
                results.append(node)
            for child in node.children:
                find_in_node(child)
        find_in_node(tree)
        return results

    def find_by_ref(self, ref: str, tab=None, timeout=None) -> AXNode | None:
        def matches(node):
            return node.ref == ref or node.ref == ref.lstrip("axnode@")
        results = self.accessibility_find(matches, tab=tab, timeout=timeout)
        return results[0] if results else None

    def find_by_role(self, role: str, tab=None, timeout=None) -> list[AXNode]:
        return self.accessibility_find(lambda n: n.role == role, tab=tab, timeout=timeout)

    def find_by_name(self, name: str, tab=None, timeout=None) -> list[AXNode]:
        return self.accessibility_find(lambda n: name in n.name, tab=tab, timeout=timeout)

    def find_by_value(self, value: str, tab=None, timeout=None) -> list[AXNode]:
        return self.accessibility_find(lambda n: value in n.value, tab=tab, timeout=timeout)