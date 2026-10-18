"""
MCP (Model Context Protocol) server for quay.

Exposes browser automation tools over stdio so MCP-capable agents
(Claude Code, Codex, OpenClaw, etc.) can drive the user's real
logged-in Chrome through quay.

Requires the optional dependency:  pip install "quay[mcp]"
Run with:  quay mcp [--host HOST] [--port PORT]

Design notes:
- MCP tool handlers run on AnyIO worker threads. Browser's sync API needs a
  running event loop that is *not* the caller's thread (it uses
  ``asyncio.run_coroutine_threadsafe``), so the server owns a dedicated loop
  thread and re-points Browser at it after construction.
- Tools return plain text and never raise: errors come back as
  ``Error: ...`` strings, which is what agents expect to read.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from ._version import __version__

logger = logging.getLogger("quay.mcp")

_SERVER_INSTRUCTIONS = (
    "quay controls the user's real, logged-in Google Chrome via the Chrome "
    "DevTools Protocol. Typical loop: browser_status -> open_tab/navigate -> "
    "snapshot (returns the accessibility tree; interactive elements carry refs "
    "like axnode@42) -> click_ref/fill_form -> snapshot to verify. Prefer "
    "click_ref with refs from snapshot over click_text when multiple matches "
    "are possible. Screenshots are saved on the machine running this server."
)


def create_server(
    host: str = "localhost",
    port: int = 9222,
    browser: Any = None,
):
    """
    Build the MCP server, connected to a live Browser instance.

    Args:
        host: Chrome DevTools host
        port: Chrome DevTools port
        browser: Pre-built Browser (or test double). When None, a Browser is
            constructed and wired to a dedicated event-loop thread.

    Returns:
        mcp MCPServer instance with quay tools registered.

    Raises:
        RuntimeError: If the optional ``mcp`` dependency is not installed.
    """
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as e:
        raise RuntimeError(
            'MCP support requires the optional dependency: pip install "quay[mcp]"'
        ) from e

    server = MCPServer(
        name="quay",
        version=__version__,
        instructions=_SERVER_INSTRUCTIONS,
    )

    if browser is None:
        from .browser import Browser

        # Dedicated event loop thread — see module docstring.
        loop = asyncio.new_event_loop()
        threading.Thread(target=loop.run_forever, name="quay-mcp-loop", daemon=True).start()

        browser = Browser(host=host, port=port)
        # Close pool connections created during construction — they belong to
        # the construction-time loop, not the dedicated server loop.
        if browser._pool is not None and browser._loop is not None:
            if not browser._loop.is_running():
                try:
                    browser._loop.run_until_complete(browser._pool.close_all())
                except Exception:  # pragma: no cover - best-effort cleanup
                    logger.debug("pool cleanup during mcp wiring failed", exc_info=True)
        # Re-point Browser at the always-running loop; next _get_pool() will
        # create connections bound to it.
        browser._loop = loop
        browser._pool = None

    # ── status / tabs ─────────────────────────────────────────────────────

    @server.tool(
        name="browser_status",
        description="Show the connected Chrome version and list open tabs (ids, titles, URLs).",
    )
    def browser_status() -> str:
        try:
            info = browser.get_version()
            tabs = browser.list_tabs()
            lines = [f"Chrome: {info.browser}", f"Tabs: {len(tabs)}"]
            for t in tabs:
                lines.append(f"  [{t.id[:12]}] {t.title[:40]} - {t.url[:80]}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    @server.tool(
        name="open_tab",
        description="Open a new browser tab at the given URL. Returns the tab id and final URL.",
    )
    def open_tab(url: str) -> str:
        try:
            tab = browser.new_tab(url)
            return f"Opened tab [{tab.id[:12]}] {tab.url}"
        except Exception as e:
            return f"Error: {e}"

    @server.tool(
        name="navigate",
        description="Navigate the current tab (or the first tab) to a URL.",
    )
    def navigate(url: str) -> str:
        try:
            if not browser.current_tab:
                tabs = browser.list_tabs()
                if tabs:
                    browser.current_tab = tabs[0]
            browser.navigate(url)
            return f"Navigated to: {url}"
        except Exception as e:
            return f"Error: {e}"

    # ── accessibility tree ────────────────────────────────────────────────

    @server.tool(
        name="snapshot",
        description=(
            "Accessibility-tree snapshot of the current page. Interactive nodes "
            "carry refs (axnode@N) usable by click_ref. Output truncated to "
            "max_chars."
        ),
    )
    def snapshot(max_chars: int = 10000) -> str:
        try:
            tree = browser.accessibility_tree()
            return tree.to_tree_str(max_length=max_chars)
        except Exception as e:
            return f"Error: {e}"

    # ── actions ───────────────────────────────────────────────────────────

    @server.tool(
        name="click_text",
        description=(
            "Click the first element containing the given visible text "
            "(links, buttons). Returns true/false."
        ),
    )
    def click_text(text: str) -> str:
        try:
            return f"Clicked: {browser.click_by_text(text)}"
        except Exception as e:
            return f"Error: {e}"

    @server.tool(
        name="click_ref",
        description=(
            "Click an element by its accessibility ref from snapshot "
            "(e.g. 'axnode@42'). Precise; use over click_text when unsure."
        ),
    )
    def click_ref(ref: str) -> str:
        try:
            return f"Clicked: {browser.click(ref)}"
        except Exception as e:
            return f"Error: {e}"

    @server.tool(
        name="fill_form",
        description=(
            "Fill form fields by label or name. fields is a JSON object of "
            "{label: value}. Returns per-field success."
        ),
    )
    def fill_form(fields: dict[str, str]) -> str:
        try:
            results = browser.fill_form(fields)
            lines = [f"  {k}: {'ok' if v else 'FAILED'}" for k, v in results.items()]
            return "Fill results:\n" + "\n".join(lines) if lines else "No fields given."
        except Exception as e:
            return f"Error: {e}"

    @server.tool(
        name="evaluate",
        description="Execute JavaScript in the current tab and return the result.",
    )
    def evaluate(script: str) -> str:
        try:
            return str(browser.evaluate(script))
        except Exception as e:
            return f"Error: {e}"

    @server.tool(
        name="screenshot",
        description=(
            "Screenshot the current tab. Saved on the server machine; returns "
            "the file path. Provide path or a temp file is used."
        ),
    )
    def screenshot(path: str | None = None) -> str:
        try:
            if path is None:
                import tempfile

                fd, path = tempfile.mkstemp(suffix=".png", prefix="quay-")
                import os

                os.close(fd)
            browser.screenshot(path)
            return f"Saved: {path}"
        except Exception as e:
            return f"Error: {e}"

    @server.tool(
        name="close_tabs",
        description=(
            "Close tab ids (list). With no ids, closes all non-chrome:// tabs. "
            "Never closes Chrome itself."
        ),
    )
    def close_tabs(ids: list[str] | None = None) -> str:
        try:
            closed = []
            if ids:
                for tab_id in ids:
                    browser.close_tab(tab_id)
                    closed.append(tab_id[:12])
            else:
                for t in browser.list_tabs():
                    if not t.url.startswith("chrome://"):
                        browser.close_tab(t.id)
                        closed.append(t.id[:12])
            return (
                f"Closed {len(closed)} tab(s): {', '.join(closed)}"
                if closed
                else "Nothing to close."
            )
        except Exception as e:
            return f"Error: {e}"

    return server


def run_server(host: str = "localhost", port: int = 9222) -> None:
    """Create the quay MCP server and serve it over stdio (blocking)."""
    server = create_server(host=host, port=port)
    logger.info("quay MCP server: serving stdio (Chrome %s:%s)", host, port)
    server.run(transport="stdio")
