"""
Sherpa-ONNX streaming ASR backend with config-driven recognizer factory.

Replaces the hardcoded from_transducer with a YAML-driven factory pattern.
Supports transducer, paraformer, whisper, nemo-ctc and any future sherpa-onnx arch.
"""

from pathlib import Path

import numpy as np

from ..logger import info
from ..model_manager.registry import ModelSpec

try:
    import sherpa_onnx

    SHERPA_AVAILABLE = True
except ImportError:
    SHERPA_AVAILABLE = False


def _build_sherpa_kwargs(spec: ModelSpec, model_root: Path) -> dict:
    """Resolve file paths and merge params for a Sherpa-ONNX recognizer factory."""
    files = spec.raw.get("files", {})
    resolved_files = {k: str(model_root / v) for k, v in files.items()}
    kwargs = {**resolved_files, **spec.params}
    kwargs.setdefault("num_threads", 4)
    kwargs.setdefault("decoding_method", "greedy_search")
    return kwargs


class SherpaOnnxStreamingBackend:
    """Config-driven Sherpa-ONNX streaming ASR backend (OnlineRecognizer)."""

    SAMPLE_RATE = 16000

    def __init__(self, spec: ModelSpec, model_root):
        if not SHERPA_AVAILABLE:
            raise ImportError("sherpa-onnx is not installed. Run: pip install sherpa-onnx")

        model_root = Path(model_root)
        factory_name = spec.raw.get("recognizer_factory", "from_transducer")

        info(f"SherpaOnnxStreamingBackend: Initializing with factory={factory_name}")

        factory = getattr(sherpa_onnx.OnlineRecognizer, factory_name)
        kwargs = _build_sherpa_kwargs(spec, model_root)
        kwargs["sample_rate"] = self.SAMPLE_RATE
        kwargs.setdefault("feature_dim", 80)
        self._recognizer = factory(**kwargs)
        self._stream = self._recognizer.create_stream()

        info("SherpaOnnxStreamingBackend: Initialized")

    def process_audio(self, audio: np.ndarray) -> str:
        self._stream.accept_waveform(self.SAMPLE_RATE, audio)
        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)
        result = self._recognizer.get_result(self._stream)
        return result.strip() if isinstance(result, str) else getattr(result, "text", "").strip()

    def reset(self) -> None:
        self._recognizer.reset(self._stream)

    def get_final_result(self) -> str:
        tail_paddings = np.zeros(int(self.SAMPLE_RATE * 0.5), dtype=np.float32)
        self._stream.accept_waveform(self.SAMPLE_RATE, tail_paddings)
        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)
        result = self._recognizer.get_result(self._stream)
        return result.strip() if isinstance(result, str) else getattr(result, "text", "").strip()


class SherpaOnnxChunkedBackend:
    """Chunked ASR backend using Sherpa-ONNX OfflineRecognizer.

    Each chunk is treated as a complete utterance — a new stream is created
    per transcribe() call, decoded, and the result text returned.
    """

    SAMPLE_RATE = 16000

    def __init__(self, spec: ModelSpec, model_root):
        if not SHERPA_AVAILABLE:
            raise ImportError("sherpa-onnx is not installed. Run: pip install sherpa-onnx")

        model_root = Path(model_root)
        factory_name = spec.raw.get("recognizer_factory", "from_transducer")

        info(f"SherpaOnnxChunkedBackend: Initializing with factory={factory_name}")

        factory = getattr(sherpa_onnx.OfflineRecognizer, factory_name)
        kwargs = _build_sherpa_kwargs(spec, model_root)
        self._recognizer = factory(**kwargs)
        
        info("SherpaOnnxChunkedBackend: Initialized")

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        stream = self._recognizer.create_stream()
        stream.accept_waveform(sample_rate, audio)
        self._recognizer.decode_stream(stream)
        return stream.result.text.strip()
