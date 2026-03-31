"""Tests for quay._browser_recording — session recording and playback."""

from __future__ import annotations

import os
import tempfile

from quay.models import Action
from quay.models import Recording


class TestActionModel:
    """Test Action model."""

    def test_create_action(self):
        """Action should be created with correct fields."""
        action = Action(type="click", timestamp=1.5, params={"x": 10, "y": 20})
        assert action.type == "click"
        assert action.timestamp == 1.5
        assert action.params == {"x": 10, "y": 20}

    def test_action_to_dict(self):
        """Action should convert to dict."""
        action = Action(type="type", timestamp=2.0, params={"text": "hello"})
        d = action.to_dict()
        assert d["type"] == "type"
        assert d["timestamp"] == 2.0

    def test_action_from_dict(self):
        """Action should be created from dict."""
        d = {"type": "screenshot", "timestamp": 3.0, "path": "/tmp/shot.png"}
        action = Action.from_dict(d)
        assert action.type == "screenshot"
        # params contains remaining fields after type/timestamp
        assert action.params["path"] == "/tmp/shot.png"


class TestRecordingModel:
    """Test Recording model methods."""

    def test_create_empty(self):
        """Recording should start empty."""
        rec = Recording()
        assert len(rec.actions) == 0

    def test_add_action_manual(self):
        """Recording should allow adding actions."""
        rec = Recording()
        action = Action(type="click", timestamp=1.0, params={"x": 10})
        rec.actions.append(action)
        assert len(rec.actions) == 1
        assert rec.actions[0].type == "click"

    def test_to_dict(self):
        """Recording should serialize to dict."""
        rec = Recording()
        rec.start_time = 0.0
        rec.actions.append(
            Action(type="click", timestamp=1.0, params={"x": 10, "y": 20})
        )

        d = rec.to_dict()
        assert "actions" in d
        assert len(d["actions"]) == 1
        assert d["version"] == "1.0"

    def test_from_dict(self):
        """Recording should deserialize from dict."""
        json_data = {
            "version": "1.0",
            "actions": [{"type": "type", "timestamp": 1.0, "text": "hello"}],
        }

        rec = Recording.from_dict(json_data)
        assert rec.version == "1.0"
        assert len(rec.actions) == 1
        assert rec.actions[0].type == "type"

    def test_save_and_load(self):
        """Recording should save and load from file."""
        rec = Recording()
        rec.start_time = 0.0
        rec.actions.append(
            Action(
                type="navigate", timestamp=0.5, params={"url": "https://example.com"}
            )
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filename = f.name

        try:
            rec.save(filename)

            loaded = Recording.from_file(filename)
            assert len(loaded.actions) == 1
            assert loaded.actions[0].type == "navigate"
        finally:
            os.unlink(filename)
