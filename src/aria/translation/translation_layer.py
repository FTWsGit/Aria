"""
TranslationLayer - shared translation orchestration for ASR pipelines.

Provides a single entry point for translation creation, state management,
and plain-sentence fallback, eliminating duplicate code across pipeline.py
and livecaptions/pipeline.py.
"""

import time
from collections import namedtuple
from collections.abc import Callable

from ..events import TranscriptMessage
from ..logger import debug, warning
from ..segmenter import PlainSentenceSegmenter
from .state_manager import TranslationStateManager

try:
    from .translator import create_translator

    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    create_translator = None  # type: ignore[assignment]

TranslationProcessResult = namedtuple(
    "TranslationProcessResult", ["committed_text", "draft_text", "batch"]
)


class TranslationLayer:
    """Encapsulates translation creation, incremental state, and plain-segmenter fallback.

    Callers use `process_text()` to feed raw source text and receive
    committed/draft translation buffers plus an optional commit batch for
    console-history emission.  `emit_message()` forwards the batch to the
    caller-supplied callback.
    """

    def __init__(
        self,
        enable_translation: bool,
        translation_engine: str,
        target_language: str,
        openai_endpoint: str,
        openai_api_key: str,
        openai_model_name: str,
        openai_temperature: float,
        openai_max_tokens: int,
        openai_system_prompt: str,
        on_message: Callable[[TranscriptMessage], None] | None,
    ):
        self._translator = None
        self._state_manager = None
        self._plain_segmenter: PlainSentenceSegmenter | None = None
        self._on_message = on_message
        self._msg_seq = 0

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
                debug("TranslationLayer: initialized")
            except Exception as e:
                warning(f"TranslationLayer: init failed: {e}")
                self._translator = None

        if not self._state_manager:
            self._plain_segmenter = PlainSentenceSegmenter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_text(self, raw_text: str) -> TranslationProcessResult:
        """Feed the latest raw source text; return current translation buffers.

        Returns a ``TranslationProcessResult`` whose fields are:

        * ``committed_text`` — stable translation paragraph (may be empty)
        * ``draft_text`` — in-progress draft translation (may be empty)
        * ``batch`` — ``(source, translation)`` tuple for a newly committed
          batch, or ``None`` if nothing committed this cycle
        """
        if not raw_text:
            return TranslationProcessResult("", "", None)

        if self._state_manager:
            state = self._state_manager.process_text(raw_text)
            batch = self._state_manager.pop_committed_batch()
            return TranslationProcessResult(state.committed_text, state.draft_text, batch)
        elif self._plain_segmenter:
            committed = self._plain_segmenter.process_text(raw_text)
            return TranslationProcessResult("", "", (committed, None) if committed else None)
        else:
            return TranslationProcessResult("", "", None)

    def emit_message(self, original: str, translation: str | None) -> None:
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

    def reset(self) -> None:
        """Reset all accumulated state (committed sources, draft, seq counter)."""
        if self._state_manager:
            self._state_manager.reset()
        if self._plain_segmenter:
            self._plain_segmenter.reset()
        self._msg_seq = 0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """True when translation is enabled and a translator was created."""
        return self._state_manager is not None

    @property
    def target_language(self) -> str | None:
        """Target language code from the translator, or None."""
        if self._translator:
            return self._translator.target_language
        return None
