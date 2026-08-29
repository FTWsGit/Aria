"""SherpaOnnxVadBackend tests against the real silero model.

Skipped when the VAD model is not downloaded locally (models_cache is
machine-local and gitignored).
"""

from pathlib import Path

import numpy as np
import pytest

from aria.model_manager.registry import ModelRegistry
from aria.vad.sherpa_vad import SherpaOnnxVadBackend

MODEL_DIR = Path("models_cache/vad-silero-v5")
MODELS_DIR = Path("models")

pytestmark = pytest.mark.skipif(
    not (MODEL_DIR / "silero_vad.onnx").is_file() or not MODELS_DIR.is_dir(),
    reason="silero VAD model not downloaded locally",
)

SR = 16000


def _make_backend(params: dict) -> SherpaOnnxVadBackend:
    spec = ModelRegistry(MODELS_DIR).get("vad-silero-v5")
    return SherpaOnnxVadBackend(spec, MODEL_DIR, params=params)


def _speech_signal(seconds: float) -> np.ndarray:
    """Harmonic stack with syllable envelope; silero reliably detects it as speech."""
    t = np.arange(int(seconds * SR)) / SR
    env = 0.5 * (1 + np.sin(2 * np.pi * 4.0 * t))
    sig = sum(np.sin(2 * np.pi * f * t + 3 * np.sin(2 * np.pi * 5.0 * t)) for f in (120, 240, 360, 480))
    return (0.4 * env * sig / 4).astype(np.float32)


def _feed(backend: SherpaOnnxVadBackend, audio: np.ndarray) -> list:
    segments = []
    for i in range(len(audio) // 1600):
        backend.accept_waveform(audio[i * 1600 : (i + 1) * 1600])
        segments.extend(backend.pop_ready_segments())
    backend.flush()
    segments.extend(backend.pop_ready_segments())
    return segments


def test_max_speech_duration_force_split():
    """sherpa ignores max_speech_duration; the backend's own force split must
    bound the segment length."""
    backend = _make_backend(
        {
            "threshold": 0.5,
            "min_silence_duration": 5.0,
            "min_speech_duration": 0.1,
            "max_speech_duration": 4.0,
        }
    )
    segments = _feed(backend, _speech_signal(14.0))
    assert len(segments) >= 2, f"expected force splits, got {len(segments)} segments"
    for seg in segments:
        assert len(seg.samples) / SR <= 5.5, f"segment too long: {len(seg.samples) / SR:.2f}s"


def test_min_silence_still_closes_segments():
    """With force-split disabled (max_speech_duration=0), min_silence closes
    segments normally."""
    backend = _make_backend(
        {
            "threshold": 0.5,
            "min_silence_duration": 0.3,
            "min_speech_duration": 0.1,
            "max_speech_duration": 0.0,
        }
    )
    speech = _speech_signal(2.0)
    silence = np.zeros(int(0.6 * SR), dtype=np.float32)
    segments = _feed(backend, np.concatenate([speech, silence, speech]))
    assert len(segments) >= 2, f"expected 2+ segments, got {len(segments)}"
