"""
Sentence segmentation shared by translation-less transcription and
`livecaptions.manager.TranslationStateManager`.

Splits a continuously-growing text stream into sentence batches using
punctuation heuristics. This is a stand-in for proper VAD-based utterance
boundaries (tracked separately); once VAD lands, its endpoint signal can
replace the punctuation trigger without changing the batch/message shape
consumed by callers.
"""

import re
from dataclasses import dataclass, field

# Sentence delimiters: standard punctuation plus commas, since long
# comma-joined clauses read poorly as a single console line.
SENTENCE_DELIMITERS = r"[.。？！?!\n，,、]"
MAX_SENTENCE_LENGTH = 80  # Force split if a single sentence exceeds this

# Buffer thresholds (mirrors TranslationStateManager's tuning).
DRAFT_COMMIT_THRESHOLD = 6
COMMIT_COUNT = 4
DRAFT_CHAR_THRESHOLD = 150


def segment_sentences(text: str) -> list[str]:
    """Split text into sentences, force-splitting overly long ones."""
    if not text:
        return []

    sentences = []
    for part in re.split(SENTENCE_DELIMITERS, text):
        part = part.strip()
        if not part:
            continue
        if len(part) > MAX_SENTENCE_LENGTH:
            for i in range(0, len(part), MAX_SENTENCE_LENGTH):
                chunk = part[i : i + MAX_SENTENCE_LENGTH].strip()
                if chunk:
                    sentences.append(chunk)
        else:
            sentences.append(part)
    return sentences


@dataclass
class PlainSentenceSegmenter:
    """Batches a growing raw-text stream into committed sentence groups.

    Used when translation is disabled, so the console history still gets
    discrete messages instead of one line growing forever. Mirrors
    `TranslationStateManager`'s commit heuristic but without any
    translation step.
    """

    _committed_count: int = field(default=0, init=False)
    _draft_sources: list[str] = field(default_factory=list, init=False)
    _last_text: str = field(default="", init=False)

    def process_text(self, full_text: str) -> str | None:
        """Feed the latest full raw text; return a newly committed batch, if any."""
        if full_text == self._last_text:
            return None
        self._last_text = full_text

        sentences = segment_sentences(full_text)
        if len(sentences) <= self._committed_count:
            return None

        self._draft_sources = sentences[self._committed_count :]

        total = len(self._draft_sources)
        char_len = sum(len(s) for s in self._draft_sources)
        if total < DRAFT_COMMIT_THRESHOLD and char_len < DRAFT_CHAR_THRESHOLD:
            return None

        commit_target = COMMIT_COUNT if total >= COMMIT_COUNT else max(1, total - 1)
        to_commit = self._draft_sources[:commit_target]
        self._committed_count += len(to_commit)
        return " ".join(to_commit)

    def pending_draft(self) -> str:
        """Return the current uncommitted tail (for a live/in-progress line)."""
        return " ".join(self._draft_sources)

    def reset(self) -> None:
        self._committed_count = 0
        self._draft_sources = []
        self._last_text = ""
