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
    target_language: str | None = None  # Target language for translation
    # Dual-buffer translation (replaces legacy translated_text)
    committed_translation: str | None = None
    draft_translation: str | None = None


@dataclass
class TranscriptMessage:
    """A single finalized transcript line for the console history view.

    Emitted once a sentence batch is committed (see `segmenter.py` /
    `TranslationStateManager`). `translation` is None when translation is
    disabled; it is always final text, never a partial/draft value.
    """

    msg_id: int
    timestamp: float
    original: str
    translation: str | None = None
    language: str = ""
