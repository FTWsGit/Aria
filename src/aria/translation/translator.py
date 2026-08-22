"""Translation module for ARIA."""

import threading

from ..logger import debug, info, warning

# Translators library import (multi-engine web scraper) - delayed to avoid conflicts
TRANSLATORS_AVAILABLE = False
try:
    import importlib.util

    if importlib.util.find_spec("translators") is not None:
        TRANSLATORS_AVAILABLE = True
        debug("translators library available (delayed import)")
except Exception as e:
    warning(f"translators check failed: {e}")


class TranslatorsLibWrapper:
    """
    Wrapper for translators library (multi-engine web scraper).
    Supports Google, Baidu, Youdao, Bing, Alibaba, and more.

    Warning: This uses web scraping and may be unstable or blocked.
    """

    # Language code mapping (NLLB format -> translators format)
    # Different engines may use different codes
    LANGUAGE_CODES = {
        # Google and most engines
        "google": {
            "zho_Hant": "zh-TW",
            "zho_Hans": "zh-CN",
            "eng_Latn": "en",
            "jpn_Jpan": "ja",
            "kor_Hang": "ko",
            "spa_Latn": "es",
            "fra_Latn": "fr",
            "deu_Latn": "de",
            "rus_Cyrl": "ru",
            "arb_Arab": "ar",
            "por_Latn": "pt",
            "ita_Latn": "it",
            "vie_Latn": "vi",
            "tha_Thai": "th",
            "ind_Latn": "id",
        },
        # Bing uses different codes
        "bing": {
            "zho_Hant": "zh-Hant",
            "zho_Hans": "zh-Hans",
            "eng_Latn": "en",
            "jpn_Jpan": "ja",
            "kor_Hang": "ko",
            "spa_Latn": "es",
            "fra_Latn": "fr",
            "deu_Latn": "de",
            "rus_Cyrl": "ru",
            "arb_Arab": "ar",
            "por_Latn": "pt",
            "ita_Latn": "it",
            "vie_Latn": "vi",
            "tha_Thai": "th",
            "ind_Latn": "id",
        },
        # Youdao only supports Chinese-English translation
        "youdao": {
            "zho_Hant": "zh-CHS",  # Only simplified Chinese supported
            "zho_Hans": "zh-CHS",
            "eng_Latn": "en",
            "jpn_Jpan": "en",  # Other languages fallback to English
            "kor_Hang": "en",
            "spa_Latn": "en",
            "fra_Latn": "en",
            "deu_Latn": "en",
            "rus_Cyrl": "en",
            "arb_Arab": "en",
            "por_Latn": "en",
            "ita_Latn": "en",
            "vie_Latn": "en",
            "tha_Thai": "en",
            "ind_Latn": "en",
        },
    }

    # Supported engines
    ENGINES = {
        "google": "Google (Free)",
        "bing": "Bing",
        "youdao": "有道翻譯 (中英互譯)",
    }

    def __init__(
        self,
        engine: str = "google",
        target_language: str = "zho_Hant",
    ):
        """
        Initialize translators library wrapper.

        Args:
            engine: Engine name ("google", "baidu", "youdao", "bing", "alibaba")
            target_language: Target language code (NLLB format)
        """
        if not TRANSLATORS_AVAILABLE:
            raise ImportError("translators library is required. Run: pip install translators")

        self.engine = engine
        # Get language code based on engine
        lang_map = self.LANGUAGE_CODES.get(engine, self.LANGUAGE_CODES["google"])
        self.target_language = lang_map.get(target_language, "zh-TW")
        self._lock = threading.Lock()

        info(f"TranslatorsLib initialized: engine={engine}, target={self.target_language}")

    def translate(
        self,
        text: str,
        source_language: str | None = None,
        target_language: str | None = None,
    ) -> str:
        """
        Translate text using selected engine.

        Args:
            text: Text to translate
            source_language: Source language code (optional, auto-detect)
            target_language: Target language code (overrides default)

        Returns:
            Translated text
        """
        if not text or not text.strip():
            return ""

        target = target_language or self.target_language

        # Lazy import translators to avoid conflicts
        import translators as ts

        with self._lock:
            try:
                # Map engine name to translators library function
                if self.engine == "google":
                    result = ts.translate_text(text, to_language=target, translator="google")
                elif self.engine == "bing":
                    result = ts.translate_text(text, to_language=target, translator="bing")
                elif self.engine == "youdao":
                    result = ts.translate_text(text, to_language=target, translator="youdao")
                else:
                    warning(f"Unknown engine: {self.engine}, falling back to Google")
                    result = ts.translate_text(text, to_language=target, translator="google")

                return result
            except Exception as e:
                warning(f"TranslatorsLib ({self.engine}) error: {e}")
                return ""

    def set_target_language(self, language: str) -> None:
        """Set the target language."""
        lang_map = self.LANGUAGE_CODES.get(self.engine, self.LANGUAGE_CODES["google"])
        self.target_language = lang_map.get(language, language)
        debug(f"TranslatorsLib target language set to: {self.target_language}")

    @classmethod
    def get_language_code(cls, nllb_code: str, engine: str = "google") -> str:
        """Get translators language code from NLLB code."""
        lang_map = cls.LANGUAGE_CODES.get(engine, cls.LANGUAGE_CODES["google"])
        return lang_map.get(nllb_code, "en")


def create_translator(engine: str = "bing", target_language: str = "zho_Hant", **kwargs):
    """
    Factory function to create a translator instance.

    Args:
        engine: "google_free", "bing", "youdao", "google", or "openai"
        target_language: Target language code (NLLB format like "zho_Hant")
        **kwargs: Additional arguments for specific translator

    Returns:
        Translator instance
    """

    if engine in ["google_free", "bing", "youdao", "google"]:
        if not TRANSLATORS_AVAILABLE:
            raise ImportError("translators library not available. Install: pip install translators")
        engine_map = {"google": "google", "google_free": "google", "bing": "bing", "youdao": "youdao"}
        ts_engine = engine_map.get(engine, "google")
        return TranslatorsLibWrapper(engine=ts_engine, target_language=target_language)
    elif engine == "openai":
        from .openai_translator import OpenAITranslator

        return OpenAITranslator(
            endpoint=kwargs.get("openai_endpoint", "http://127.0.0.1:1234/v1"),
            api_key=kwargs.get("openai_api_key") or None,
            model_name=kwargs.get("openai_model_name", ""),
            target_language=target_language,
            temperature=kwargs.get("openai_temperature", 0.2),
            max_tokens=kwargs.get("openai_max_tokens", 1024),
            system_prompt=kwargs.get("openai_system_prompt") or None,
        )
    else:
        raise ValueError(f"Unknown translation engine: {engine}")



