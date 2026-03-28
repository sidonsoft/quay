"""Tests for quay.errors — error types with context."""
from __future__ import annotations


from quay.errors import (
    BrowserError,
    ConnectionError,
    TabError,
    TimeoutError,
    CDPError,
)


class TestBrowserError:
    def test_basic(self):
        err = BrowserError("Something failed")
        assert str(err) == "Something failed"
        assert err.context == {}

    def test_with_context(self):
        err = BrowserError("Failed", context={"url": "https://x.com", "code": 500})
        s = str(err)
        assert "Failed" in s
        assert "url=https://x.com" in s
        assert "code=500" in s

    def test_repr(self):
        err = BrowserError("Oops", context={"key": "val"})
        r = repr(err)
        assert "BrowserError" in r
        assert "Oops" in r

    def test_context_none_values_filtered(self):
        err = BrowserError("msg", context={"a": None, "b": "val"})
        s = str(err)
        assert "a=" not in s
        assert "b=val" in s

    def test_inheritance(self):
        """All error types should inherit from BrowserError."""
        assert issubclass(ConnectionError, BrowserError)
        assert issubclass(TabError, BrowserError)
        assert issubclass(TimeoutError, BrowserError)
        assert issubclass(CDPError, BrowserError)


class TestErrorCreation:
    """Test that errors can be created with basic args."""
    
    def test_connection_error(self):
        err = ConnectionError("Failed to connect")
        assert "Failed" in str(err)

    def test_tab_error(self):
        err = TabError("Tab not found")
        assert "Tab" in str(err)

    def test_timeout_error(self):
        err = TimeoutError("Operation timed out")
        assert "timed out" in str(err).lower() or "timeout" in str(err).lower()

    def test_cdp_error(self):
        err = CDPError("CDP error", code=-32000)
        assert "CDP" in str(err) or "-32000" in str(err)