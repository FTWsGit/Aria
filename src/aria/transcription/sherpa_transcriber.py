"""
Sherpa-ONNX Streaming Transcriber for real-time speech recognition.

Uses Sherpa-ONNX OnlineRecognizer for true streaming transcription.
Model paths are provided explicitly — no hardcoded model configs.
"""

import numpy as np

from ..logger import debug, info

# Sherpa import with error handling
try:
    import sherpa_onnx

    SHERPA_AVAILABLE = True
except ImportError:
    SHERPA_AVAILABLE = False


class SherpaTranscriber:
    """
    Sherpa-ONNX based streaming transcriber.

    Features:
    - True streaming: outputs text incrementally
    - No hardcoded models: accepts explicit ONNX/token paths
    - No repetition: proper streaming architecture
    """

    SAMPLE_RATE = 16000

    def __init__(
        self,
        encoder: str,
        decoder: str,
        joiner: str,
        tokens: str,
        num_threads: int = 4,
        feature_dim: int = 80,
        decoding_method: str = "greedy_search",
    ):
        """
        Initialize the Sherpa transcriber with explicit model paths.

        Args:
            encoder: Path to encoder ONNX model
            decoder: Path to decoder ONNX model
            joiner: Path to joiner ONNX model
            tokens: Path to tokens.txt
            num_threads: Number of CPU threads for inference
            feature_dim: Feature dimension (default 80)
            decoding_method: Decoding method (greedy_search or modified_beam_search)
        """
        if not SHERPA_AVAILABLE:
            raise ImportError("sherpa-onnx is not installed. Run: pip install sherpa-onnx")

        debug(f"SherpaTranscriber: Loading model from {encoder}")

        self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            encoder=encoder,
            decoder=decoder,
            joiner=joiner,
            tokens=tokens,
            num_threads=num_threads,
            sample_rate=self.SAMPLE_RATE,
            feature_dim=feature_dim,
            decoding_method=decoding_method,
        )

        # Create stream
        self._stream = self._recognizer.create_stream()

        info("SherpaTranscriber: Initialized")

    def process_audio(self, audio: np.ndarray) -> str:
        """
        Process audio data and get transcription.

        Args:
            audio: Audio samples (float32, 16kHz mono)

        Returns:
            Full accumulated transcript text (continuous stream, no segmentation)
        """
        # Feed audio to stream
        self._stream.accept_waveform(self.SAMPLE_RATE, audio)

        # Decode
        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)

        # Get result - sherpa returns string directly
        result = self._recognizer.get_result(self._stream)
        text = result.strip() if isinstance(result, str) else getattr(result, "text", "").strip()

        return text

    def reset(self) -> None:
        """Reset the recognizer state."""
        self._recognizer.reset(self._stream)

    def get_final_result(self) -> str:
        """Get any remaining final result."""
        # Flush the stream
        tail_paddings = np.zeros(int(self.SAMPLE_RATE * 0.5), dtype=np.float32)
        self._stream.accept_waveform(self.SAMPLE_RATE, tail_paddings)

        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)

        result = self._recognizer.get_result(self._stream)
        text = result.strip() if isinstance(result, str) else getattr(result, "text", "").strip()
        return text
