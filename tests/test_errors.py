"""Tests for quay.errors."""

import pytest

from quay.errors import BrowserError
from quay.errors import CDPError
from quay.errors import ConnectionError
from quay.errors import TabError
from quay.errors import TimeoutError
from quay.errors import parse_cdp_error


class TestBrowserError:
    """Tests for BrowserError base class."""

    def test_message_only(self):
        """BrowserError renders message only when no context."""
        err = BrowserError("Something went wrong")
        assert str(err) == "Something went wrong"
        assert err.context == {}

    def test_message_with_context(self):
        """BrowserError includes context in string."""
        err = BrowserError("Failed", context={"host": "localhost", "port": 9222})
        s = str(err)
        assert "Failed" in s
        assert "localhost" in s
        assert "9222" in s

    def test_repr(self):
        """BrowserError repr includes context."""
        err = BrowserError("Test", context={"foo": "bar"})
        r = repr(err)
        assert "Test" in r
        assert "foo" in r

    def test_catchable(self):
        """All browser errors catchable as BrowserError."""
        with pytest.raises(BrowserError):
            raise ConnectionError("test")


class TestConnectionError:
    """Tests for ConnectionError."""

    def test_default_message(self):
        """ConnectionError has sensible default."""
        err = ConnectionError()
        assert "not reachable" in str(err)

    def test_context(self):
        """ConnectionError stores host and port."""
        err = ConnectionError("Chrome down", host="192.168.1.1", port=9223)
        assert err.host == "192.168.1.1"
        assert err.port == 9223
        assert "192.168.1.1" in str(err)
        assert "9223" in str(err)

    def test_with_original_error(self):
        """ConnectionError wraps original exception."""
        original = RuntimeError("connection refused")
        err = ConnectionError("Failed", original_error=original)
        assert err.original_error is original
        assert "connection refused" in str(err)


class TestTabError:
    """Tests for TabError."""

    def test_context(self):
        """TabError stores tab_id and operation."""
        err = TabError("Tab gone", tab_id="abc123", operation="click")
        assert err.tab_id == "abc123"
        assert err.operation == "click"
        assert "abc123" in str(err)

    def test_string_output(self):
        """TabError formats cleanly."""
        err = TabError("Not found", tab_id="tab1", operation="navigate")
        s = str(err)
        assert "Not found" in s
        assert "tab1" in s


class TestTimeoutError:
    """Tests for TimeoutError."""

    def test_context(self):
        """TimeoutError stores timeout and operation."""
        err = TimeoutError("Timed out", timeout=30.0, operation="load")
        assert err.timeout == 30.0
        assert err.operation == "load"
        assert "30.0" in str(err)


class TestCDPError:
    """Tests for CDPError."""

    def test_code_mapping(self):
        """CDPError maps known codes to descriptions."""
        err = CDPError("Invalid params", code=-32602)
        assert err.code == -32602
        assert "Invalid params" in str(err)

    def test_unknown_code(self):
        """CDPError handles unknown codes."""
        err = CDPError("Unknown error", code=9999)
        assert err.code == 9999
        # description is stored in context, not as direct attribute
        assert err.context.get("description") is None

    def test_full_context(self):
        """CDPError includes all context."""
        err = CDPError(
            "Error",
            code=-32000,
            method="Page.navigate",
            params={"url": "https://example.com"},
        )
        assert err.method == "Page.navigate"
        assert err.params == {"url": "https://example.com"}
        assert "Page.navigate" in str(err)


class TestParseCDPError:
    """Tests for parse_cdp_error helper."""

    def test_no_error(self):
        """parse_cdp_error returns None when no error key."""
        result = {"id": 1, "result": {}}
        assert parse_cdp_error(result) is None

    def test_parses_error(self):
        """parse_cdp_error creates CDPError from response."""
        response = {
            "id": 1,
            "error": {"code": -32601, "message": "Method not found"},
        }
        err = parse_cdp_error(response, method="Page.navigate")
        assert err is not None
        assert isinstance(err, CDPError)
        assert err.code == -32601
        assert err.method == "Page.navigate"

    def test_without_method(self):
        """parse_cdp_error works without method."""
        response = {"id": 1, "error": {"code": -32600, "message": "Bad request"}}
        err = parse_cdp_error(response)
        assert err is not None
        assert err.code == -32600
