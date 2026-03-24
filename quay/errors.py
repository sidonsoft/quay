"""
Browser Hybrid - Exception hierarchy with actionable error messages.

All exceptions include context for debugging.
"""

from __future__ import annotations

from typing import Any


class BrowserError(Exception):
    """
    Base exception for browser operations.

    All exceptions inherit from this for easy catching.

    Example:
        try:
            browser.navigate(url)
        except BrowserError as e:
            print(f"Failed: {e}")
            print(f"Context: {e.context}")
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        self.context = context or {}
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items() if v is not None)
            if ctx_str:
                return f"{base} [{ctx_str}]"
        return base

    def __repr__(self) -> str:
        """Standard repr including context."""
        base = f"{self.__class__.__name__}: {self.args[0]}"
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items() if v is not None)
            if ctx_str:
                return f"{base} [{ctx_str}]"
        return base


class ConnectionError(BrowserError):
    """
    Chrome not running or debug port unavailable.

    Example:
        ConnectionError("Chrome DevTools not reachable", host="localhost", port=9222)
    """

    def __init__(
        self,
        message: str = "Chrome DevTools not reachable",
        host: str | None = None,
        port: int | None = None,
        original_error: Exception | None = None,
    ):
        context = {
            "host": host,
            "port": port,
            "original": str(original_error) if original_error else None,
        }
        super().__init__(message, context)
        self.host = host
        self.port = port
        self.original_error = original_error


class TabError(BrowserError):
    """
    Tab not found or operation failed.

    Example:
        TabError("Tab not found", tab_id="abc123", operation="navigate")
    """

    def __init__(
        self,
        message: str,
        tab_id: str | None = None,
        operation: str | None = None,
    ):
        context = {"tab_id": tab_id, "operation": operation}
        super().__init__(message, context)
        self.tab_id = tab_id
        self.operation = operation


class TimeoutError(BrowserError):
    """
    Operation timed out.

    Example:
        TimeoutError("Navigation timed out", timeout=30.0, operation="navigate")
    """

    def __init__(
        self,
        message: str,
        timeout: float | None = None,
        operation: str | None = None,
    ):
        context = {"timeout": timeout, "operation": operation}
        super().__init__(message, context)
        self.timeout = timeout
        self.operation = operation


class CDPError(BrowserError):
    """
    Chrome DevTools Protocol error.

    CDP returns errors with codes and messages. This maps them to specific errors.

    Example:
        CDPError("Invalid node", code=-32000, method="DOM.resolveNode")
    """

    # CDP error codes
    CODES = {
        -32700: "Parse error",
        -32600: "Invalid request",
        -32601: "Method not found",
        -32602: "Invalid params",
        -32603: "Internal error",
        -32000: "Server error",
    }

    def __init__(
        self,
        message: str,
        code: int | None = None,
        method: str | None = None,
        params: dict[str, Any] | None = None,
    ):
        context = {
            "code": code,
            "method": method,
            "params": params,
            "description": self.CODES.get(code) if code else None,
        }
        super().__init__(message, context)
        self.code = code
        self.method = method
        self.params = params


def parse_cdp_error(response: dict[str, Any], method: str | None = None) -> CDPError | None:
    """
    Parse CDP error response into CDPError.

    Args:
        response: CDP response dict
        method: The method that was called (for context)

    Returns:
        CDPError if response has error, None otherwise

    Example:
        result = await ws.send(...)
        if error := parse_cdp_error(result, "Page.navigate"):
            raise error
    """
    if "error" not in response:
        return None

    error = response["error"]
    code = error.get("code")
    message = error.get("message", "Unknown CDP error")
    params = response.get("params")

    return CDPError(
        message=f"CDP error: {message}",
        code=code,
        method=method,
        params=params,
    )
