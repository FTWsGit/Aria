"""
Sherpa-ONNX VoiceActivityDetector backend implementing the VADBackend protocol.
"""

from pathlib import Path

import numpy as np

from ..model_manager.registry import ModelSpec

try:
    import sherpa_onnx

    SHERPA_AVAILABLE = True
except ImportError:
    SHERPA_AVAILABLE = False

from .base import VadSegment


class SherpaOnnxVadBackend:
    """Adapts sherpa_onnx.VoiceActivityDetector to the VADBackend protocol.

    Supports Silero VAD (model_family="silero") and Ten VAD (model_family="ten").
    """

    SAMPLE_RATE = 16000

    def __init__(
        self,
        spec: ModelSpec,
        model_root,
        buffer_size_in_seconds: int = 60,
        params: dict | None = None,
    ):
        if not SHERPA_AVAILABLE:
            raise ImportError("sherpa-onnx is not installed. Run: pip install sherpa-onnx")

        model_root = Path(model_root)
        cfg = params if params is not None else spec.params
        family = cfg.get("model_family", "silero")
        model_path = model_root / spec.raw["files"]["model"]

        if not model_path.is_file():
            raise FileNotFoundError(f"VAD model file not found: {model_path}")

        config = sherpa_onnx.VadModelConfig()
        sub = config.ten_vad if family == "ten" else config.silero_vad
        sub.model = str(model_path)
        sub.threshold = cfg.get("threshold", 0.5)
        sub.min_silence_duration = cfg.get("min_silence_duration", 0.5)
        sub.min_speech_duration = cfg.get("min_speech_duration", 0.25)
        # sherpa 1.13.x does not act on max_speech_duration; the force split is
        # implemented in this backend, so sherpa's own (inactive) handling
        # stays at the config value untouched.
        self._max_speech_samples = int(float(cfg.get("max_speech_duration", 20.0)) * self.SAMPLE_RATE)
        config.sample_rate = self.SAMPLE_RATE
        config.num_threads = cfg.get("num_threads", 1)
        config.provider = cfg.get("provider", "cpu")

        self._vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds)
        self._window_size = sub.window_size
        self._active_samples = 0
        self._forced_segments: list[VadSegment] = []

    @property
    def frame_size(self) -> int:
        return self._window_size

    def accept_waveform(self, frame: np.ndarray) -> None:
        was_active = self._vad.is_speech_detected()
        self._vad.accept_waveform(frame)
        if not was_active and self._vad.is_speech_detected():
            self._active_samples = 0
        if self._vad.is_speech_detected():
            self._active_samples += len(frame)
            if 0 < self._max_speech_samples <= self._active_samples:
                # sherpa never closes the open segment on its own at
                # max_speech_duration, so cut it here: copy the accumulated
                # segment, reset the detector, deliver the cut as a completed
                # segment. Continuing speech re-forms a new segment after the
                # detector's min_speech re-arming delay.
                samples = self.current_segment_samples()
                if len(samples) > 0:
                    self._forced_segments.append(VadSegment(start_sample=0, samples=samples))
                self._vad.reset()
                self._active_samples = 0

    def is_speech_active(self) -> bool:
        return self._vad.is_speech_detected()

    def current_segment_samples(self) -> np.ndarray:
        if not self._vad.is_speech_detected():
            return np.zeros(0, dtype=np.float32)
        return np.array(self._vad.current_segment.samples, dtype=np.float32, copy=True)

    def pop_ready_segments(self) -> list[VadSegment]:
        out = list(self._forced_segments)
        self._forced_segments.clear()
        while not self._vad.empty():
            seg = self._vad.front
            out.append(
                VadSegment(
                    start_sample=seg.start,
                    samples=np.array(seg.samples, dtype=np.float32, copy=True),
                )
            )
            self._vad.pop()
        return out

    def flush(self) -> None:
        self._vad.flush()

    def reset(self) -> None:
        self._vad.reset()
