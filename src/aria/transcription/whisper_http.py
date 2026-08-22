"""
Whisper HTTP backend - connects to any OpenAI-compatible /v1/audio/transcriptions service.

Supports whisper.cpp (whisper-server), faster-whisper-server, and any OpenAI Audio API compatible service.
"""

import io
import wave

import numpy as np
import requests

from ..logger import debug, info
from ..model_manager.registry import ModelSpec


class WhisperHttpBackend:
    """Chunked ASR backend that sends audio to an OpenAI-compatible HTTP endpoint."""

    def __init__(self, spec: ModelSpec, model_root=None):
        """Initialize from a ModelSpec.

        Args:
            spec: ModelSpec with raw yaml containing endpoint, api_key, model_name
            model_root: Not used for HTTP backend (kept for interface consistency)
        """
        self.endpoint = spec.raw["endpoint"]
        self.api_key = spec.raw.get("api_key")
        self.model_name = spec.raw.get("model_name", "whisper-1")
        self.language = spec.params.get("language", "auto")
        self.chunk_seconds = spec.params.get("chunk_seconds", 2.0)

        info(f"WhisperHttpBackend: endpoint={self.endpoint}, model={self.model_name}, language={self.language}")

    def _audio_to_bytes(self, audio: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy float32 audio to WAV bytes."""
        audio_int16 = (audio * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())
        return buf.getvalue()

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        """Send audio chunk to the HTTP endpoint and return transcribed text."""
        wav_bytes = self._audio_to_bytes(audio, sample_rate)
        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        data = {"model": self.model_name}
        if self.language and self.language != "auto":
            data["language"] = self.language

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        debug(f"WhisperHttpBackend: Sending {len(wav_bytes)} bytes to {self.endpoint}")
        resp = requests.post(self.endpoint, files=files, data=data, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        text = result.get("text", "").strip()
        debug(f"WhisperHttpBackend: Got result: '{text[:60]}...'")
        return text
