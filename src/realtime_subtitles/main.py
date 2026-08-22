"""
ARIA - Main entry point.

Run with: python -m realtime_subtitles.main
"""

from .events import SubtitleEvent  # noqa: F401 - kept for backward compatibility

__all__ = ["SubtitleEvent"]