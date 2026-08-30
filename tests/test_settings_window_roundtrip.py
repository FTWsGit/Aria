"""Settings window save/restore round-trip test.

This guards against the specific class of bug found during the VAD
feature's review: a widget wired to `_persist_ui_settings()` on change, but
never actually read in `_gather_settings()`, or never restored in
`_load_saved_settings()` (the `vad_advanced_group` collapsible section was
shipped with exactly this gap — checked on toggle, saved nowhere, restored
nowhere).

Requires PyQt6. Runs headless via the "offscreen" Qt platform plugin — no
real display needed. Uses a temporary HOME so it never touches the
developer's real ~/.config/aria/settings.json.
"""

import pytest

pytest.importorskip("PyQt6")

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PyQt6.QtWidgets import QApplication

from aria.settings_manager import reset_for_test


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    """Point SettingsManager at a scratch dir and reset the singleton after."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    reset_for_test()
    yield
    reset_for_test()


def _new_window(qapp):
    from aria.ui.settings_window import SettingsWindow

    return SettingsWindow()


def test_settings_roundtrip_asr_mode(qapp, isolated_settings):
    """Every ASR/VAD/translation-tab widget survives a save -> reload cycle."""
    win = _new_window(qapp)

    # Recognition tab
    win.timezone_dropdown.setCurrentText("Asia/Tokyo")
    idx = win.audio_source_dropdown.findData(_mic_default_source())
    assert idx >= 0, "microphone default option must always be present"
    win.audio_source_dropdown.setCurrentIndex(idx)

    win.vad_checkbox.setChecked(True)
    win.vad_threshold_spin.setValue(0.77)
    win.vad_min_silence_spin.setValue(1.23)
    win.vad_min_speech_spin.setValue(0.44)
    win.vad_max_speech_spin.setValue(33.5)
    win.vad_split_punctuation_check.setChecked(False)
    win.vad_advanced_group.setChecked(True)  # the specific control that was broken

    vad_idx = win.vad_model_dropdown.findData("vad-ten-vad")
    if vad_idx >= 0:
        win.vad_model_dropdown.setCurrentIndex(vad_idx)

    # Translation tab
    win.trans_checkbox.setChecked(False)
    win.trans_engine_dropdown.setCurrentText(win.trans_engine_dropdown.itemText(0))
    win.translation_context_spin.setValue(4)
    win.openai_endpoint.setText("http://example.invalid:9999/v1")
    win.openai_api_key.setText("sk-test-roundtrip")
    win.openai_model_name.setText("test-model")
    win.openai_system_prompt.setText("test prompt")
    win.openai_temperature.setValue(1.1)
    win.openai_max_tokens.setValue(2048)

    expected = win._gather_settings()

    win.deleteLater()
    win2 = _new_window(qapp)
    restored = win2._gather_settings()

    # Every key _gather_settings() produces must round-trip unchanged. This
    # is the actual regression guard: if any widget's restore line is
    # missing, its value in `restored` silently falls back to a hardcoded
    # default here and this comparison catches it.
    mismatches = {k: (expected[k], restored[k]) for k in expected if expected[k] != restored[k]}
    assert not mismatches, f"settings failed to round-trip: {mismatches}"

    # Spot-check the exact control that was broken, directly on the widget
    # (not just via _gather_settings, in case gather itself were ever wrong).
    assert win2.vad_advanced_group.isChecked() is True


def test_settings_roundtrip_mode_switch(qapp, isolated_settings):
    """Switching to Live Captions mode persists across reload."""
    win = _new_window(qapp)
    win._on_mode_change("livecaptions")
    win._persist_ui_settings()

    win.deleteLater()
    win2 = _new_window(qapp)
    assert win2.mode_livecaptions_btn.isChecked() is True
    assert win2.mode_asr_btn.isChecked() is False


def _mic_default_source() -> str:
    from aria.audio.capture import AudioCapture

    return AudioCapture.MIC_DEFAULT_SOURCE
