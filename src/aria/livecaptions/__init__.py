"""
Windows LiveCaptions integration module.

Provides integration with Windows 11's built-in Live Captions feature
using UI Automation to capture subtitle text for translation and display.
"""

from .controller import LiveCaptionsController
from .monitor import CaptionEvent, LiveCaptionsMonitor
from .pipeline import LiveCaptionsPipeline

__all__ = [
    "CaptionEvent",
    "LiveCaptionsController",
    "LiveCaptionsMonitor",
    "LiveCaptionsPipeline",
]
