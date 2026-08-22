"""
Shared event types used across pipeline modules.

Extracted from pipeline.py to allow removal of the Precise/Faster-Whisper pipeline
while keeping the SubtitleEvent dataclass available to other pipelines.
"""

from dataclasses import dataclass


@dataclass
class SubtitleEvent:
    """A subtitle event with text and metadata."""
    text: str
    language: str
    confidence: float
    timestamp: float
    is_partial: bool = False
    translated_text: str | None = None  # Translation (if enabled)
    target_language: str | None = None  # Target language for translation
    # Dual-buffer support
    committed_translation: str | None = None
    draft_translation: str | None = None