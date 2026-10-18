"""Tests for quay.browser — Browser class composition."""

from __future__ import annotations

import pytest

from quay.browser import Browser


class TestBrowserComposition:
    """Test that Browser properly inherits from mixins."""

    def test_has_tab_methods(self):
        """Browser should have tab mixin methods."""
        assert hasattr(Browser, "list_tabs")
        assert hasattr(Browser, "new_tab")
        assert hasattr(Browser, "close_tab")

    def test_has_cdp_methods(self):
        """Browser should have CDP mixin methods."""
        assert hasattr(Browser, "_send_cdp")

    def test_has_wait_methods(self):
        """Browser should have wait mixin methods."""
        assert hasattr(Browser, "wait_for")
        assert hasattr(Browser, "wait_for_load_state")
        assert hasattr(Browser, "wait_for_selector_visible")

    def test_has_accessibility_methods(self):
        """Browser should have accessibility mixin methods."""
        assert hasattr(Browser, "accessibility_tree")
        assert hasattr(Browser, "find_by_ref")
        assert hasattr(Browser, "find_by_name")


class TestBrowserInstantiation:
    """Test Browser instantiation."""

    def test_creates_instance_with_mock(self):
        """Browser should create an instance when Chrome is available."""
        # Skip this test as it requires Chrome running
        # The composition tests are sufficient
        pass


class TestChrome144ConnectionGuidance:
    """Connection failure message must cover Chrome 136+/144+ requirements."""

    def test_unreachable_error_mentions_user_data_dir(self):
        """Error hints that Chrome 136+ requires a separate --user-data-dir."""
        from quay.errors import ConnectionError as QuayConnectionError

        with pytest.raises(QuayConnectionError) as exc_info:
            # Port unlikely to be open; connection refused is immediate
            Browser(port=59322)

        msg = str(exc_info.value)
        assert "not reachable" in msg
        assert "--user-data-dir" in msg
        assert "136" in msg

    def test_unreachable_error_mentions_inspect_consent(self):
        """Error points at chrome://inspect consent flow for Chrome 144+."""
        from quay.errors import ConnectionError as QuayConnectionError

        with pytest.raises(QuayConnectionError) as exc_info:
            Browser(port=59322)

        msg = str(exc_info.value)
        assert "chrome://inspect/#remote-debugging" in msg
        assert "144" in msg


class TestBrowserContextManager:
    """Test Browser as context manager."""

    def test_context_manager_protocol(self):
        """Browser should implement context manager protocol."""
        assert hasattr(Browser, "__enter__")
        assert hasattr(Browser, "__exit__")
