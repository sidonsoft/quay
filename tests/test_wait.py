"""Tests for quay._browser_wait — wait conditions."""
from __future__ import annotations


from quay._browser_core import escape_js_string


class TestEscapeJsString:
    """Test that escape_js_string produces safe JavaScript strings."""
    
    def test_returns_json_quoted(self):
        """escape_js_string should return JSON-quoted string."""
        result = escape_js_string("hello")
        assert result == '"hello"'
    
    def test_double_quotes_escaped(self):
        """Double quotes should be escaped."""
        result = escape_js_string('He said "hi"')
        assert r'\"' in result
    
    def test_injection_prevention(self):
        """Potentially malicious strings should be safely quoted."""
        text = "'); alert('xss"
        result = escape_js_string(text)
        # Should be safely quoted with double quotes
        assert result.startswith('"')
        assert result.endswith('"')
        # Single quotes are preserved inside the JSON string
        assert "'" in result


class TestWaitMethodsExist:
    """Test that wait methods are defined."""
    
    def test_wait_for_load_state_exists(self):
        """wait_for_load_state should be defined."""
        from quay._browser_wait import BrowserWaitMixin
        assert hasattr(BrowserWaitMixin, 'wait_for_load_state')

    def test_wait_for_exists(self):
        """wait_for should be defined."""
        from quay._browser_wait import BrowserWaitMixin
        assert hasattr(BrowserWaitMixin, 'wait_for')

    def test_wait_for_selector_visible_exists(self):
        """wait_for_selector_visible should be defined."""
        from quay._browser_wait import BrowserWaitMixin
        assert hasattr(BrowserWaitMixin, 'wait_for_selector_visible')
    
    def test_wait_for_selector_hidden_exists(self):
        """wait_for_selector_hidden should be defined."""
        from quay._browser_wait import BrowserWaitMixin
        assert hasattr(BrowserWaitMixin, 'wait_for_selector_hidden')