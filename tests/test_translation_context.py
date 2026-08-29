"""
Tests for context-aware translation (translation_context_sentences).

Does not depend on Qt, audio devices, network, or model files.
"""

import sys
import types

from aria.translation import translator as translator_mod
from aria.translation.openai_translator import OpenAITranslator
from aria.translation.state_manager import TranslationStateManager
from aria.translation.translation_layer import OpenAIConfig, TranslationLayer


class RecordingTranslator:
    """Fake translator recording every (text, kwargs) pair per call."""

    def __init__(self, target_lang: str = "zh"):
        self.target_language = target_lang
        self.calls: list[tuple[str, dict]] = []

    def translate(self, text: str, **kwargs) -> str:
        self.calls.append((text, kwargs))
        return text.upper()


def _make_layer(context_sentences: int, translator) -> TranslationLayer:
    layer = TranslationLayer(
        enable_translation=True,
        translation_engine="google",
        target_language="zh",
        openai_config=OpenAIConfig(),
        on_message=None,
        context_sentences=context_sentences,
    )
    # Swap in the fake translator (real engines would hit the network)
    object.__setattr__(layer, "_translator", translator)
    object.__setattr__(layer, "_state_manager", None)
    return layer


# ---------------------------------------------------------------------------
# VAD path: TranslationLayer.process_committed_sentence
# ---------------------------------------------------------------------------


def test_context_disabled_matches_legacy_behavior():
    """context_sentences=0: translator is called exactly like before (no
    context kwarg), results unchanged, and no window state accumulates."""
    translator = RecordingTranslator()
    layer = _make_layer(context_sentences=0, translator=translator)

    result1 = layer.process_committed_sentence("hello")
    result2 = layer.process_committed_sentence("world")

    assert result1.committed_text == "HELLO"
    assert result1.batch == ("hello", "HELLO")
    assert result2.committed_text == "WORLD"
    assert result2.batch == ("world", "WORLD")
    assert translator.calls == [("hello", {}), ("world", {})]
    assert layer._context_window == []


def test_context_is_recent_committed_sources_excluding_current():
    """With context_sentences=2, each sentence receives the last N committed
    source sentences as context; the current sentence is never in its own
    context."""
    translator = RecordingTranslator()
    layer = _make_layer(context_sentences=2, translator=translator)

    layer.process_committed_sentence("s1")
    layer.process_committed_sentence("s2")
    layer.process_committed_sentence("s3")

    contexts = [kwargs.get("context") for _text, kwargs in translator.calls]
    assert contexts[0] is None, "First sentence has no previously committed context"
    assert contexts[1] == ["s1"]
    assert contexts[2] == ["s1", "s2"], "Current sentence must not appear in its own context"

    # Window keeps only the last N sentences
    assert layer._context_window == ["s2", "s3"]


def test_layer_reset_clears_context_window():
    """reset() clears the rolling window so a new session starts clean."""
    translator = RecordingTranslator()
    layer = _make_layer(context_sentences=2, translator=translator)

    layer.process_committed_sentence("s1")
    layer.reset()
    assert layer._context_window == []

    layer.process_committed_sentence("s2")
    assert translator.calls[-1][1].get("context") is None


# ---------------------------------------------------------------------------
# Engine interface
# ---------------------------------------------------------------------------


def test_translators_lib_wrapper_accepts_and_ignores_context(monkeypatch):
    """TranslatorsLibWrapper accepts the context argument for interface
    uniformity but ignores it (no error, same result)."""
    fake_ts = types.ModuleType("translators")

    def fake_translate_text(text, to_language=None, translator=None):
        return f"[{translator}:{text}]"

    fake_ts = types.SimpleNamespace(translate_text=fake_translate_text)
    monkeypatch.setitem(sys.modules, "translators", fake_ts)
    monkeypatch.setattr(translator_mod, "TRANSLATORS_AVAILABLE", True)

    wrapper = translator_mod.TranslatorsLibWrapper(engine="google", target_language="zho_Hans")
    assert wrapper.translate("hello") == "[google:hello]"
    assert wrapper.translate("hello", context=["previous sentence"]) == "[google:hello]"


def test_openai_translator_injects_context_as_reference_only_system_message():
    """OpenAI engine: context becomes an extra system message before the user
    turn; without context the message list is unchanged (system + user)."""
    translator = OpenAITranslator(endpoint="http://127.0.0.1:1/v1", model_name="m")

    captured: list[dict] = []

    def fake_create(**kwargs):
        captured.append(kwargs)
        message = types.SimpleNamespace(content=" TRANSLATED ")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    object.__setattr__(
        translator,
        "client",
        types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))),
    )

    result = translator.translate("hello", context=["prev one", "prev two"])
    assert result == "TRANSLATED"

    messages = captured[0]["messages"]
    assert [m["role"] for m in messages] == ["system", "system", "user"]
    assert "prev one" in messages[1]["content"]
    assert "prev two" in messages[1]["content"]
    assert messages[2]["content"] == "hello"

    translator.translate("hello")
    assert [m["role"] for m in captured[1]["messages"]] == ["system", "user"]


# ---------------------------------------------------------------------------
# Legacy path: TranslationStateManager context penetration
# ---------------------------------------------------------------------------


def test_state_manager_passes_committed_sources_as_context():
    """Legacy path: draft translation, commit batch translation, and draft
    re-translation carry the last N committed source sentences as context."""
    calls: list[tuple[str, list[str] | None]] = []

    def recording_translator(text: str, context: list[str] | None = None) -> str:
        calls.append((text, context))
        return text.upper()

    manager = TranslationStateManager(translator=recording_translator, context_sentences=2)
    manager.process_text(
        "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
    )

    # Call 1: initial full-draft translation — nothing committed yet
    assert calls[0][1] is None
    # Call 2: commit batch translation — context snapshot taken before extend
    assert calls[1][1] is None
    # Call 3: remaining-draft re-translation — last 2 committed sources
    # (segmenter strips trailing punctuation, hence no periods)
    assert calls[2][1] == ["Third sentence", "Fourth sentence"]
    # The committed batch itself must not appear in its own context
    assert "First sentence" not in (calls[1][1] or [])

    # Next update: draft translation carries the last 2 committed sources
    calls.clear()
    manager.process_text(
        "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. "
        "Sixth sentence. Seventh sentence."
    )
    assert len(calls) == 1
    assert calls[0][1] == ["Third sentence", "Fourth sentence"]
