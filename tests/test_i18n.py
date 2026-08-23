from unittest.mock import MagicMock, patch

import aria.i18n
from aria.i18n.en import TRANSLATIONS as EN
from aria.i18n.zh_CN import TRANSLATIONS as ZH_CN


def test_i18n_keys_aligned():
    """zh_CN and en should have exactly the same keys."""
    zh_keys = set(ZH_CN.keys())
    en_keys = set(EN.keys())
    missing_in_en = zh_keys - en_keys
    missing_in_zh = en_keys - zh_keys
    assert not missing_in_en, f"Keys in zh_CN but missing in en: {missing_in_en}"
    assert not missing_in_zh, f"Keys in en but missing in zh_CN: {missing_in_zh}"


def test_i18n_t_basic():
    """t() should return translated text for known keys."""
    # Reset globals to avoid state leakage from other tests
    aria.i18n._current_language = None
    aria.i18n._translations = {}

    with patch("aria.i18n.get_settings_manager", return_value=MagicMock()):
        set_language = aria.i18n.set_language
        t = aria.i18n.t

        set_language("zh_CN")
        assert t("window_title") == "ARIA"

        set_language("en")
        assert t("window_title") == "ARIA"


def test_i18n_t_fallback():
    """t() should return key itself for unknown keys."""
    # Reset globals — this test is independent of test_i18n_t_basic
    aria.i18n._current_language = None
    aria.i18n._translations = {}

    with patch("aria.i18n.get_settings_manager", return_value=MagicMock()):
        t = aria.i18n.t
        assert t("nonexistent_key_xyz") == "nonexistent_key_xyz"
