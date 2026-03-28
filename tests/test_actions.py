"""Tests for quay._browser_actions — click, type, key definitions."""
from __future__ import annotations


from quay._browser_actions import _key_to_key_definition, _KEY_MAP


class TestKeyToKeyDefinition:
    def test_regular_character(self):
        """Regular characters should map to their key."""
        result = _key_to_key_definition("a")
        assert result["key"] == "a"
        assert result["text"] == "a"
        assert result["modifiers"] == 0

    def test_enter(self):
        """Enter key should have correct keyCode."""
        result = _key_to_key_definition("Enter")
        assert result["key"] == "Enter"
        assert result["keyCode"] == 13

    def test_space(self):
        """Space should produce actual space character."""
        result = _key_to_key_definition("Space")
        assert result["key"] == "Space"
        assert result["keyCode"] == 32
        assert result["text"] == " "

    def test_tab(self):
        """Tab key should have correct keyCode."""
        result = _key_to_key_definition("Tab")
        assert result["key"] == "Tab"
        assert result["keyCode"] == 9

    def test_escape(self):
        """Escape key should have correct keyCode."""
        result = _key_to_key_definition("Escape")
        assert result["key"] == "Escape"
        assert result["keyCode"] == 27

    def test_arrow_keys(self):
        """Arrow keys should have correct mappings."""
        for direction in ["Up", "Down", "Left", "Right"]:
            result = _key_to_key_definition(f"Arrow{direction}")
            assert result["key"] == f"Arrow{direction}"
            assert "keyCode" in result

    def test_backspace(self):
        """Backspace should have correct keyCode."""
        result = _key_to_key_definition("Backspace")
        assert result["key"] == "Backspace"
        assert result["keyCode"] == 8

    def test_delete(self):
        """Delete key should have correct keyCode."""
        result = _key_to_key_definition("Delete")
        assert result["key"] == "Delete"
        assert result["keyCode"] == 46


class TestKeyMapCompleteness:
    def test_key_map_has_common_keys(self):
        """_KEY_MAP should include all commonly used keys."""
        required_keys = [
            "Enter", "Space", "Tab", "Escape",
            "Backspace", "Delete",
            "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
            "Home", "End", "PageUp", "PageDown"
        ]
        for key in required_keys:
            assert key in _KEY_MAP, f"Missing key: {key}"

    def test_key_map_has_key_code(self):
        """Every entry should have a keyCode for browser compatibility."""
        for key_name, key_def in _KEY_MAP.items():
            assert "keyCode" in key_def, f"{key_name} missing keyCode"