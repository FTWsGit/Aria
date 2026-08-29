"""
Main Settings Window for ARIA using PyQt6.

A native Windows-style settings interface.
"""

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...i18n import LANGUAGES, get_current_language, set_language, t
from ...settings_manager import get_settings_manager
from ...timezone_utils import validate_timezone_name
from .general_tab import GeneralTabMixin
from .model_tab import ModelTabMixin
from .recognition_tab import RecognitionTabMixin
from .translation_tab import TranslationTabMixin


class SettingsWindow(QMainWindow, ModelTabMixin, RecognitionTabMixin, TranslationTabMixin, GeneralTabMixin):
    """Main settings window with one functional domain per tab."""

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
        self.setMinimumSize(520, 500)
        self.resize(520, 600)

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
        header.setContentsMargins(10, 8, 10, 5)
        main_layout.addWidget(header)

        # === Tabbed content area: one functional domain per tab ===
        self.tabs = QTabWidget()

        self.tabs.addTab(self._create_recognition_tab(), t("tab_recognition"))
        self.tabs.addTab(self._create_model_tab(), t("tab_models"))
        self.tabs.addTab(self._create_translation_tab(), t("tab_translation"))
        self.tabs.addTab(self._create_general_tab(), t("tab_general"))

        main_layout.addWidget(self.tabs)

        # === OpenAI config overlay (hidden by default) ===
        self._create_openai_overlay(central)

    def _create_header(self):
        """Create a minimal header with language selector."""
        header = QFrame()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addStretch()

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
            model_id = self.model_dropdown.itemData(idx) if idx >= 0 else None

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

        # VAD settings
        if mode == "livecaptions":
            settings["enable_vad"] = False
        else:
            settings["enable_vad"] = self.vad_checkbox.isChecked()
            idx = self.vad_model_dropdown.currentIndex()
            settings["vad_model_id"] = self.vad_model_dropdown.itemData(idx) if idx >= 0 else "vad-silero-v5"
            settings["vad_threshold"] = self.vad_threshold_spin.value()
            settings["vad_min_silence_duration"] = self.vad_min_silence_spin.value()
            settings["vad_min_speech_duration"] = self.vad_min_speech_spin.value()
            settings["vad_max_speech_duration"] = self.vad_max_speech_spin.value()
            settings["vad_split_by_punctuation"] = self.vad_split_punctuation_check.isChecked()
            settings["vad_advanced_expanded"] = self.vad_advanced_group.isChecked()

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

        model_id = sm.get("model_id")
        if model_id:
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

        # VAD settings
        self.vad_checkbox.setChecked(sm.get("enable_vad", False))
        vad_model_id = sm.get("vad_model_id", "vad-silero-v5")
        self._populate_vad_model_dropdown()
        idx = self.vad_model_dropdown.findData(vad_model_id)
        if idx >= 0:
            self.vad_model_dropdown.setCurrentIndex(idx)
        self.vad_threshold_spin.setValue(sm.get("vad_threshold", 0.5))
        self.vad_min_silence_spin.setValue(sm.get("vad_min_silence_duration", 0.5))
        self.vad_min_speech_spin.setValue(sm.get("vad_min_speech_duration", 0.25))
        self.vad_max_speech_spin.setValue(sm.get("vad_max_speech_duration", 20.0))
        self.vad_split_punctuation_check.setChecked(sm.get("vad_split_by_punctuation", True))
        self.vad_advanced_group.setChecked(sm.get("vad_advanced_expanded", False))
        self._update_vad_controls_visibility()
