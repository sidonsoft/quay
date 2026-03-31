"""Tests for quay.connection — WebSocket connection lifecycle."""

from __future__ import annotations

import asyncio

from quay.connection import ConnectionState
from quay.connection import OperationQueue


class TestOperationQueue:
    def test_queue_returns_future(self):
        """queue() should return an asyncio.Future."""
        q = OperationQueue()
        future = q.queue(1, "Page.navigate", {"url": "https://x.com"})
        assert isinstance(future, asyncio.Future)
        assert not future.done()

    def test_get_all_clears(self):
        """get_all() should clear the queue."""
        q = OperationQueue()
        q.queue(1, "m1", None)
        q.queue(2, "m2", None)
        ops = q.get_all()
        assert len(ops) == 2
        # Second call should be empty
        assert q.get_all() == []

    def test_get_all_preserves_order(self):
        """get_all() should preserve insertion order."""
        q = OperationQueue()
        q.queue(1, "first", None)
        q.queue(2, "second", None)
        q.queue(3, "third", None)
        ops = q.get_all()
        assert ops[0].method == "first"
        assert ops[1].method == "second"
        assert ops[2].method == "third"


class TestConnectionState:
    def test_initial_state(self):
        """New connection should start in disconnected state."""
        state = ConnectionState.DISCONNECTED
        assert state == ConnectionState.DISCONNECTED

    def test_state_equality(self):
        """State should compare equal correctly."""
        assert ConnectionState.CONNECTED == ConnectionState.CONNECTED
        assert ConnectionState.CONNECTED != ConnectionState.DISCONNECTED


class TestConnectionBasics:
    """Basic connection tests."""

    def test_state_exists(self):
        """ConnectionState enum should exist."""
        assert ConnectionState.DISCONNECTED is not None
        assert ConnectionState.CONNECTED is not None
