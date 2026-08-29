"""
VAD backend protocol and data types for the voice-activity-detection subsystem.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass
class VadSegment:
    """One complete, closed speech segment.

    Attributes:
        start_sample: Sample offset within the audio stream where this segment
            began (relative to the first sample ever fed to the VAD backend).
        samples: Complete utterance audio (float32, mono, 16 kHz).
    """

    start_sample: int
    samples: np.ndarray


@dataclass
class VadFeedResult:
    """Result of one VadGate.feed() call.

    Attributes:
        is_speech_active: Whether the backend considers speech currently in
            progress (an open segment).
        new_active_audio: Delta audio since the last feed() call while the
            current segment has been open, or None if no segment is active.
            Callers should feed this to a streaming ASR backend.
        completed_segments: Segments that were closed by the VAD backend since
            the last feed() call. Usually 0 or 1 element.
    """

    is_speech_active: bool
    new_active_audio: np.ndarray | None
    completed_segments: list[VadSegment]


@runtime_checkable
class VADBackend(Protocol):
    """Frame-level voice-activity-detection engine.

    Callers must feed exactly ``frame_size``-sample windows to
    ``accept_waveform()``.  VadGate handles the alignment so backend
    implementations do not need to buffer partial frames.
    """

    @property
    def frame_size(self) -> int:
        """Size of the audio window (in samples) that this backend expects."""
        ...

    def accept_waveform(self, frame: np.ndarray) -> None:
        """Feed one frame of audio samples to the VAD engine.

        Args:
            frame: Audio samples, shape (frame_size,), float32, mono, 16 kHz.
        """
        ...

    def is_speech_active(self) -> bool:
        """Return True if the VAD engine is currently inside a speech segment."""
        ...

    def current_segment_samples(self) -> np.ndarray:
        """Return cumulative audio samples of the current (open) speech segment.

        Returns an empty array if no segment is active.
        """
        ...

    def pop_ready_segments(self) -> list[VadSegment]:
        """Return all closed segments that are ready and remove them from the
        internal queue.

        The returned VadSegment.samples arrays are independent copies — the
        caller owns them and they are safe to use after further VAD calls.
        """
        ...

    def flush(self) -> None:
        """Force-close the current segment (if any) so that it becomes
        available via pop_ready_segments()."""
        ...

    def reset(self) -> None:
        """Reset the VAD engine to its initial state, discarding all
        accumulated audio and any open or buffered segments."""
        ...
