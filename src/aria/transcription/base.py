"""
ASR backend protocols for streaming and chunked transcription.
"""

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class StreamingASR(Protocol):
    """True streaming ASR: feed audio frame-by-frame, get incremental text."""

    def process_audio(self, audio: np.ndarray) -> str: ...
    def reset(self) -> None: ...
    def get_final_result(self) -> str: ...


@runtime_checkable
class ChunkedASR(Protocol):
    """Chunked ASR: accumulate a segment, return full text at once."""

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str: ...
