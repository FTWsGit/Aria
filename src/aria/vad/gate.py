"""
Backend-agnostic VAD gate: frame alignment, delta tracking, and lifecycle.
"""

import numpy as np

from .base import VADBackend, VadFeedResult, VadSegment


class VadGate:
    """Backend-agnostic audio segmentation coordinator.

    Responsibilities:
        - Frame alignment: buffers leftover samples across feed() calls so
          the backend always receives complete frames.
        - Delta tracking: slices only the new tail of the cumulative
          current-segment buffer so that callers never re-feed already-decoded
          audio into a streaming ASR backend.
    """

    def __init__(self, backend: VADBackend):
        self._backend = backend
        self._leftover = np.zeros(0, dtype=np.float32)
        self._delivered_in_segment = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def feed(self, audio: np.ndarray) -> VadFeedResult:
        """Feed an arbitrary-sized audio chunk into the VAD pipeline.

        Args:
            audio: float32, mono, 16 kHz samples. Size does not need to be a
                multiple of the backend's frame_size.

        Returns:
            VadFeedResult with the delta of new active audio and any completed
            segments.
        """
        buf = np.concatenate([self._leftover, audio]) if len(self._leftover) else audio
        n = self._backend.frame_size
        usable = (len(buf) // n) * n
        frames, self._leftover = buf[:usable], buf[usable:].copy()

        for i in range(0, usable, n):
            self._backend.accept_waveform(frames[i : i + n])

        completed = self._backend.pop_ready_segments()
        is_active = self._backend.is_speech_active()

        # Reset delivered counter when a segment ends (including forced
        # splits that produce a completed segment while speech is still
        # active, so the next read starts from sample 0 of the new segment).
        if completed or not is_active:
            self._delivered_in_segment = 0

        new_audio = None
        if is_active:
            current = self._backend.current_segment_samples()
            new_audio = current[self._delivered_in_segment :]
            self._delivered_in_segment += len(new_audio)

        return VadFeedResult(
            is_speech_active=is_active,
            new_active_audio=new_audio,
            completed_segments=completed,
        )

    def flush(self) -> VadSegment | None:
        """Force-close the current utterance and return its segment.

        Call this on pipeline stop() so an in-progress utterance is not lost.

        Returns:
            The last completed segment, or None if no segment was produced.
        """
        self._backend.flush()
        segs = self._backend.pop_ready_segments()
        self._delivered_in_segment = 0
        return segs[-1] if segs else None

    def reset(self) -> None:
        """Reset the gate and its backend to initial state."""
        self._backend.reset()
        self._leftover = np.zeros(0, dtype=np.float32)
        self._delivered_in_segment = 0
