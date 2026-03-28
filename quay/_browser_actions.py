from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .errors import BrowserError
from .models import ComparisonResult

logger = logging.getLogger(__name__)

AX_REF_PATTERN = __import__("re").compile(r"^(axnode@)?\d+$")


def _validate_ref(ref: str) -> None:
    if not AX_REF_PATTERN.match(ref):
        raise ValueError(f"Invalid ref format: {ref!r}. Expected format: 'axnode@<number>' or '<number>'")


_KEY_MAP = {
    "Enter": {"key": "Enter", "code": "Enter", "keyCode": 13, "text": "\r"},
    "Space": {"key": "Space", "code": "Space", "keyCode": 32, "text": " "},
    "Tab": {"key": "Tab", "code": "Tab", "keyCode": 9},
    "Escape": {"key": "Escape", "code": "Escape", "keyCode": 27},
    "Backspace": {"key": "Backspace", "code": "Backspace", "keyCode": 8, "text": "\b"},
    "Delete": {"key": "Delete", "code": "Delete", "keyCode": 46},
    "ArrowUp": {"key": "ArrowUp", "code": "ArrowUp", "keyCode": 38},
    "ArrowDown": {"key": "ArrowDown", "code": "ArrowDown", "keyCode": 40},
    "ArrowLeft": {"key": "ArrowLeft", "code": "ArrowLeft", "keyCode": 37},
    "ArrowRight": {"key": "ArrowRight", "code": "ArrowRight", "keyCode": 39},
    "Home": {"key": "Home", "code": "Home", "keyCode": 36},
    "End": {"key": "End", "code": "End", "keyCode": 35},
    "PageUp": {"key": "PageUp", "code": "PageUp", "keyCode": 33},
    "PageDown": {"key": "PageDown", "code": "PageDown", "keyCode": 34},
}


def _key_to_key_definition(key: str, modifiers: int = 0) -> dict:
    if len(key) == 1:
        return {"key": key, "code": f"Key{key.upper()}" if key.isalpha() else key, "text": key, "modifiers": modifiers}
    if key in _KEY_MAP:
        return {**_KEY_MAP[key], "modifiers": modifiers}
    return {"key": key, "code": key, "modifiers": modifiers}


class BrowserActionsMixin:
    """Browser action methods (click, type, screenshot, etc.).
    
    Requires: BrowserCoreMixin
    """
    
    def click_by_text(self, text: str, tab=None, timeout=None, *, double=False, button="left") -> bool:
        async def _click():
            # Find element by text
            nodes = self.find_by_name(text, tab=tab, timeout=timeout)  # type: ignore[attr-defined]
            if not nodes:
                raise BrowserError(f"Element with text '{text}' not found")
            node = nodes[0]
            conn = await self._get_connection(node)  # type: ignore[attr-defined]
            # Click the element
            await conn.send("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "x": 0, "y": 0,
                "button": button,
                "clickCount": 2 if double else 1
            })
            await conn.send("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "x": 0, "y": 0,
                "button": button,
                "clickCount": 2 if double else 1
            })
            return True
        return self._run_async(_click())  # type: ignore[attr-defined]

    def type_text(self, text: str, tab=None, timeout=None, *, slowly=False) -> bool:
        async def _type():
            conn = await self._get_connection(tab)  # type: ignore[attr-defined]
            for char in text:
                await conn.send("Input.dispatchKeyEvent", {
                    "type": "keyDown",
                    "text": char
                })
                if slowly:
                    import asyncio
                    await asyncio.sleep(0.05)
                await conn.send("Input.dispatchKeyEvent", {
                    "type": "keyUp",
                    "text": char
                })
            return True
        return self._run_async(_type())  # type: ignore[attr-defined]

    def evaluate(self, script: str, tab=None, timeout=None) -> Any:
        async def _eval():
            conn = await self._get_connection(tab)  # type: ignore[attr-defined]
            result = await self._send_cdp(conn, "Runtime.evaluate", {  # type: ignore[attr-defined]
                "expression": script,
                "returnByValue": True,
            }, domains=["Runtime"], timeout=timeout)
            return result.get("result", {}).get("value")
        return self._run_async(_eval())  # type: ignore[attr-defined]

    def screenshot(self, path=None, tab=None, timeout=None, full_page=False) -> bytes | str:
        async def _screenshot():
            conn = await self._get_connection(tab)  # type: ignore[attr-defined]
            result = await self._send_cdp(conn, "Page.captureScreenshot", {  # type: ignore[attr-defined]
                "format": "png",
                "captureBeyondViewport": full_page
            }, domains=["Page"], timeout=timeout)
            data = base64.b64decode(result.get("data", ""))
            if path:
                with open(path, "wb") as f:
                    f.write(data)
                return path
            return data
        return self._run_async(_screenshot())  # type: ignore[attr-defined]

    def compare_screenshots(self, baseline: str | bytes, current: str | bytes, threshold=0.01) -> ComparisonResult:
        """Compare two screenshots and return comparison result."""
        # Simple implementation - would use PIL/Pillow in production
        if isinstance(baseline, str):
            with open(baseline, "rb") as f:
                baseline_data = f.read()
        else:
            baseline_data = baseline
        if isinstance(current, str):
            with open(current, "rb") as f:
                current_data = f.read()
        else:
            current_data = current
        # Placeholder comparison
        match = baseline_data == current_data
        diff_pixels = 0 if match else len(baseline_data)
        return ComparisonResult(match=match, diff_pixels=diff_pixels, baseline_path=baseline if isinstance(baseline, str) else None, current_path=current if isinstance(current, str) else None)