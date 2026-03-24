"""
Data models for browser-hybrid.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tab:
    """Represents a Chrome tab."""

    id: str
    url: str
    title: str
    type: str
    web_socket_debugger_url: str

    @classmethod
    def from_dict(cls, data: dict) -> Tab:
        """Create Tab from Chrome DevTools response."""
        return cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            title=data.get("title", ""),
            type=data.get("type", "page"),
            web_socket_debugger_url=data.get("webSocketDebuggerUrl", ""),
        )

    def __repr__(self) -> str:
        return f"Tab(id={self.id[:12]}..., title={self.title[:20]}..., url={self.url[:30]}...)"


@dataclass
class AXNode:
    """
    Accessibility tree node with ref for targeting.

    Usage:
        tree = browser.accessibility_tree()
        print(tree.to_tree_str())  # agent-browser format

        links = tree.find_by_role("link")
        for link in links:
            print(f"{link.ref}: {link.name}")

        node = tree.find("ref_id")
    """

    ref: str
    role: str
    name: str
    value: str | None = None
    url: str | None = None
    level: int | None = None
    focused: bool = False
    description: str | None = None
    children: list[AXNode] = field(default_factory=list)
    parent: AXNode | None = field(default=None, repr=False)

    def find(self, ref: str) -> AXNode | None:
        """Find node by accessibility ref."""
        if self.ref == ref:
            return self
        for child in self.children:
            found = child.find(ref)
            if found:
                return found
        return None

    def find_by_role(self, role: str) -> list[AXNode]:
        """Find all nodes with given ARIA role."""
        results = []
        if self.role == role:
            results.append(self)
        for child in self.children:
            results.extend(child.find_by_role(role))
        return results

    def find_by_name(self, text: str | None) -> list[AXNode]:
        """
        Find nodes containing text in accessible name (case-insensitive).

        Args:
            text: Text pattern to search for. Empty string or None returns no results.
        """
        if not text:
            return []

        results = []
        if text.lower() in self.name.lower():
            results.append(self)
        for child in self.children:
            results.extend(child.find_by_name(text))
        return results

    def find_interactive(self) -> list[AXNode]:
        """Find all interactive elements (links, buttons, inputs)."""
        interactive_roles = {
            "link",
            "button",
            "textbox",
            "checkbox",
            "radio",
            "combobox",
            "searchbox",
            "spinbutton",
            "slider",
            "menuitem",
            "tab",
            "switch",
        }
        results = []
        if self.role in interactive_roles:
            results.append(self)
        for child in self.children:
            results.extend(child.find_interactive())
        return results

    def to_tree_str(self, indent: int = 0, fmt: str = "text") -> str:
        """
        Format as tree string like agent-browser snapshot.

        Args:
            indent: Indentation level
            fmt: Output format - "text" (default) or "compact"

        Example:
            - RootWebArea "Page Title" [ref=1] /url: https://example.com/
        """
        if fmt == "compact":
            return f"{self.role}[{self.ref}]: {self.name}"

        lines = []
        prefix = "  " * indent + "- " if indent > 0 else "- "

        # Build the line
        attrs = [self.role]
        if self.name:
            attrs.append(f'"{self.name}"')
        if self.ref:
            attrs.append(f"[ref={self.ref}]")
        if self.level:
            attrs.append(f"[level={self.level}]")

        # Add URL if present
        if self.url:
            attrs.append(f"/url: {self.url}")

        # Add value for inputs
        if self.value:
            value_preview = (
                self.value[:50] + "..." if len(str(self.value)) > 50 else str(self.value)
            )
            attrs.append(f"/value: {value_preview}")

        lines.append(prefix + " ".join(attrs))

        # Recurse children
        for child in self.children:
            lines.append(child.to_tree_str(indent + 1, fmt=fmt))

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert node to dictionary."""
        return {
            "ref": self.ref,
            "role": self.role,
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "url": self.url,
            "level": self.level,
            "children": [c.to_dict() for c in self.children],
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Convert node to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class BrowserInfo:
    """Chrome version information."""

    browser: str
    protocol_version: str
    user_agent: str
    v8_version: str
    webkit_version: str
    web_socket_debugger_url: str

    @classmethod
    def from_dict(cls, data: dict) -> BrowserInfo:
        return cls(
            browser=data.get("Browser", ""),
            protocol_version=data.get("Protocol-Version", ""),
            user_agent=data.get("User-Agent", ""),
            v8_version=data.get("V8-Version", ""),
            webkit_version=data.get("WebKit-Version", ""),
            web_socket_debugger_url=data.get("webSocketDebuggerUrl", ""),
        )


@dataclass
class Action:
    """A recorded browser action."""

    type: str
    timestamp: float
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "timestamp": round(self.timestamp, 3),
            **self.params,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Action:
        """Create Action from dictionary."""
        # Deep copy to avoid mutating original dict
        data = data.copy()
        action_type = data.pop("type", "")
        timestamp = data.pop("timestamp", 0.0)
        return cls(type=action_type, timestamp=timestamp, params=data)


@dataclass
class Recording:
    """A recorded browser session."""

    path: str | None = None
    actions: list[Action] = field(default_factory=list)
    version: str = "1.0"
    quay_version: str | None = None
    recorded_at: str | None = None
    paused: bool = False
    start_time: float | None = None
    end_time: float | None = None

    def to_dict(self) -> dict:
        duration = 0.0
        if self.actions and self.start_time is not None:
            duration = round(self.actions[-1].timestamp, 3)
        return {
            "version": self.version,
            "quay_version": self.quay_version,
            "recorded_at": self.recorded_at,
            "actions": [a.to_dict() for a in self.actions],
            "metadata": {
                "total_duration": duration,
                "action_count": len(self.actions),
            },
        }

    @classmethod
    def from_dict(cls, data: dict, path: str | None = None) -> Recording:
        """Create Recording from dictionary."""
        actions_data = data.get("actions", [])
        actions = [Action.from_dict(a) for a in actions_data]

        return cls(
            path=path,
            actions=actions,
            version=data.get("version", "1.0"),
            quay_version=data.get("quay_version"),
            recorded_at=data.get("recorded_at"),
        )

    @classmethod
    def from_file(cls, path: str) -> Recording:
        """Load Recording from JSON file."""
        import json

        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data, path=path)

    def save(self, path: str | None = None) -> str:
        """Save recording to JSON file."""
        target_path = path or self.path
        if not target_path:
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
                target_path = f.name

        with open(target_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return target_path


@dataclass
class ComparisonResult:
    """Result of a screenshot comparison."""

    match: bool
    diff_pixels: int
    diff_percentage: float
    baseline_size: tuple[int, int]
    current_size: tuple[int, int]
    diff_path: str | None = None
    message: str = ""
