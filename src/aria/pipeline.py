"""
Streaming Pipeline for real-time transcription.

Uses Sherpa-ONNX OnlineRecognizer for pure streaming ASR.
Audio flows directly from capture → Sherpa → partial results → UI.
No VAD, no segmentation, no multi-backend routing.
"""

import threading
import queue
import time
from pathlib import Path
from typing import Optional, Callable
import numpy as np

from .audio.capture import AudioCapture
from .events import SubtitleEvent
from .logger import info, debug, warning, error, transcript

# Import Sherpa transcriber
from .transcription.sherpa_transcriber import SherpaTranscriber, SHERPA_AVAILABLE

# Translation support (optional)
try:
    from .translation.translator import create_translator, CTRANSLATE2_AVAILABLE, GOOGLETRANS_AVAILABLE
    TRANSLATION_AVAILABLE = CTRANSLATE2_AVAILABLE or GOOGLETRANS_AVAILABLE
    debug(f"Translation module loaded, CTRANSLATE2={CTRANSLATE2_AVAILABLE}, GOOGLE={GOOGLETRANS_AVAILABLE}")
except ImportError as e:
    warning(f"Translation import failed: {e}")
    TRANSLATION_AVAILABLE = False
    create_translator = None

# TranslationStateManager for incremental translation
from .livecaptions.manager import TranslationStateManager


def _discover_model_paths(model_dir: Optional[str] = None) -> tuple:
    """Discover Sherpa model files in the given directory.

    Looks for files matching *encoder*.onnx, *decoder*.onnx, *joiner*.onnx, tokens.txt.
    """
    if model_dir is None:
        current = Path(__file__).resolve()
        project_root = current.parent.parent.parent
        search_dir = project_root / "models"
    else:
        search_dir = Path(model_dir)

    if not search_dir.is_dir():
        raise FileNotFoundError(
            f"Model directory not found: {search_dir}\n"
            f"Please place Sherpa-ONNX model files (encoder.onnx, decoder.onnx, joiner.onnx, tokens.txt) in {search_dir}"
        )

    def _find_in_dir(directory: Path, pattern: str) -> str:
        matches = sorted(directory.glob(pattern))
        if matches:
            return str(matches[0])
        # Also search one level deep (for extracted model subdirectories)
        for sub in directory.iterdir():
            if sub.is_dir():
                sub_matches = sorted(sub.glob(pattern))
                if sub_matches:
                    return str(sub_matches[0])
        raise FileNotFoundError(
            f"Could not find '{pattern}' in {directory}\n"
            f"Please ensure your Sherpa-ONNX model files are in this directory."
        )

    encoder = _find_in_dir(search_dir, "*encoder*.onnx")
    decoder = _find_in_dir(search_dir, "*decoder*.onnx")
    joiner = _find_in_dir(search_dir, "*joiner*.onnx")
    tokens = _find_in_dir(search_dir, "tokens.txt")

    info(f"Discovered model: encoder={Path(encoder).name}, decoder={Path(decoder).name}")
    return encoder, decoder, joiner, tokens


class StreamingPipeline:
    """
    Pure streaming transcription pipeline using Sherpa-ONNX.

    Audio flows continuously:
        AudioCapture → Sherpa OnlineRecognizer → partial results → UI

    No VAD, no speech segmentation, no multi-backend routing.
    """

    def __init__(
        self,
        encoder: Optional[str] = None,
        decoder: Optional[str] = None,
        joiner: Optional[str] = None,
        tokens: Optional[str] = None,
        model_dir: Optional[str] = None,
        on_subtitle: Optional[Callable[[SubtitleEvent], None]] = None,
        max_lines: int = 4,
        # Translation settings
        enable_translation: bool = False,
        translation_engine: str = "google",
        target_language: str = "zh",
        audio_source: str = "system",
    ):
        """
        Initialize the streaming pipeline.

        Args:
            encoder: Path to encoder ONNX model (auto-discovered if model_dir is set)
            decoder: Path to decoder ONNX model (auto-discovered if model_dir is set)
            joiner: Path to joiner ONNX model (auto-discovered if model_dir is set)
            tokens: Path to tokens.txt (auto-discovered if model_dir is set)
            model_dir: Directory to auto-discover model files (default: models/)
            on_subtitle: Callback for subtitle events
            max_lines: Maximum lines to display
            enable_translation: Whether to enable translation
            translation_engine: "google", "nllb", "bing", or "youdao"
            target_language: Target language for translation
            audio_source: "system" or "mic:..." for microphone
        """
        self.on_subtitle = on_subtitle or self._default_callback
        self.max_lines = max_lines
        self.enable_translation = enable_translation
        self.translation_engine = translation_engine
        self.target_language = target_language

        # Auto-discover model paths if not explicitly provided
        if encoder and decoder and joiner and tokens:
            pass  # Use explicit paths
        else:
            encoder, decoder, joiner, tokens = _discover_model_paths(model_dir)

        if not SHERPA_AVAILABLE:
            raise ImportError("sherpa-onnx is required. Run: pip install sherpa-onnx")

        self._transcriber = SherpaTranscriber(
            encoder=encoder,
            decoder=decoder,
            joiner=joiner,
            tokens=tokens,
        )

        # Translation (optional)
        self._translator = None
        self._state_manager = None
        if enable_translation and TRANSLATION_AVAILABLE:
            try:
                self._translator = create_translator(
                    engine=translation_engine,
                    target_language=target_language,
                )
                self._state_manager = TranslationStateManager(
                    translator=self._translator.translate
                )
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
        self._process_thread: Optional[threading.Thread] = None

        # Async Conflation State (buffering ASR while translating)
        self._latest_raw_text: str = ""
        self._new_text_event = threading.Event()
        self._text_lock = threading.Lock()
        self._translation_thread: Optional[threading.Thread] = None

        trans_status = "enabled (incremental)" if self._state_manager else "disabled"
        info(f"StreamingPipeline: Sherpa-ONNX, translation={trans_status}")

    def _default_callback(self, event: SubtitleEvent) -> None:
        """Default subtitle callback."""
        debug(f"[{event.language}] {event.text}")

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

            # Process with Sherpa (fast, local C++ call)
            raw_text = self._transcriber.process_audio(audio)

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

    def _translation_loop(self) -> None:
        """
        Translation Thread: Low-speed translation processing.
        Consumes latest raw text, blocks on network calls.
        Conflates updates (skips intermediate frames if falling behind).
        """
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

            except Exception as e:
                warning(f"StreamingPipeline: Translation error: {e}")

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

        # Start threads
        self._process_thread = threading.Thread(
            target=self._process_loop,
            daemon=True,
            name="StreamingPipeline_ASR"
        )
        self._process_thread.start()

        if self._state_manager:
            self._translation_thread = threading.Thread(
                target=self._translation_loop,
                daemon=True,
                name="StreamingPipeline_Translation"
            )
            self._translation_thread.start()

        # Start audio capture
        self._audio_capture.start(callback=self._on_audio)

        info("StreamingPipeline started (Sherpa-ONNX)")

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