"""
Streaming Pipeline for real-time transcription.

Config-driven pipeline that supports multiple ASR backends via ModelRegistry.
Supports streaming (OnlineRecognizer) and chunked (OfflineRecognizer) modes.
"""

import queue
import threading
import time
from collections.abc import Callable

import numpy as np

from .audio.capture import AudioCapture
from .events import SubtitleEvent, TranscriptMessage
from .logger import debug, exception, info, transcript, warning

# Import ASR backends and model registry
from .model_manager.manager import ModelManager
from .model_manager.registry import ModelRegistry
from .segmenter import PlainSentenceSegmenter
from .transcription.base import ChunkedASR, StreamingASR
from .transcription.sherpa_onnx import SherpaOnnxChunkedBackend, SherpaOnnxStreamingBackend

# Translation support (optional)
try:
    from .translation.translator import create_translator

    TRANSLATION_AVAILABLE = True
    debug("Translation module loaded")
except ImportError as e:
    warning(f"Translation import failed: {e}")
    TRANSLATION_AVAILABLE = False
    create_translator = None

# TranslationStateManager for incremental translation
from .translation.state_manager import TranslationStateManager

STREAMING_BACKENDS = {
    "sherpa_onnx": SherpaOnnxStreamingBackend,
}

CHUNKED_BACKENDS = {
    "sherpa_onnx": SherpaOnnxChunkedBackend,
}


class StreamingPipeline:
    """
    Config-driven streaming ASR pipeline.

    Supports multiple backends and modes:
    - Streaming mode: process audio frame-by-frame (Sherpa-ONNX).
    - Chunked mode: accumulate audio then transcribe chunks (whisper-http).
    """

    # Max consecutive failures before escalating to fatal error
    MAX_CONSECUTIVE_FAILURES = 5

    def __init__(
        self,
        model_id: str,
        registry: ModelRegistry,
        model_manager: ModelManager,
        on_subtitle: Callable[[SubtitleEvent], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_message: Callable[[TranscriptMessage], None] | None = None,
        max_lines: int = 4,
        # Translation settings
        enable_translation: bool = False,
        translation_engine: str = "google",
        target_language: str = "zh",
        audio_source: str = "system",
        # OpenAI translator settings
        openai_endpoint: str = "http://127.0.0.1:1234/v1",
        openai_api_key: str = "",
        openai_model_name: str = "",
        openai_temperature: float = 0.2,
        openai_max_tokens: int = 1024,
        openai_system_prompt: str = "",
    ):
        """
        Initialize the streaming pipeline.

        Args:
            model_id: Model ID to look up in the registry
            registry: ModelRegistry for discovering model configurations
            model_manager: ModelManager for checking download status
            on_subtitle: Callback for subtitle events
            max_lines: Maximum lines to display
            enable_translation: Whether to enable translation
            translation_engine: "google", "bing", "youdao", or "openai"
            target_language: Target language for translation
            audio_source: "system" or "mic:..." for microphone
        """
        self.on_subtitle = on_subtitle or self._default_callback
        self._on_error = on_error
        self._on_message = on_message
        self.max_lines = max_lines
        self.enable_translation = enable_translation
        self.translation_engine = translation_engine
        self.target_language = target_language

        # Look up model spec from registry
        spec = registry.get(model_id)

        # Check if model files are downloaded (never auto-download!)
        model_root = model_manager.get_model_path(spec)
        if not model_manager.is_downloaded(spec):
            raise RuntimeError(f"Model '{model_id}' is not downloaded yet. Please download it in Model Manager first.")

        # Dispatch by kind
        if spec.kind == "asr_streaming":
            backend_cls = STREAMING_BACKENDS[spec.backend]
            self._transcriber: StreamingASR = backend_cls(spec, model_root)
            self._mode = "streaming"
        elif spec.kind == "asr_chunked":
            backend_cls = CHUNKED_BACKENDS[spec.backend]
            self._transcriber: ChunkedASR = backend_cls(spec, model_root)
            self._mode = "chunked"
        else:
            raise ValueError(f"Unsupported ASR kind: {spec.kind}")

        # Translation (optional)
        self._translator = None
        self._state_manager = None
        if enable_translation and TRANSLATION_AVAILABLE:
            try:
                self._translator = create_translator(
                    engine=translation_engine,
                    target_language=target_language,
                    openai_endpoint=openai_endpoint,
                    openai_api_key=openai_api_key,
                    openai_model_name=openai_model_name,
                    openai_temperature=openai_temperature,
                    openai_max_tokens=openai_max_tokens,
                    openai_system_prompt=openai_system_prompt,
                )
                self._state_manager = TranslationStateManager(translator=self._translator.translate)
                debug("StreamingPipeline: TranslationStateManager initialized")
            except Exception as e:
                warning(f"Translation init failed: {e}")
                self._translator = None
                self._state_manager = None

        # Audio capture
        self._audio_capture = AudioCapture(source=audio_source)

        # State
        self._running = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._process_thread: threading.Thread | None = None

        # Chunked mode buffer
        self._chunk_buffer: list = []
        self._chunk_samples = 0

        # Async Conflation State (buffering ASR while translating)
        self._latest_raw_text: str = ""
        self._new_text_event = threading.Event()
        self._text_lock = threading.Lock()
        self._translation_thread: threading.Thread | None = None

        # Discrete message history (console view). When translation is off,
        # `_plain_segmenter` derives the same kind of commit batches directly
        # from the raw ASR text so the console still gets one line per group
        # of sentences instead of nothing.
        self._msg_seq: int = 0
        self._plain_segmenter: PlainSentenceSegmenter | None = None
        if not self._state_manager:
            self._plain_segmenter = PlainSentenceSegmenter()

        # Failure tracking
        self._consecutive_asr_failures: int = 0
        self._consecutive_translation_failures: int = 0
        self._asr_fatal: bool = False

        trans_status = "enabled (incremental)" if self._state_manager else "disabled"
        info(f"StreamingPipeline: mode={self._mode}, backend={spec.backend}, translation={trans_status}")

    def _default_callback(self, event: SubtitleEvent) -> None:
        """Default subtitle callback."""
        debug(f"[{event.language}] {event.text}")

    def _emit_message(self, original: str, translation: str | None) -> None:
        """Emit one finalized console-history line."""
        if not self._on_message or not original:
            return
        self._msg_seq += 1
        self._on_message(
            TranscriptMessage(
                msg_id=self._msg_seq,
                timestamp=time.time(),
                original=original,
                translation=translation,
            )
        )

    def _on_audio(self, audio: np.ndarray, sample_rate: int) -> None:
        """Callback from AudioCapture."""
        self._audio_queue.put(audio)

    def _process_loop(self) -> None:
        """
        ASR Thread: High-speed audio processing.
        Produces raw text stream, never blocks on translation.
        """
        while self._running:
            try:
                audio = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # Dispatch by mode, wrapped in try/except for resilience
            try:
                if self._mode == "streaming":
                    raw_text = self._transcriber.process_audio(audio)
                elif self._mode == "chunked":
                    self._chunk_buffer.append(audio)
                    self._chunk_samples += len(audio)

                    chunk_seconds = getattr(self._transcriber, "chunk_seconds", 2.0)
                    chunk_samples_needed = int(16000 * chunk_seconds)
                    if self._chunk_samples < chunk_samples_needed:
                        continue

                    combined = np.concatenate(self._chunk_buffer)
                    self._chunk_buffer = []
                    self._chunk_samples = 0
                    raw_text = self._transcriber.transcribe(combined, 16000)
                else:
                    raw_text = ""

                # Reset failure counter on success
                self._consecutive_asr_failures = 0

            except Exception:
                self._consecutive_asr_failures += 1
                exception(f"ASR backend error ({self._consecutive_asr_failures}/{self.MAX_CONSECUTIVE_FAILURES})")
                if self._consecutive_asr_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    self._asr_fatal = True
                    if self._on_error:
                        self._on_error("error_asr_backend_failed")
                    break
                # Single failure: skip this chunk, continue
                continue

            # Check for changes to avoid redundant updates
            if not raw_text or raw_text == self._latest_raw_text:
                continue

            # Update latest text safely
            with self._text_lock:
                self._latest_raw_text = raw_text
                self._new_text_event.set()  # Signal translation thread

            transcript(raw_text)

            # If no translation, emit immediately
            if not self._state_manager:
                event = SubtitleEvent(
                    text=raw_text,
                    language="",
                    confidence=1.0,
                    timestamp=time.time(),
                    is_partial=True,
                    committed_translation="",
                    draft_translation="",
                    target_language=None,
                )
                self.on_subtitle(event)

                if self._plain_segmenter:
                    committed = self._plain_segmenter.process_text(raw_text)
                    if committed:
                        self._emit_message(committed, None)

    def _translation_loop(self) -> None:
        """
        Translation Thread: Low-speed translation processing.
        Consumes latest raw text, blocks on network calls.
        Conflates updates (skips intermediate frames if falling behind).
        """
        _translation_error_reported = False
        while self._running:
            if not self._new_text_event.wait(timeout=0.1):
                continue

            raw_text = ""
            with self._text_lock:
                raw_text = self._latest_raw_text
                self._new_text_event.clear()

            if not raw_text or not self._state_manager:
                continue

            try:
                state = self._state_manager.process_text(raw_text)
                if state.committed_text:
                    transcript(state.committed_text)
                if state.draft_text:
                    transcript(state.draft_text)

                event = SubtitleEvent(
                    text=raw_text,
                    language="",
                    confidence=1.0,
                    timestamp=time.time(),
                    is_partial=True,
                    committed_translation=state.committed_text,
                    draft_translation=state.draft_text,
                    target_language=self.target_language,
                )
                self.on_subtitle(event)

                batch = self._state_manager.pop_committed_batch()
                if batch:
                    self._emit_message(batch[0], batch[1])

                # Reset failure counter on success
                self._consecutive_translation_failures = 0
                _translation_error_reported = False

            except Exception:
                self._consecutive_translation_failures += 1
                exception(
                    f"Translation error ({self._consecutive_translation_failures}/{self.MAX_CONSECUTIVE_FAILURES})"
                )
                if (
                    self._consecutive_translation_failures >= self.MAX_CONSECUTIVE_FAILURES
                    and not _translation_error_reported
                    and self._on_error
                ):
                    self._on_error("error_translation_unavailable")
                    _translation_error_reported = True

    def start(self) -> None:
        """Start the streaming pipeline."""
        if self._running:
            return

        self._running = True

        # Reset state
        self._latest_raw_text = ""
        self._new_text_event.clear()

        if self._state_manager:
            self._state_manager.reset()
        if self._plain_segmenter:
            self._plain_segmenter.reset()
        self._msg_seq = 0

        # Start threads
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True, name="StreamingPipeline_ASR")
        self._process_thread.start()

        if self._state_manager:
            self._translation_thread = threading.Thread(
                target=self._translation_loop, daemon=True, name="StreamingPipeline_Translation"
            )
            self._translation_thread.start()

        # Start audio capture
        self._audio_capture.start(callback=self._on_audio)

        info("StreamingPipeline started")

    def stop(self) -> None:
        """Stop the pipeline."""
        self._running = False
        self._new_text_event.set()

        self._audio_capture.stop()

        if self._process_thread:
            self._process_thread.join(timeout=2.0)

        if self._translation_thread:
            self._translation_thread.join(timeout=2.0)

        # Clear queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        info("StreamingPipeline stopped")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
