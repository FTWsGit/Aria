"""
LiveCaptions subsystem: reads Windows 11's built-in Live Captions window
via UI Automation instead of doing our own audio capture + ASR.

Peer to `audio/` + `transcription/` combined, not a peer of `transcription/`
alone: Windows does the capture and recognition invisibly, so this package
covers both jobs (`controller.py` launches/positions the window, `monitor.py`
reads text out of it) plus its own orchestration (`pipeline.py`).
"""

from .controller import LiveCaptionsController, is_livecaptions_available, is_windows_11
from .monitor import CaptionEvent, LiveCaptionsMonitor
from .pipeline import LiveCaptionsPipeline

__all__ = [
    "LiveCaptionsPipeline",
    "LiveCaptionsController",
    "is_livecaptions_available",
    "is_windows_11",
    "CaptionEvent",
    "LiveCaptionsMonitor",
]
