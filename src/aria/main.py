"""
ARIA - Main entry point.

Run with: python -m aria.main
"""

from .events import SubtitleEvent  # noqa: F401 - kept for backward compatibility

__all__ = ["SubtitleEvent"]