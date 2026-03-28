"""Tests for quay._browser_navigation — navigation methods."""
from __future__ import annotations


from quay._browser_navigation import BrowserNavigationMixin


class TestNavigationMixin:
    """Test navigation methods."""
    
    def test_navigate_method_exists(self):
        """navigate should be defined."""
        assert hasattr(BrowserNavigationMixin, 'navigate')
    
    def test_goto_method_exists(self):
        """goto should be defined."""
        assert hasattr(BrowserNavigationMixin, 'goto')


class TestNavigationIntegration:
    """Test navigation calls properly."""
    
    def test_navigate_receives_tab(self):
        """navigate should accept tab parameter."""
        import inspect
        sig = inspect.signature(BrowserNavigationMixin.navigate)
        assert 'tab' in sig.parameters


class TestTabsMixin:
    """Test tab operations from _browser_tabs."""
    
    def test_list_tabs_exists(self):
        """list_tabs should be defined."""
        from quay._browser_tabs import BrowserTabsMixin
        assert hasattr(BrowserTabsMixin, 'list_tabs')
    
    def test_new_tab_exists(self):
        """new_tab should be defined."""
        from quay._browser_tabs import BrowserTabsMixin
        assert hasattr(BrowserTabsMixin, 'new_tab')
    
    def test_close_tab_exists(self):
        """close_tab should be defined."""
        from quay._browser_tabs import BrowserTabsMixin
        assert hasattr(BrowserTabsMixin, 'close_tab')
    
    def test_activate_tab_exists(self):
        """activate_tab should be defined."""
        from quay._browser_tabs import BrowserTabsMixin
        assert hasattr(BrowserTabsMixin, 'activate_tab')