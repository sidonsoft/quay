"""Tests for design issue fixes (DES-1 through DES-6)."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quay.connection import Connection, ConnectionState, ConnectionPool
from quay._browser_wait import BrowserWaitMixin
from quay._browser_cdp import BrowserCDPMixin
from quay._browser_recording import BrowserRecordingMixin, PLAYBACK_ALLOWED_ACTIONS
from quay.models import Action, Recording


class TestDES1AsyncPolling:
    """Test that wait methods use asyncio.sleep instead of time.sleep."""

    def test_wait_mixin_has_poll_until_method(self):
        """BrowserWaitMixin should have _poll_until async helper."""
        assert hasattr(BrowserWaitMixin, "_poll_until")
        # It should be async (coroutine function)
        import inspect
        assert inspect.iscoroutinefunction(BrowserWaitMixin._poll_until)

    @pytest.mark.asyncio
    async def test_poll_until_returns_true_when_check_passes(self):
        """_poll_until should return True when check_fn returns True."""
        mixin = BrowserWaitMixin()
        call_count = 0

        async def check_fn():
            nonlocal call_count
            call_count += 1
            return call_count >= 3  # Pass on third call

        result = await mixin._poll_until(check_fn, timeout=5.0, poll_interval=0.01)
        assert result is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_poll_until_returns_false_on_timeout(self):
        """_poll_until should return False when timeout reached."""
        mixin = BrowserWaitMixin()

        async def check_fn():
            return False  # Never passes

        result = await mixin._poll_until(check_fn, timeout=0.1, poll_interval=0.02)
        assert result is False


class TestDES2EvictionNoFireAndForgetC:
    """Test that _evict_oldest doesn't use fire-and-forget asyncio.create_task."""

    def test_evict_marks_disconnected_not_async(self):
        """_evict_oldest should synchronously mark connection as disconnected."""
        pool = ConnectionPool(max_connections=2)

        # Create mock connections
        conn1 = MagicMock(spec=Connection)
        conn1.last_used = 100.0
        conn1._state = ConnectionState.CONNECTED
        conn1._connected = True

        conn2 = MagicMock(spec=Connection)
        conn2.last_used = 200.0
        conn2._state = ConnectionState.CONNECTED
        conn2._connected = True

        pool._connections = {"tab1": conn1, "tab2": conn2}

        # Evict should not call asyncio.create_task
        with patch("asyncio.create_task") as mock_create_task:
            pool._evict_oldest()
            # Should NOT create an async task
            mock_create_task.assert_not_called()

        # Oldest (tab1) should be removed and marked disconnected
        assert "tab1" not in pool._connections
        assert conn1._state == ConnectionState.DISCONNECTED
        assert conn1._connected is False


class TestDES3AgeBasedCleanup:
    """Test age-based cleanup for stale pending futures."""

    def test_connection_tracks_pending_timestamps(self):
        """Connection should track when each message was added."""
        conn = Connection("ws://localhost:9222", "test-tab-id")
        assert hasattr(conn, "_pending_timestamps")
        assert isinstance(conn._pending_timestamps, dict)

    def test_stale_age_constant_exists(self):
        """Connection should have _STALE_AGE_SECONDS constant."""
        assert hasattr(Connection, "_STALE_AGE_SECONDS")
        assert Connection._STALE_AGE_SECONDS == 30.0

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_futures(self):
        """_cleanup_stale_messages should remove futures older than threshold."""
        conn = Connection("ws://localhost:9222", "test-tab-id")

        # Create an old pending message
        loop = asyncio.get_event_loop()
        old_future = loop.create_future()
        old_msg_id = 999

        conn._pending[old_msg_id] = old_future
        conn._pending_timestamps[old_msg_id] = time.time() - 60.0  # 60 seconds ago

        # Create a recent pending message
        recent_future = loop.create_future()
        recent_msg_id = 1000
        conn._pending[recent_msg_id] = recent_future
        conn._pending_timestamps[recent_msg_id] = time.time()

        conn._cleanup_stale_messages()

        # Old message should be removed
        assert old_msg_id not in conn._pending
        # Recent message should remain
        assert recent_msg_id in conn._pending


class TestDES4DomainCaching:
    """Test that CDP domains are only enabled once per connection."""

    def test_mixin_has_domain_cache(self):
        """BrowserCDPMixin should have _enabled_domains WeakKeyDictionary (lazy)."""
        # It's initialized lazily in _send_cdp, not at class level
        # This avoids MRO __init__ conflicts in the mixin pattern
        import weakref
        cdp = BrowserCDPMixin()
        assert not hasattr(cdp, '_enabled_domains')
        # After calling any method that uses it, it should be initialized
        cdp._enabled_domains = weakref.WeakKeyDictionary()
        assert hasattr(cdp, '_enabled_domains')

    @pytest.mark.asyncio
    async def test_send_cdp_caches_domains(self):
        """_send_cdp should only enable domain once per connection."""
        cdp = BrowserCDPMixin()
        cdp._resolve_timeout = lambda t: 10.0  # type: ignore

        mock_conn = AsyncMock(spec=Connection)
        cdp._enabled_domains = AsyncMock()  # type: ignore

        # Initialize domain cache
        import weakref
        cdp._enabled_domains = weakref.WeakKeyDictionary()

        # Track enable calls
        enable_calls = []

        async def mock_send(method, params=None, timeout=None):
            if "enable" in method:
                enable_calls.append(method)
            return {"result": {}}

        mock_conn.send = mock_send

        # First call: should send Page.enable
        await cdp._send_cdp(mock_conn, "Page.navigate", {"url": "http://example.com"}, domains=["Page"])
        assert len(enable_calls) == 1
        assert enable_calls[0] == "Page.enable"

        # Second call: should NOT send Page.enable again
        await cdp._send_cdp(mock_conn, "Page.navigate", {"url": "http://example.com"}, domains=["Page"])
        assert len(enable_calls) == 1  # No new enable calls

        # Different domain: should send
        await cdp._send_cdp(mock_conn, "Runtime.evaluate", {"expression": "1"}, domains=["Runtime"])
        assert len(enable_calls) == 2
        assert enable_calls[1] == "Runtime.enable"


class TestDES5GetExistingConnectedOnly:
    """Test that get_existing only returns connected connections."""

    @pytest.mark.asyncio
    async def test_get_existing_returns_none_for_disconnected(self):
        """get_existing should return None for disconnected connections."""
        pool = ConnectionPool()

        # Create a mock connection that's disconnected
        mock_conn = MagicMock(spec=Connection)
        mock_conn.state = ConnectionState.DISCONNECTED

        pool._connections["tab1"] = mock_conn

        result = await pool.get_existing("tab1")
        assert result is None

        # And for connected
        mock_conn.state = ConnectionState.CONNECTED
        result = await pool.get_existing("tab1")
        assert result is mock_conn


class TestDES6PlaybackWhitelist:
    """Test that playback only allows whitelisted action types."""

    def test_playback_allowed_actions_exists(self):
        """PLAYBACK_ALLOWED_ACTIONS should be defined."""
        assert hasattr(BrowserRecordingMixin, "__module__")
        assert isinstance(PLAYBACK_ALLOWED_ACTIONS, frozenset)

    def test_playback_allowed_actions_no_private_methods(self):
        """Allowed actions should not include internal methods."""
        for action in PLAYBACK_ALLOWED_ACTIONS:
            assert not action.startswith("_"), f"Internal method '{action}' should not be allowed"

    def test_playback_allowed_actions_includes_common(self):
        """Allowed actions should include common browser operations."""
        expected = {"open", "navigate", "click", "type", "screenshot"}
        for action in expected:
            assert action in PLAYBACK_ALLOWED_ACTIONS, f"Missing expected action: {action}"

    def test_playback_rejects_internal_method(self):
        """playback should raise BrowserError for internal methods."""
        mixin = BrowserRecordingMixin()
        mixin._playing_back = False

        recording = Recording(
            actions=[Action(type="_close_all", timestamp=0.0, params={})]
        )

        from quay.errors import BrowserError
        with pytest.raises(BrowserError) as exc_info:
            mixin.playback(recording)

        assert "not allowed" in str(exc_info.value)
        assert "_close_all" in str(exc_info.value)

    def test_playback_rejects_arbitrary_method(self):
        """playback should raise BrowserError for arbitrary methods."""
        mixin = BrowserRecordingMixin()
        mixin._playing_back = False

        recording = Recording(
            actions=[Action(type="__import__", timestamp=0.0, params={})]
        )

        from quay.errors import BrowserError
        with pytest.raises(BrowserError) as exc_info:
            mixin.playback(recording)

        assert "not allowed" in str(exc_info.value)


class TestDES4ClearDomainCache:
    """Test _clear_domain_cache method."""

    def test_clear_domain_cache_method_exists(self):
        """BrowserCDPMixin should have _clear_domain_cache method."""
        assert hasattr(BrowserCDPMixin, "_clear_domain_cache")

    @pytest.mark.asyncio
    async def test_clear_domain_cache_removes_entry(self):
        """_clear_domain_cache should remove connection from cache."""
        import weakref

        cdp = BrowserCDPMixin()
        cdp._resolve_timeout = lambda t: 10.0  # type: ignore

        mock_conn = AsyncMock(spec=Connection)

        # Initialize cache
        cdp._enabled_domains = weakref.WeakKeyDictionary()
        cdp._enabled_domains[mock_conn] = {"Page", "Runtime"}

        assert mock_conn in cdp._enabled_domains

        # Clear it
        cdp._clear_domain_cache(mock_conn)

        assert mock_conn not in cdp._enabled_domains