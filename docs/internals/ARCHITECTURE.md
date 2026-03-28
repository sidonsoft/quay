# Quay Architecture

Quay uses a **mixin-based architecture** for maintainability and modularity.

## Module Structure

The `Browser` class is composed of 8 focused mixins:

```
quay/
├── browser.py              # Main Browser class (41 lines)
├── _browser_core.py        # Connection lifecycle, HTTP helpers
├── _browser_tabs.py        # Tab CRUD operations
├── _browser_cdp.py         # Chrome DevTools Protocol low-level
├── _browser_navigation.py  # Navigation methods
├── _browser_wait.py        # Wait methods (8 variants)
├── _browser_accessibility.py  # Accessibility tree parsing
├── _browser_actions.py     # Click, type, screenshot, evaluate
├── _browser_recording.py   # Session recording & playback
├── connection.py           # WebSocket connection management
├── models.py               # Data models (Tab, AXNode, etc.)
└── errors.py               # Exception classes
```

## Mixin Composition

```python
class Browser(
    BrowserCoreMixin,        # Base: __init__, start, stop, connect
    BrowserTabsMixin,        # Tab management
    BrowserCDPMixin,         # Low-level CDP methods
    BrowserRecordingMixin,   # Session recording
    BrowserNavigationMixin,  # Navigation helpers
    BrowserWaitMixin,        # Wait methods
    BrowserAccessibilityMixin,  # Accessibility tree
    BrowserActionsMixin,     # User actions
):
    pass
```

## Mixin Responsibilities

| Mixin | Lines | Purpose |
|-------|-------|---------|
| `BrowserCoreMixin` | 229 | Connection pooling, HTTP helpers, `_run_async`, `_get_connection` |
| `BrowserTabsMixin` | 101 | `list_tabs`, `new_tab`, `close_tab`, `activate_tab` |
| `BrowserCDPMixin` | 45 | `_send_cdp`, low-level CDP communication |
| `BrowserNavigationMixin` | 33 | `navigate`, `goto` |
| `BrowserWaitMixin` | 109 | `wait_for`, `wait_for_url`, `wait_for_selector_*` |
| `BrowserAccessibilityMixin` | 73 | `accessibility_tree`, `find_by_ref`, `find_by_role` |
| `BrowserActionsMixin` | 122 | `click_by_text`, `type_text`, `evaluate`, `screenshot` |
| `BrowserRecordingMixin` | 76 | `start_recording`, `stop_recording`, `playback` |

## Why Mixins?

1. **Modularity**: Each feature area is isolated in its own file
2. **Testability**: Mixins can be tested independently
3. **Readability**: `browser.py` is 41 lines instead of 3,000+
4. **Extensibility**: Add new features by adding new mixins

## Key Design Decisions

### Type Hints with Mixins

Mixins access methods from other mixins they'll be combined with. Python's type system doesn't understand this by default, so we use:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._browser_core import BrowserCoreMixin

class BrowserWaitMixin:
    def wait_for(self, selector=None, text=None, tab=None, timeout=10.0) -> bool:
        # Type ignore for mixin cross-references
        resolved_tab = self._resolve_tab(tab)  # type: ignore[attr-defined]
```

### Public API Unchanged

All public methods remain on the `Browser` class:

```python
from quay import Browser

browser = Browser(port=9222)
browser.navigate("https://example.com")
browser.wait_for_selector_visible("#content")
tree = browser.accessibility_tree()
```

## Before vs After

| Metric | Before | After |
|--------|--------|-------|
| `browser.py` lines | 3,151 | 41 |
| Total mixin lines | — | 788 |
| Files | 1 | 9 |
| Max file size | 116KB | 8KB |

The refactoring reduced the monolithic `browser.py` from an unmaintainable 3,151 lines to a simple 41-line composition class, with all functionality preserved in focused mixin modules.