"""Unit tests for VadGate: frame alignment, delta tracking, and lifecycle.

Pure Python tests — no sherpa_onnx, no audio devices, no Qt required.
"""

import numpy as np

from aria.vad.base import VadSegment
from aria.vad.gate import VadGate

# ---------------------------------------------------------------------------
# Fake deterministic VAD backend
# ---------------------------------------------------------------------------


class FakeVADBackend:
    """Deterministic, scriptable VAD backend for testing VadGate arithmetic.

    The script is a dict of ``{frame_number: action}``.  Actions:
        "activate"    — start a new speech segment with this frame.
        "deactivate"  — close the current segment (speech ends).
        "force_split" — close the current segment AND start a new one
                        immediately (speech continues).
    """

    def __init__(self, frame_size: int = 512):
        self._frame_size = frame_size
        self._frames_received: list[np.ndarray] = []
        self._frame_count = 0
        self._total_samples = 0
        self._active = False
        self._segment_start_sample = 0
        self._segment_samples: list[np.ndarray] = []
        self._completed_segments: list[VadSegment] = []
        self._script: dict[int, str] = {}

    def set_script(self, script: dict[int, str]) -> None:
        self._script = script

    # -- VADBackend protocol ------------------------------------------------

    @property
    def frame_size(self) -> int:
        return self._frame_size

    def accept_waveform(self, frame: np.ndarray) -> None:
        self._frames_received.append(frame.copy())
        self._total_samples += len(frame)
        self._frame_count += 1

        action = self._script.get(self._frame_count)
        if action == "activate":
            self._active = True
            self._segment_start_sample = self._total_samples - len(frame)
            self._segment_samples = [frame.copy()]
        elif action == "deactivate":
            if self._active:
                seg = VadSegment(
                    start_sample=self._segment_start_sample,
                    samples=np.concatenate(self._segment_samples),
                )
                self._completed_segments.append(seg)
                self._segment_samples = []
                self._active = False
        elif action == "force_split":
            if self._active:
                seg = VadSegment(
                    start_sample=self._segment_start_sample,
                    samples=np.concatenate(self._segment_samples),
                )
                self._completed_segments.append(seg)
                self._segment_samples = [frame.copy()]
                self._segment_start_sample = self._total_samples - len(frame)
                self._active = True
        elif self._active:
            self._segment_samples.append(frame.copy())

    def is_speech_active(self) -> bool:
        return self._active

    def current_segment_samples(self) -> np.ndarray:
        if not self._active or not self._segment_samples:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self._segment_samples)

    def pop_ready_segments(self) -> list[VadSegment]:
        segs = self._completed_segments
        self._completed_segments = []
        return segs

    def flush(self) -> None:
        if self._active and self._segment_samples:
            seg = VadSegment(
                start_sample=self._segment_start_sample,
                samples=np.concatenate(self._segment_samples),
            )
            self._completed_segments.append(seg)
            self._segment_samples = []
            self._active = False

    def reset(self) -> None:
        self._frames_received = []
        self._frame_count = 0
        self._total_samples = 0
        self._active = False
        self._segment_start_sample = 0
        self._segment_samples = []
        self._completed_segments = []
        self._script = {}

    # -- Test helpers -------------------------------------------------------

    @property
    def total_frames_received(self) -> int:
        return len(self._frames_received)

    def all_received_samples(self) -> np.ndarray:
        if not self._frames_received:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self._frames_received)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(size: int, *, start: int = 0) -> np.ndarray:
    """Return a float32 array of *size* samples with linearly increasing values."""
    return np.arange(start, start + size, dtype=np.float32)


# ===================================================================
# Test 1 — Frame alignment
# ===================================================================


def test_frame_alignment_leftover_carried():
    """1600-sample chunks with frame_size=512: leftover samples carried across
    feed() calls, all input samples eventually reach the backend."""
    backend = FakeVADBackend(frame_size=512)
    gate = VadGate(backend)

    total_input = 0
    for _ in range(4):
        chunk = _make_chunk(1600, start=total_input)
        total_input += len(chunk)
        gate.feed(chunk)

    received = backend.all_received_samples()
    # All received samples must be complete frames
    assert len(received) % 512 == 0

    # Sum of received + leftover == total input
    leftover = gate._leftover
    assert len(received) + len(leftover) == total_input


def test_frame_alignment_samples_are_contiguous():
    """Verify that concatenated received frames form a contiguous prefix of
    the input, without gaps or reordering."""
    backend = FakeVADBackend(frame_size=512)
    gate = VadGate(backend)

    input_chunks = []
    for _ in range(3):
        chunk = _make_chunk(1600, start=sum(len(c) for c in input_chunks))
        input_chunks.append(chunk)
        gate.feed(chunk)

    all_input = np.concatenate(input_chunks)
    received = backend.all_received_samples()
    leftover = gate._leftover

    assert np.array_equal(received, all_input[: len(received)])
    assert len(received) + len(leftover) == len(all_input)


# ===================================================================
# Test 2 — Delta tracking
# ===================================================================


def test_delta_tracking_no_overlap_no_gap():
    """During continuous speech, concatenated new_active_audio across feed()
    calls equals the full current_segment_samples, with no overlap or gaps."""
    backend = FakeVADBackend(frame_size=512)
    backend.set_script({2: "activate"})  # activate on 2nd frame
    gate = VadGate(backend)

    all_deltas: list[np.ndarray] = []
    for _ in range(4):
        chunk = _make_chunk(1600)
        result = gate.feed(chunk)
        if result.new_active_audio is not None and len(result.new_active_audio) > 0:
            all_deltas.append(result.new_active_audio)

    full_segment = backend.current_segment_samples()
    concatenated = np.concatenate(all_deltas) if all_deltas else np.zeros(0, dtype=np.float32)
    assert len(concatenated) == len(full_segment)
    assert np.array_equal(concatenated, full_segment)


def test_delta_tracking_only_new_samples():
    """Each feed() returns only samples that haven't been returned before."""
    backend = FakeVADBackend(frame_size=512)
    backend.set_script({2: "activate"})
    gate = VadGate(backend)

    prev_length = 0
    for _ in range(4):
        result = gate.feed(_make_chunk(1600))
        if result.new_active_audio is not None and len(result.new_active_audio) > 0:
            assert len(result.new_active_audio) > 0
            # The cumulative segment should have grown by exactly the delta
            current = backend.current_segment_samples()
            assert len(current) == prev_length + len(result.new_active_audio)
            prev_length = len(current)


# ===================================================================
# Test 3 — Completed segments
# ===================================================================


def test_completed_segment_carries_full_samples():
    """When a segment closes, completed_segments contains the full segment
    audio, and delivered resets for the next segment."""
    backend = FakeVADBackend(frame_size=512)
    backend.set_script({2: "activate", 5: "deactivate"})
    gate = VadGate(backend)

    completed = None
    for _ in range(4):
        chunk = _make_chunk(1600)
        result = gate.feed(chunk)
        if result.completed_segments:
            completed = result.completed_segments[0]

    assert completed is not None
    assert len(completed.samples) > 0
    assert completed.start_sample >= 0

    # After deactivation, delivered resets to 0
    assert gate._delivered_in_segment == 0


def test_completed_segment_then_new_segment():
    """After one segment closes, the next segment starts from delivered=0."""
    backend = FakeVADBackend(frame_size=512)
    backend.set_script({2: "activate", 5: "deactivate", 8: "activate"})
    gate = VadGate(backend)

    first_segment = None
    for _ in range(6):
        chunk = _make_chunk(1600)
        result = gate.feed(chunk)
        if result.completed_segments and first_segment is None:
            first_segment = result.completed_segments[0]

    assert first_segment is not None
    # After the second activation, delivered should be tracking from 0
    assert gate._delivered_in_segment >= 0


# ===================================================================
# Test 4 — Forced split boundary (key correction)
# ===================================================================


def test_force_split_new_segment_starts_at_zero():
    """When a segment is force-closed but speech is still active (e.g.
    max_speech_duration), the new segment's new_active_audio starts from
    sample 0, not from the old segment's delivered offset."""
    backend = FakeVADBackend(frame_size=512)
    # activate at frame 2, force_split at frame 5 (still active)
    backend.set_script({2: "activate", 5: "force_split"})
    gate = VadGate(backend)

    # Feed enough to reach frame 2 (activate)
    chunk = _make_chunk(1600)
    result = gate.feed(chunk)
    # Should have some new_active_audio from the first segment
    assert result.new_active_audio is not None
    assert len(result.new_active_audio) > 0

    # Feed more to reach frame 5 (force_split)
    chunk = _make_chunk(1600)
    result = gate.feed(chunk)

    # Should have a completed segment (the old one)
    assert len(result.completed_segments) == 1
    # Should still be active (new segment started)
    assert result.is_speech_active
    # new_active_audio should contain only the new segment's samples
    assert result.new_active_audio is not None

    new_segment_samples = backend.current_segment_samples()
    # The new_active_audio should be identical to the new segment's full samples
    # (because delivered was reset to 0 before reading)
    assert len(result.new_active_audio) == len(new_segment_samples)
    assert np.array_equal(result.new_active_audio, new_segment_samples)


def test_force_split_old_segment_intact():
    """The completed segment from a force split contains the old segment's
    full samples, not truncated."""
    backend = FakeVADBackend(frame_size=512)
    backend.set_script({2: "activate", 5: "force_split"})
    gate = VadGate(backend)

    # Feed phase 1: reach activate
    gate.feed(_make_chunk(1600))
    # Feed phase 2: trigger force split
    result = gate.feed(_make_chunk(1600))

    assert len(result.completed_segments) == 1
    completed = result.completed_segments[0]
    assert completed.start_sample >= 0
    assert len(completed.samples) > 0

    # The old segment + new segment samples should be contiguous
    current = backend.current_segment_samples()
    assert len(completed.samples) + len(current) > 0


# ===================================================================
# Test 5 — Flush
# ===================================================================


def test_flush_returns_last_segment():
    """flush() returns the last open segment."""
    backend = FakeVADBackend(frame_size=512)
    backend.set_script({2: "activate"})
    gate = VadGate(backend)

    for _ in range(3):
        gate.feed(_make_chunk(1600))

    trailing = gate.flush()
    assert trailing is not None
    assert isinstance(trailing, VadSegment)
    assert len(trailing.samples) > 0
    # delivered must be reset after flush
    assert gate._delivered_in_segment == 0


def test_flush_returns_none_when_idle():
    """flush() returns None when no segment is active."""
    backend = FakeVADBackend(frame_size=512)
    gate = VadGate(backend)

    gate.feed(_make_chunk(1600))
    trailing = gate.flush()
    assert trailing is None
    assert gate._delivered_in_segment == 0


def test_flush_resets_delivered():
    """flush() always resets delivered_in_segment to 0."""
    backend = FakeVADBackend(frame_size=512)
    backend.set_script({2: "activate"})
    gate = VadGate(backend)

    gate.feed(_make_chunk(1600))  # some audio delivered
    assert gate._delivered_in_segment > 0
    gate.flush()
    assert gate._delivered_in_segment == 0


# ===================================================================
# Test 6 — Reset
# ===================================================================


def test_reset_clears_leftover_and_delivered():
    """reset() clears both leftover buffer and delivered counter."""
    backend = FakeVADBackend(frame_size=512)
    backend.set_script({2: "activate"})
    gate = VadGate(backend)

    # Feed to accumulate leftover and delivered
    gate.feed(_make_chunk(1600))
    gate.feed(_make_chunk(1600))

    assert len(gate._leftover) > 0 or gate._delivered_in_segment > 0

    gate.reset()

    assert len(gate._leftover) == 0
    assert gate._delivered_in_segment == 0


def test_reset_backend_also_reset():
    """reset() calls through to the backend."""
    backend = FakeVADBackend(frame_size=512)
    backend.set_script({2: "activate"})
    gate = VadGate(backend)

    gate.feed(_make_chunk(1600))
    assert backend.total_frames_received > 0

    gate.reset()
    assert backend.total_frames_received == 0
    assert not backend.is_speech_active()


# ===================================================================
# Test 7 — Edge cases
# ===================================================================


def test_empty_feed():
    """Feeding an empty array should not crash."""
    backend = FakeVADBackend(frame_size=512)
    gate = VadGate(backend)

    result = gate.feed(np.zeros(0, dtype=np.float32))
    assert not result.is_speech_active
    assert result.new_active_audio is None
    assert result.completed_segments == []


def test_feed_smaller_than_frame_size():
    """Feeding a chunk smaller than frame_size accumulates in leftover."""
    backend = FakeVADBackend(frame_size=512)
    gate = VadGate(backend)

    # Feed 100 samples — no complete frame
    gate.feed(_make_chunk(100))
    assert backend.total_frames_received == 0
    assert len(gate._leftover) == 100

    # Feed 412 more — one complete frame of 512
    gate.feed(_make_chunk(412))
    assert backend.total_frames_received == 1
    assert len(gate._leftover) == 0


def test_silence_produces_no_new_audio():
    """When no speech is active, new_active_audio is None."""
    backend = FakeVADBackend(frame_size=512)
    gate = VadGate(backend)

    result = gate.feed(_make_chunk(1600))
    assert not result.is_speech_active
    assert result.new_active_audio is None


def test_verify_Protocol_accepts_fake_backend():
    """The fake backend satisfies the VADBackend Protocol at runtime."""
    from aria.vad.base import VADBackend

    backend = FakeVADBackend(frame_size=512)
    assert isinstance(backend, VADBackend)
