import json
from pathlib import Path
from unittest.mock import patch

from aria.settings_manager import SettingsManager


def test_default_settings():
    """SettingsManager should start with default values."""
    with patch.object(SettingsManager, "_load", return_value=None):
        sm = SettingsManager.__new__(SettingsManager)
        sm._config_dir = Path("/tmp/aria")
        sm._config_file = sm._config_dir / "settings.json"
        sm._settings = sm.DEFAULT_SETTINGS.copy()

        assert sm.get("mode") == "realtime"
        assert sm.get("openai_max_tokens") == 1024
        assert sm.get("overlay_visible") is True


def test_settings_merge_defaults(tmp_path):
    """Loading should merge saved values with defaults for missing keys."""
    config_dir = tmp_path / ".config" / "aria"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "settings.json"
    # Only save one key, others should come from defaults
    config_file.write_text(json.dumps({"mode": "livecaptions"}), encoding="utf-8")

    sm = SettingsManager.__new__(SettingsManager)
    sm._config_dir = config_dir
    sm._config_file = config_file
    sm._settings = sm.DEFAULT_SETTINGS.copy()
    sm._load()

    assert sm.get("mode") == "livecaptions"
    # Default should still be present for keys not in saved file
    assert sm.get("openai_max_tokens") == 1024


def test_settings_set_and_get(tmp_path):
    """set() and get() should work correctly."""
    with patch.object(SettingsManager, "_load", return_value=None):
        sm = SettingsManager.__new__(SettingsManager)
        sm._config_dir = tmp_path / ".config" / "aria"
        sm._config_file = sm._config_dir / "settings.json"
        sm._settings = sm.DEFAULT_SETTINGS.copy()

        sm.set("mode", "livecaptions")
        assert sm.get("mode") == "livecaptions"
        assert sm.get("nonexistent", "default") == "default"
