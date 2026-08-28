from aria.translation.state_manager import TranslationStateManager


def fake_translator(text: str) -> str:
    """Mock translator that returns uppercase."""
    return text.upper()


# ---------------------------------------------------------------------------
# Existing tests (renamed)
# ---------------------------------------------------------------------------


def test_single_word_no_commit():
    """A single word is too short to trigger a commit."""
    manager = TranslationStateManager(translator=fake_translator)
    state = manager.process_text("hello")
    assert state.committed_text == ""
    assert state.draft_text == "HELLO"


def test_state_manager_reset():
    """reset() should clear state."""
    manager = TranslationStateManager(translator=fake_translator)
    manager.process_text("hello world")
    manager.reset()
    state = manager.process_text("hello")
    assert state.committed_text == ""


# ---------------------------------------------------------------------------
# New tests
# ---------------------------------------------------------------------------


def test_commit_mechanism():
    """Feed 6 sentences: DRAFT_COMMIT_THRESHOLD triggers, COMMIT_COUNT=4 committed."""
    manager = TranslationStateManager(translator=fake_translator)
    text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
    state = manager.process_text(text)

    assert state.committed_text != "", "Expected non-empty committed text"
    # COMMIT_COUNT=4 sentences should be committed, 2 remain as draft
    assert state.draft_text != "", "Expected non-empty draft text (remaining 2 sentences)"


def test_draft_accumulation():
    """Committed text should grow across multiple process_text calls."""
    manager = TranslationStateManager(translator=fake_translator)

    # First call: 6 sentences → 4 committed, 2 draft
    state1 = manager.process_text(
        "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
    )
    assert state1.committed_text != ""

    # Second call: same 4 committed + 6 new sentences → another commit batch
    text2 = (
        "First sentence. Second sentence. Third sentence. Fourth sentence. "
        "Fifth sentence. Sixth sentence. Seventh sentence. Eighth sentence. "
        "Ninth sentence. Tenth sentence."
    )
    state2 = manager.process_text(text2)
    # Committed should now have 2 paragraphs (4 + 4 sentences)
    assert "\n" in state2.committed_text, f"Expected at least 2 commit paragraphs, got: {state2.committed_text!r}"


def test_translator_exception():
    """Translator that raises → _draft_translation is empty, committed stays empty."""

    def failing_translator(_text: str) -> str:
        raise Exception("Simulated translator failure")

    manager = TranslationStateManager(translator=failing_translator)
    manager.process_text(
        "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
    )
    assert manager._draft_translation == ""
    assert manager._committed_paragraphs == []


def test_fuzzy_match():
    """Slightly modified text should still fuzzy-match committed sentences."""
    manager = TranslationStateManager(translator=fake_translator)

    # Build committed state: 4 committed, 2 draft
    manager.process_text(
        "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
    )

    # Feed slightly modified text (6th sentence has a typo)
    state = manager.process_text(
        "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentxnce."
    )
    # Fuzzy matching should still find the 4 committed sentences
    # Draft = only the 2 sentences after committed (the modified portion)
    assert "FIFTH SENTENCE" in state.draft_text
    assert "SIXTH SENTXNCE" in state.draft_text


def test_retranslate_committed():
    """Feeding completely different text triggers _retranslate_committed."""
    manager = TranslationStateManager(translator=fake_translator)

    # Build committed state
    manager.process_text(
        "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
    )
    assert len(manager._committed_sources) > 0, "Expected committed sources after first call"

    # Feed completely different text — no fuzzy match → committed trimmed
    manager.process_text("Completely different text. Nothing matches before.")
    # _committed_sources should be trimmed (decreased or cleared)
    assert len(manager._committed_sources) == 0, (
        f"Expected committed sources to be cleared, got {len(manager._committed_sources)}"
    )
    assert manager._committed_paragraphs == []


def test_max_draft_sentences_skip():
    """Draft > MAX_DRAFT_SENTENCES(8) → excess skipped, draft capped at 8."""
    manager = TranslationStateManager(translator=fake_translator)

    # First build committed state so the safeguard doesn't truncate input
    manager.process_text(
        "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
    )
    # Now committed has 4 sentences, draft has 2

    # Feed the same 4 committed + 10 new sentences → draft = 10 sentences
    # 10 > MAX_DRAFT_SENTENCES(8) → skip 2, draft = 8
    # Then _check_commit_threshold commits 4 → draft = 4
    text = (
        "First sentence. Second sentence. Third sentence. Fourth sentence. "
        "Fifth sentence. Sixth sentence. Seventh sentence. Eighth sentence. "
        "Ninth sentence. Tenth sentence. Eleventh sentence. Twelfth sentence. "
        "Thirteenth sentence. Fourteenth sentence."
    )
    manager.process_text(text)

    # After MAX_DRAFT_SENTENCES skip + commit, draft should be ≤ 8
    assert len(manager._draft_sources) <= 8, f"Expected draft <= 8, got {len(manager._draft_sources)}"
