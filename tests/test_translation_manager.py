from aria.livecaptions.manager import TranslationStateManager


def fake_translator(text: str) -> str:
    """Mock translator that returns uppercase."""
    return text.upper()


def test_state_manager_committed():
    """Committed text should accumulate as input grows."""
    manager = TranslationStateManager(translator=fake_translator)
    state = manager.process_text("hello")
    # First call, nothing committed yet (too short)
    assert state.committed_text == ""
    assert state.draft_text == "HELLO"


def test_state_manager_reset():
    """reset() should clear state."""
    manager = TranslationStateManager(translator=fake_translator)
    manager.process_text("hello world")
    manager.reset()
    state = manager.process_text("hello")
    assert state.committed_text == ""
