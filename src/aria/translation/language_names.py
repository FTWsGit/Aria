"""NLLB language code to human-readable name mapping.

Shared between UI (settings_window) and translation engines (OpenAITranslator)
so that NLLB codes like "zho_Hans" are rendered as "简体中文" / "Simplified Chinese"
in prompts and UI, rather than being passed through as opaque codes.
"""

from ..i18n import t
from ..logger import warning

# NLLB code -> i18n key for human-readable name
_NLLB_TO_I18N_KEY = {
    "zho_Hant": "target_zh_TW",
    "zho_Hans": "target_zh_CN",
    "eng_Latn": "target_en",
    "jpn_Jpan": "target_ja",
    "kor_Hang": "target_ko",
    "spa_Latn": "target_es",
    "fra_Latn": "target_fr",
    "deu_Latn": "target_de",
}


def nllb_code_to_name(nllb_code: str) -> str:
    """Convert an NLLB language code to a human-readable name.

    Args:
        nllb_code: NLLB format code like "zho_Hans", "eng_Latn"

    Returns:
        Human-readable name in current UI language (e.g. "简体中文" or "Simplified Chinese").
        Falls back to the raw code with a warning if no mapping is found.
    """
    if key := _NLLB_TO_I18N_KEY.get(nllb_code):
        return t(key)
    warning(f"Unknown NLLB language code '{nllb_code}', using raw code as fallback")
    return nllb_code


def get_target_language_options() -> list[tuple[str, str]]:
    """Return (display_name, nllb_code) pairs for UI dropdowns."""
    return [(t(key), code) for code, key in _NLLB_TO_I18N_KEY.items()]
