"""
TranslationStateManager - Overwrite-Draft Translation with Sliding Window

Simplified logic:
1. Committed sources are stable - we track the source sentences.
2. Committed translation is the translation of all committed sources (one string).
3. Draft is everything after committed - fully re-translated on every update.
4. When draft accumulates enough SOURCE sentences, promote them to committed.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher

# Import logger - use try/except for standalone testing
try:
    from ..logger import debug, info, warning
except ImportError:
    # Fallback for testing without full package
    def debug(msg):
        print(f"[DEBUG] {msg}")

    def info(msg):
        print(f"[INFO] {msg}")

    def warning(msg):
        print(f"[WARN] {msg}")


try:
    from ..segmenter import (
        COMMIT_COUNT,
        DRAFT_CHAR_THRESHOLD,
        DRAFT_COMMIT_THRESHOLD,
        compute_commit_target,
        segment_sentences,
    )
    from ..segmenter import MAX_SENTENCE_LENGTH as _MAX_SENTENCE_LENGTH
    from ..segmenter import SENTENCE_DELIMITERS as _SENTENCE_DELIMITERS
except ImportError:
    # Fallback for standalone testing
    _SENTENCE_DELIMITERS = r"[.。？！?!\n，,、]"
    _MAX_SENTENCE_LENGTH = 80
    DRAFT_COMMIT_THRESHOLD = 6
    COMMIT_COUNT = 4
    DRAFT_CHAR_THRESHOLD = 150

    def segment_sentences(text):
        if not text:
            return []
        parts = re.split(_SENTENCE_DELIMITERS, text)
        sentences = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) > _MAX_SENTENCE_LENGTH:
                for i in range(0, len(part), _MAX_SENTENCE_LENGTH):
                    chunk = part[i : i + _MAX_SENTENCE_LENGTH].strip()
                    if chunk:
                        sentences.append(chunk)
            else:
                sentences.append(part)
        return sentences

    def compute_commit_target(draft_sources):
        total = len(draft_sources)
        char_len = sum(len(s) for s in draft_sources)
        if total < DRAFT_COMMIT_THRESHOLD and char_len < DRAFT_CHAR_THRESHOLD:
            return None
        return COMMIT_COUNT if total >= COMMIT_COUNT else max(1, total - 1)


@dataclass
class TranslationState:
    """Represents the current translation state."""

    committed_text: str = ""  # White text (stable, translated)
    draft_text: str = ""  # Green text (in progress, translated)


class TranslationStateManager:
    """
    Manages translation with overwrite-draft mechanism.

    Core Logic:
    1. Maintain committed sources (list of sentences that are stable).
    2. Maintain committed translation (single string for all committed).
    3. On each update:
       a. Find where committed content ends in new input (prefix matching).
       b. Everything after = draft portion.
       c. Translate the ENTIRE draft portion (overwrite, not append).
    4. When draft has enough source sentences, promote them to committed.
    """

    # Buffer thresholds (imported from segmenter.py)
    DRAFT_COMMIT_THRESHOLD = DRAFT_COMMIT_THRESHOLD

    # Fuzzy matching threshold
    FUZZY_THRESHOLD = 0.65  # 65% similarity = match (Lowered for stability)

    # Max draft size (sentences) to prevent huge translation requests
    # MUST be >= DRAFT_COMMIT_THRESHOLD to avoid skipping sentences
    MAX_DRAFT_SENTENCES = 8

    def __init__(
        self,
        translator: Callable[[str], str] | None = None,
    ):
        """
        Initialize the manager.

        Args:
            translator: Function to translate text (source -> target)
        """
        self.translator = translator

        # Committed state
        self._committed_sources: list[str] = []  # Source sentences that are locked
        self._committed_paragraphs: list[str] = []  # Translation paragraphs (each commit batch = 1 paragraph)

        # Draft state (volatile, overwritten each update)
        self._draft_sources: list[str] = []  # Source sentences pending
        self._draft_translation: str = ""  # Translation of draft sources
        self._last_processed_text: str = ""  # Cache for duplicate detection

        # Most recently committed batch, for callers that want one message
        # per commit rather than the full running `committed_text`.
        self._last_committed_batch: tuple[str, str] | None = None

    def process_text(self, full_source_text: str) -> TranslationState:
        """
        Advance translation state with new source text.

        This is a stateful operation: it may truncate committed content on
        divergence, re-translate draft, promote draft to committed, and
        populate the batch buffer for `pop_committed_batch`.

        Args:
            full_source_text: The complete source text from LiveCaptions

        Returns:
            TranslationState with committed (white) and draft (green) text
        """
        # Duplicate check: If text hasn't changed, don't re-process
        if full_source_text == self._last_processed_text:
            return self._build_state()

        self._last_processed_text = full_source_text

        if not full_source_text or not full_source_text.strip():
            return self._build_state()

        # Segment into sentences
        source_sentences = segment_sentences(full_source_text)

        if not source_sentences:
            return self._build_state()

        # Safeguard: If starting fresh with huge history, only take last 6 sentences
        # This prevents overwhelming the translator on initial startup
        if not self._committed_sources and len(source_sentences) > self.DRAFT_COMMIT_THRESHOLD:
            source_sentences = source_sentences[-self.DRAFT_COMMIT_THRESHOLD :]

        # Find where committed content ends, then truncate if diverged
        committed_end_index = self._find_committed_end(source_sentences)
        committed_end_index = self._recommit_from_divergence(source_sentences, committed_end_index)

        # Everything after committed = draft portion
        draft_sources = source_sentences[committed_end_index:]

        # FIX: Check if draft is too large (lost sync or huge update)
        # If so, force-commit the excess without translation to catch up
        if len(draft_sources) > self.MAX_DRAFT_SENTENCES:
            skipped_count = len(draft_sources) - self.MAX_DRAFT_SENTENCES
            skipped_part = draft_sources[:skipped_count]
            draft_sources = draft_sources[skipped_count:]

            # Add skipped part to committed sources so we match them next time
            # But DO NOT add to committed_paragraphs (hiding them from UI)
            self._committed_sources.extend(skipped_part)
            warning(f"TSM: Draft too large ({skipped_count + len(draft_sources)}), skipped {skipped_count} sentences.")

        self._draft_sources = draft_sources

        if not draft_sources:
            # No new content, just return current state
            self._draft_translation = ""
            return self._build_state()

        # OVERWRITE draft: translate entire draft portion
        if self.translator:
            try:
                draft_text = " ".join(draft_sources)
                translated = self.translator(draft_text)
                self._draft_translation = translated or ""
            except Exception as e:
                warning(f"TSM: Translation error: {e}")
                self._draft_translation = ""

        # Check if we should commit some draft
        self._check_commit_threshold()

        return self._build_state()

    def _find_committed_end(self, source_sentences: list[str]) -> int:
        """Find where committed content ends in source sentences (read-only)."""
        if not self._committed_sources:
            return 0

        matched_count = 0
        for _i, committed_src in enumerate(self._committed_sources):
            if matched_count >= len(source_sentences):
                break
            similarity = self._similarity(committed_src, source_sentences[matched_count])
            if similarity >= self.FUZZY_THRESHOLD:
                matched_count += 1
            else:
                break

        return matched_count

    def _recommit_from_divergence(self, source_sentences: list[str], committed_end: int) -> int:
        """Truncate committed sources at divergence point and re-translate."""
        if committed_end >= len(self._committed_sources):
            return committed_end
        if committed_end >= len(source_sentences):
            self._committed_sources = self._committed_sources[:committed_end]
            self._retranslate_committed()
            return min(committed_end, len(source_sentences))
        self._committed_sources = self._committed_sources[:committed_end]
        self._retranslate_committed()
        return committed_end

    def _retranslate_committed(self) -> None:
        """Re-translate all committed sources after trimming (rebuild paragraphs)."""
        if not self._committed_sources or not self.translator:
            self._committed_paragraphs.clear()
            return

        # When committed is trimmed, we need to rebuild as a single paragraph
        # (We lose the paragraph structure, but this is a rare edge case)
        try:
            text = " ".join(self._committed_sources)
            translated = self.translator(text) or ""
            self._committed_paragraphs = [translated] if translated else []
        except Exception as e:
            warning(f"TSM: Re-translation error: {e}")

    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity ratio between two strings."""
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _check_commit_threshold(self) -> None:
        """Check if draft should be partially committed."""
        commit_target = compute_commit_target(self._draft_sources)
        if commit_target is None:
            return

        to_commit = self._draft_sources[:commit_target]
        batch_text = " ".join(to_commit)

        # Add to committed sources
        self._committed_sources.extend(to_commit)

        # Translate the newly committed batch and add as a NEW PARAGRAPH
        batch_translation = ""
        if self.translator:
            try:
                batch_translation = self.translator(batch_text) or ""
                if batch_translation:
                    self._committed_paragraphs.append(batch_translation)
            except Exception as e:
                warning(f"TSM: Commit translation error: {e}")

        self._last_committed_batch = (batch_text, batch_translation)

        # Remove from draft
        self._draft_sources = self._draft_sources[commit_target:]

        # Re-translate remaining draft
        if self._draft_sources and self.translator:
            try:
                draft_text = " ".join(self._draft_sources)
                self._draft_translation = self.translator(draft_text) or ""
            except Exception as e:
                warning(f"TSM: Draft re-translation error: {e}")
        else:
            self._draft_translation = ""

    def _build_state(self) -> TranslationState:
        """Build the current translation state for display."""
        # Join paragraphs with single newline for tighter visual separation
        committed_text = "\n".join(self._committed_paragraphs)
        return TranslationState(committed_text=committed_text, draft_text=self._draft_translation)

    def pop_committed_batch(self) -> tuple[str, str] | None:
        """Pop the most recently committed (source, translation) batch.

        Returns the batch and clears it - each batch is consumed at most once.
        Returns None if nothing has been committed since the last pop.
        """
        batch = self._last_committed_batch
        self._last_committed_batch = None
        return batch

    def reset(self) -> None:
        """Reset all state."""
        self._committed_sources.clear()
        self._committed_paragraphs.clear()
        self._draft_sources.clear()
        self._draft_translation = ""
        self._last_processed_text = ""
        self._last_committed_batch = None

    def get_debug_info(self) -> dict:
        """Get debug information about current state."""
        return {
            "committed_sources": self._committed_sources.copy(),
            "committed_paragraphs": self._committed_paragraphs.copy(),
            "draft_sources": self._draft_sources.copy(),
            "draft_translation": self._draft_translation,
        }
