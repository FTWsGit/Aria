"""
Sherpa-ONNX streaming ASR backend with config-driven recognizer factory.

Replaces the hardcoded from_transducer with a YAML-driven factory pattern.
Supports transducer, paraformer, whisper, nemo-ctc and any future sherpa-onnx arch.
"""

import numpy as np

from ..logger import info
from ..model_manager.registry import ModelSpec

try:
    import sherpa_onnx

    SHERPA_AVAILABLE = True
except ImportError:
    SHERPA_AVAILABLE = False


class SherpaOnnxBackend:
    """Config-driven Sherpa-ONNX streaming ASR backend."""

    SAMPLE_RATE = 16000

    def __init__(self, spec: ModelSpec, model_root):
        """Initialize from a ModelSpec and downloaded model root directory.

        Args:
            spec: ModelSpec from registry (contains raw yaml with files, recognizer_factory, etc.)
            model_root: Path to downloaded model directory (resolved by ModelManager)
        """
        if not SHERPA_AVAILABLE:
            raise ImportError("sherpa-onnx is not installed. Run: pip install sherpa-onnx")

        from pathlib import Path

        model_root = Path(model_root)

        # Read Sherpa-specific fields from raw yaml
        files = spec.raw.get("files", {})
        factory_name = spec.raw.get("recognizer_factory", "from_transducer")

        # Resolve file paths to absolute paths
        resolved_files = {k: str(model_root / v) for k, v in files.items()}

        info(f"SherpaOnnxBackend: Initializing with factory={factory_name}, files={list(resolved_files.keys())}")

        # Get factory method dynamically
        factory = getattr(sherpa_onnx.OnlineRecognizer, factory_name)

        kwargs = {
            **resolved_files,
            **spec.params,
            "sample_rate": self.SAMPLE_RATE,
        }
        kwargs.setdefault("num_threads", 4)
        kwargs.setdefault("feature_dim", 80)
        kwargs.setdefault("decoding_method", "greedy_search")
        self._recognizer = factory(**kwargs)
        self._stream = self._recognizer.create_stream()

        info("SherpaOnnxBackend: Initialized")

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
