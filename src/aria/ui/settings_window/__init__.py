"""
Main Settings Window for ARIA using PyQt6.

A modern, beautiful settings interface.
"""

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...i18n import LANGUAGES, get_current_language, set_language, t
from ...settings_manager import get_settings_manager
from ...timezone_utils import validate_timezone_name
from ..styles import MAIN_STYLESHEET
from .general_tab import GeneralTabMixin
from .recognition_tab import RecognitionTabMixin
from .translation_tab import TranslationTabMixin


class SettingsWindow(QMainWindow, RecognitionTabMixin, TranslationTabMixin, GeneralTabMixin):
    """Main settings window with model selection, language, VAD options, etc."""

    # Model options
    LANGUAGE_CODES = [None, "zh", "en", "ja", "ko", "yue", "es", "fr", "de"]

    @staticmethod
    def _get_asr_languages():
        """Get available languages for asr mode."""
        return [
            ("中/英文", "zh"),
            ("日文", "ja"),
        ]

    @staticmethod
    def _get_streaming_model_for_language(lang_code: str) -> str:
        """Get the streaming model ID for a language."""
        if lang_code in ["zh", "en"]:
            return "sherpa-zh-en"
        elif lang_code == "ja":
            return "vosk-ja"
        return "sherpa-zh-en"

    @staticmethod
    def _get_languages():
        """Get languages list with translated display names."""
        return [
            (t("auto_detect"), None),
            ("中文（简体）", "zh_hans"),
            ("中文（繁体）", "zh_hant"),
            (t("lang_english"), "en"),
            (t("lang_japanese"), "ja"),
            (t("lang_korean"), "ko"),
            (t("lang_cantonese"), "yue"),
            (t("lang_spanish"), "es"),
            (t("lang_french"), "fr"),
            (t("lang_german"), "de"),
            (t("lang_russian"), "ru"),
        ]

    @property
    def asr_LANGUAGES(self):
        return self._get_asr_languages()

    @property
    def LANGUAGES(self):
        return self._get_languages()

    def __init__(
        self,
        on_quit: Callable[[], None] | None = None,
        on_toggle_overlay: Callable[[], bool] | None = None,
    ):
        """Initialize the settings window.

        Args:
            on_quit: Callback when user clicks Quit.
            on_toggle_overlay: Callback to toggle the subtitle overlay's visibility.

        Note: starting/stopping transcription now lives in ConsoleWindow;
        call `get_settings()` to read the current form values instead.
        """
        super().__init__()

        self.on_quit = on_quit
        self.on_toggle_overlay = on_toggle_overlay
        self._loading = True

        # Window setup. Qt.WindowType.Tool keeps this out of the taskbar —
        # ConsoleWindow (not this window) is the app's main/taskbar window.
        self.setWindowTitle(t("settings_window_title"))
        self.setWindowFlags(Qt.WindowType.Tool)
        self.setMinimumSize(820, 620)
        self.resize(860, 700)
        self.setStyleSheet(self._get_stylesheet())

        # Center on screen
        self._center_on_screen()

        # Create UI
        self._create_ui()

        # Load saved settings
        self._load_saved_settings()
        self._loading = False

    def _center_on_screen(self):
        """Center window on screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _get_stylesheet(self):
        """Return the main stylesheet: a plain, light Windows-style theme."""
        return MAIN_STYLESHEET

    def _create_ui(self):
        """Create all UI components."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === Header (fixed, not scrollable) ===
        header = self._create_header()
        header.setContentsMargins(20, 20, 20, 10)
        main_layout.addWidget(header)

        # === Tabbed content area ===
        self.tabs = QTabWidget()

        self.tabs.addTab(
            self._create_tab_page([self._create_recognition_card(), self._create_model_card()]),
            t("tab_recognition"),
        )
        self.tabs.addTab(self._create_tab_page([self._create_translation_card()]), t("tab_translation"))
        self.tabs.addTab(self._create_tab_page([self._create_reset_card()]), t("tab_general"))

        main_layout.addWidget(self.tabs)

        # === OpenAI config overlay (hidden by default) ===
        self._create_openai_overlay(central)

    def _create_tab_page(self, cards: list) -> QScrollArea:
        """Wrap a list of setting cards in a scrollable tab page."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        content = QWidget()
        content.setStyleSheet("background-color: #ffffff;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(15)
        for card in cards:
            layout.addWidget(card)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _create_header(self):
        """Create header with title and language selector."""
        header = QFrame()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        # Left spacer (same width as language selector for balance)
        left_spacer = QWidget()
        left_spacer.setFixedWidth(210)
        layout.addWidget(left_spacer)

        # Spacer
        layout.addStretch()

        # Title (centered)
        title_container = QVBoxLayout()

        title = QLabel("ARIA")
        title.setFont(QFont("", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_container.addWidget(title)

        subtitle = QLabel(t("subtitle"))
        subtitle.setStyleSheet("color: #666666; font-size: 12px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_container.addWidget(subtitle)

        layout.addLayout(title_container)

        # Spacer
        layout.addStretch()

        # Language selector (right side)
        self.lang_selector = QComboBox()
        lang_options = [LANGUAGES[code][0] for code in LANGUAGES]
        self.lang_selector.addItems(lang_options)
        current_lang = get_current_language()
        current_lang_name = LANGUAGES.get(current_lang, LANGUAGES["zh_CN"])[0]
        self.lang_selector.setCurrentText(current_lang_name)
        self.lang_selector.currentTextChanged.connect(self._on_ui_language_change)
        self.lang_selector.setFixedWidth(120)
        layout.addWidget(self.lang_selector)

        return header

    def _create_card(self, title: str) -> tuple:
        """Create a card frame with title. Returns (frame, content_layout)."""
        frame = QFrame()
        frame.setObjectName("card")
        frame.setMaximumWidth(400)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(12)

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("", 13, QFont.Weight.Bold))
        layout.addWidget(title_label)

        return frame, layout

    def resizeEvent(self, event):
        """Reposition overlay when window resizes."""
        super().resizeEvent(event)
        if hasattr(self, "openai_overlay") and self.openai_overlay.isVisible():
            self.openai_overlay.setGeometry(self.tabs.geometry())

    def showEvent(self, event):
        """Reposition overlay on first show."""
        super().showEvent(event)
        if hasattr(self, "openai_overlay") and self.openai_overlay.isVisible():
            self.openai_overlay.setGeometry(self.tabs.geometry())

    # === Event Handlers ===

    def _on_toggle_overlay(self):
        """Toggle subtitle overlay visibility."""
        if not self.on_toggle_overlay:
            return
        is_visible = self.on_toggle_overlay()
        self.overlay_toggle_button.setText(t("overlay_hide") if is_visible else t("overlay_show"))

    def _on_ui_language_change(self, lang_display: str):
        """Handle UI language change."""
        lang_code = None
        for code, (name, _) in LANGUAGES.items():
            if name == lang_display:
                lang_code = code
                break

        if lang_code and lang_code != get_current_language():
            set_language(lang_code)
            QMessageBox.information(self, t("restart_required"), t("restart_required"))

    def get_settings(self) -> dict:
        """Public accessor for ConsoleWindow's start button: current form values."""
        return self._gather_settings()

    def _persist_ui_settings(self) -> None:
        """Persist current UI selections without starting."""
        if self._loading:
            return
        self._gather_settings()

    def _gather_settings(self) -> dict:
        """Gather current settings into a dictionary."""
        mode = "livecaptions" if self.mode_livecaptions_btn.isChecked() else "asr"

        if mode == "livecaptions":
            model_id = None
            lang_code = None
        else:
            lang_code = None
            idx = self.model_dropdown.currentIndex()
            if idx >= 0:
                model_id = self.model_dropdown.itemData(idx) or "sherpa-zh-en-zipformer"
            else:
                model_id = "sherpa-zh-en-zipformer"

        target_lang = self._get_target_language_code()

        engine_display = self.trans_engine_dropdown.currentText()
        engine_map = {
            t("engine_openai"): "openai",
            t("engine_google_free"): "google_free",
            t("engine_bing"): "bing",
            t("engine_youdao"): "youdao",
        }
        engine = engine_map.get(engine_display, "bing")
        tz_name = self.timezone_dropdown.currentText().strip() or "system"
        if not validate_timezone_name(tz_name):
            tz_name = "system"

        settings = {
            "mode": mode,
            "model_id": model_id,
            "language": lang_code,
            "timezone": tz_name,
            "enable_translation": self.trans_checkbox.isChecked(),
            "translation_engine": engine,
            "target_language": target_lang,
            "audio_source": self._get_selected_audio_source(),
        }

        settings.update(
            {
                "openai_endpoint": self.openai_endpoint.text().strip(),
                "openai_api_key": self.openai_api_key.text().strip(),
                "openai_model_name": self.openai_model_name.text().strip(),
                "openai_temperature": self.openai_temperature.value(),
                "openai_max_tokens": self.openai_max_tokens.value(),
                "openai_system_prompt": self.openai_system_prompt.text().strip(),
            }
        )

        self._save_settings(settings)

        return settings

    def _get_target_language_code(self) -> str:
        """Get target language code from dropdown."""
        return self.target_lang_dropdown.currentData() or "zho_Hant"

    def _save_settings(self, settings: dict):
        """Save settings to file."""
        sm = get_settings_manager()
        for key, value in settings.items():
            sm.set(key, value)
        sm.save()

    def _load_saved_settings(self):
        """Load saved settings from previous session."""
        sm = get_settings_manager()

        mode = sm.get("mode", "asr")
        if mode in ["實時", "asr", "精準", "precise"]:
            mode = "asr"
        self._on_mode_change(mode)

        model_id = sm.get("model_id", "sherpa-zh-en-zipformer")
        idx = self.model_dropdown.findData(model_id)
        if idx >= 0:
            self.model_dropdown.setCurrentIndex(idx)

        self.trans_checkbox.setChecked(sm.get("enable_translation", False))

        engine = sm.get("translation_engine", "bing")
        engine_reverse_map = {
            "openai": t("engine_openai"),
            "google_free": t("engine_google_free"),
            "bing": t("engine_bing"),
            "youdao": t("engine_youdao"),
            "google": t("engine_google_free"),
            "baidu": t("engine_bing"),
            "alibaba": t("engine_bing"),
            "nllb": t("engine_bing"),
        }
        display_name = engine_reverse_map.get(engine, t("engine_bing"))
        self.trans_engine_dropdown.setCurrentText(display_name)
        self._on_engine_change(display_name)

        target = sm.get("target_language", "zho_Hant")
        from ...translation.language_names import nllb_code_to_name

        display_name = nllb_code_to_name(target)
        idx = self.target_lang_dropdown.findText(display_name)
        if idx >= 0:
            self.target_lang_dropdown.setCurrentIndex(idx)

        tz_name = sm.get("timezone", "system") or "system"
        if not validate_timezone_name(tz_name):
            tz_name = "system"
        self.timezone_dropdown.setCurrentText(tz_name)

        audio_source = sm.get("audio_source", "system")
        self._populate_audio_source_dropdown(preferred_source=audio_source)

        overlay_visible = sm.get("overlay_visible", True)
        self.overlay_toggle_button.setText(t("overlay_hide") if overlay_visible else t("overlay_show"))

        self.openai_endpoint.setText(sm.get("openai_endpoint", "http://127.0.0.1:1234/v1"))
        self.openai_api_key.setText(sm.get("openai_api_key", ""))
        self.openai_model_name.setText(sm.get("openai_model_name", ""))
        self.openai_temperature.setValue(sm.get("openai_temperature", 0.2))
        self.openai_max_tokens.setValue(sm.get("openai_max_tokens", 1024))
        self.openai_system_prompt.setText(sm.get("openai_system_prompt", ""))
