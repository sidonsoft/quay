from __future__ import annotations

import datetime
import json
import logging
import os
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from ._version import __version__
from .errors import BrowserError
from .models import Action, Recording

logger = logging.getLogger(__name__)


class BrowserRecordingMixin:
    """Session recording and playback for Browser.
    
    Requires: BrowserCoreMixin
    """

    def start_recording(self: "BrowserRecordingMixin", path: str | None = None) -> Recording:
        self._recording = Recording(path=path, quay_version=__version__, recorded_at=datetime.datetime.now().isoformat(), start_time=time.time())
        return self._recording

    def stop_recording(self: "BrowserRecordingMixin") -> str:
        if not self._recording:
            raise ValueError("No recording in progress")
        self._recording.end_time = time.time()
        recording = self._recording
        self._recording = None
        return recording.save()

    def pause_recording(self: "BrowserRecordingMixin") -> None:
        if self._recording:
            self._recording.paused = True

    def resume_recording(self: "BrowserRecordingMixin") -> None:
        if self._recording:
            self._recording.paused = False

    def get_recording(self: "BrowserRecordingMixin") -> Recording | None:
        return self._recording

    def _record_action(self: "BrowserRecordingMixin", action_type: str, **params) -> None:
        if not self._recording or self._recording.paused or self._playing_back or self._record_depth.get() > 0:
            return
        if self._recording.start_time is None:
            return
        self._recording.actions.append(Action(type=action_type, timestamp=time.time() - self._recording.start_time, params=params))

    def playback(self: "BrowserRecordingMixin", recording: Recording | str, speed: float = 1.0, verify: bool = False) -> bool:
        if isinstance(recording, str):
            if not os.path.exists(recording):
                raise FileNotFoundError(f"Recording file not found: {recording}")
            with open(recording) as f:
                recording = Recording.from_dict(json.load(f))
        if not isinstance(recording, Recording):
            raise TypeError("Expected Recording object or JSON file path")
        self._playing_back = True
        try:
            last_ts = 0.0
            for action in recording.actions:
                delay = (action.timestamp - last_ts) / speed
                if delay > 0:
                    time.sleep(delay)
                last_ts = action.timestamp
                result = getattr(self, action.type)(**action.params)
                if verify and result is False:
                    raise BrowserError(f"Action '{action.type}' failed during playback")
            return True
        finally:
            self._playing_back = False