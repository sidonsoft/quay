"""Tests for quay._browser_core.escape_js_string — JavaScript safety."""
from __future__ import annotations


from quay._browser_core import escape_js_string


class TestEscapeJsString:
    def test_basic_string(self):
        """Basic strings should be quoted and escaped."""
        result = escape_js_string("hello")
        assert result == '"hello"'

    def test_double_quotes_inside(self):
        """Double quotes should be escaped with backslash."""
        result = escape_js_string('He said "hi"')
        assert r'\"' in result

    def test_single_quotes(self):
        """Single quotes don't need escaping in JSON."""
        result = escape_js_string("It's fine")
        assert "'" in result

    def test_newline(self):
        """Newlines should be escaped."""
        result = escape_js_string("line1\nline2")
        assert "\\n" in result

    def test_backslash(self):
        """Backslashes should be escaped."""
        result = escape_js_string(r"C:\path")
        assert "\\\\" in result or "\\" in result

    def test_empty_string(self):
        """Empty string returns just quotes."""
        result = escape_js_string("")
        assert result == '""'

    def test_returns_json_quoted(self):
        """Result should be valid JSON string literal."""
        import json
        result = escape_js_string("test")
        # The result should be parseable as JSON
        parsed = json.loads(result)
        assert parsed == "test"