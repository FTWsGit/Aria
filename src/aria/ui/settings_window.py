"""
Main Settings Window for ARIA using PyQt6.

A modern, beautiful settings interface.
"""

import sys
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..audio.capture import AudioCapture
from ..i18n import LANGUAGES, get_current_language, set_language, t
from ..model_manager.registry import ModelRegistry
from ..settings_manager import get_settings_manager
from ..timezone_utils import available_timezone_names, validate_timezone_name
from .model_manager_window import show_model_manager


class SettingsWindow(QMainWindow):
    """Main settings window with model selection, language, VAD options, etc."""

    # Model options
    LANGUAGE_CODES = [None, "zh", "en", "ja", "ko", "yue", "es", "fr", "de"]

    # Signal for thread-safe updates
    status_update = pyqtSignal(str, str)  # text, color

    @staticmethod
    def _get_realtime_languages():
        """Get available languages for realtime mode."""
        return [
            ("中/英文", "zh"),  # Uses Sherpa
            ("日文", "ja"),  # Uses Vosk
        ]

    @staticmethod
    def _get_streaming_model_for_language(lang_code: str) -> str:
        """Get the streaming model ID for a language."""
        if lang_code in ["zh", "en"]:
            return "sherpa-zh-en"
        elif lang_code == "ja":
            return "vosk-ja"
        return "sherpa-zh-en"  # Default

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
    def REALTIME_LANGUAGES(self):
        return self._get_realtime_languages()

    @property
    def LANGUAGES(self):
        return self._get_languages()

    def __init__(
        self,
        on_start: Callable[[dict], None],
        on_quit: Callable[[], None] | None = None,
        on_toggle_overlay: Callable[[], bool] | None = None,
    ):
        """Initialize the settings window.

        Args:
            on_start: Callback when user clicks Start. Called with settings dict.
            on_quit: Callback when user clicks Quit.
        """
        super().__init__()

        self.on_start = on_start
        self.on_quit = on_quit
        self.on_toggle_overlay = on_toggle_overlay
        self._is_running = False
        self._loading = True

        # Window setup
        self.setWindowTitle("ARIA")
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

        # Connect status signal
        self.status_update.connect(self._update_status_label)

    def _center_on_screen(self):
        """Center window on screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _get_stylesheet(self):
        """Return the main stylesheet."""
        return """
            QMainWindow {
                background-color: #1a1a1a;
            }
            QLabel {
                color: white;
            }
            QFrame#card {
                background-color: #2a2a2a;
                border-radius: 12px;
            }
            QFrame#title_label {
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #3B8ED0;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4AA3E0;
            }
            QPushButton:pressed {
                background-color: #2A7DC0;
            }
            QPushButton#secondary {
                background-color: transparent;
                border: 1px solid #555555;
                color: #aaaaaa;
            }
            QPushButton#secondary:hover {
                background-color: #333333;
            }
            QComboBox {
                background-color: #333333;
                color: white;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 180px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: #333333;
                color: white;
                selection-background-color: #3B8ED0;
            }
            QCheckBox {
                color: white;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 1px solid #555555;
                background-color: #333333;
            }
            QCheckBox::indicator:hover {
                border-color: #3B8ED0;
                background-color: #444444;
            }
            QCheckBox::indicator:checked {
                background-color: #3B8ED0;
                border-color: #3B8ED0;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #4AA3E0;
                border-color: #4AA3E0;
            }
            QComboBox:hover {
                border-color: #3B8ED0;
            }
        """

    def _create_ui(self):
        """Create all UI components."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # === Header ===
        header = self._create_header()
        main_layout.addWidget(header)

        # === Two-column layout ===
        columns = QHBoxLayout()
        columns.setSpacing(15)

        # Left column
        left_col = QVBoxLayout()
        left_col.setSpacing(15)
        self.recognition_card = self._create_recognition_card()
        self.model_card = self._create_model_card()
        left_col.addWidget(self.recognition_card, 0)
        left_col.addWidget(self.model_card, 1)
        left_col.setStretch(0, 0)
        left_col.setStretch(1, 1)
        columns.addLayout(left_col, 1)  # Equal weight

        # Right column
        right_col = QVBoxLayout()
        right_col.setSpacing(15)
        right_col.addWidget(self._create_translation_card())
        right_col.addWidget(self._create_reset_card())
        columns.addLayout(right_col, 1)  # Equal weight

        main_layout.addLayout(columns)

        # Push button to bottom
        main_layout.addStretch()

        # === Start Button ===
        button_row = QHBoxLayout()
        button_row.addStretch()

        self.start_button = QPushButton("🎙 " + t("start"))
        self.start_button.setMinimumHeight(45)
        self.start_button.setMinimumWidth(150)
        self.start_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.start_button.clicked.connect(self._on_start_click)
        button_row.addWidget(self.start_button)

        button_row.addStretch()
        main_layout.addLayout(button_row)

        # === Status Label (close to button) ===
        self.status_label = QLabel(t("status_ready"))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #888888; margin-top: 5px;")
        main_layout.addWidget(self.status_label)

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

        subtitle = QLabel(t("subtitle") + " | v2.0.1")
        subtitle.setStyleSheet("color: #aaaaaa; font-size: 12px;")
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
        frame.setMaximumWidth(400)  # Limit maximum width to prevent imbalance
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(12)

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("", 13, QFont.Weight.Bold))
        layout.addWidget(title_label)

        return frame, layout

    def _create_recognition_card(self):
        """Create recognition settings card."""
        card, layout = self._create_card(t("recognition_settings"))
        card.setMinimumHeight(250)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Mode selector (Precise / Realtime)
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(10)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.addStretch()

        self.mode_realtime_btn = QPushButton(t("mode_realtime"))
        self.mode_realtime_btn.setMinimumWidth(92)
        self.mode_realtime_btn.setMinimumHeight(38)
        self.mode_realtime_btn.setCheckable(True)
        self.mode_realtime_btn.setChecked(True)
        self.mode_realtime_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #555555;
                color: #888888;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #3B8ED0;
            }
            QPushButton:checked {
                background-color: #3B8ED0;
                border: none;
                color: white;
            }
            QPushButton:checked:hover {
                background-color: #4AA3E0;
            }
        """)
        self.mode_realtime_btn.clicked.connect(lambda: self._on_mode_change("realtime"))
        mode_layout.addWidget(self.mode_realtime_btn)

        self.mode_livecaptions_btn = QPushButton(t("mode_livecaptions"))
        self.mode_livecaptions_btn.setMinimumWidth(92)
        self.mode_livecaptions_btn.setMinimumHeight(38)
        self.mode_livecaptions_btn.setCheckable(True)
        self.mode_livecaptions_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #555555;
                color: #888888;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #3B8ED0;
            }
            QPushButton:checked {
                background-color: #3B8ED0;
                border: none;
                color: white;
            }
            QPushButton:checked:hover {
                background-color: #4AA3E0;
            }
        """)
        self.mode_livecaptions_btn.clicked.connect(lambda: self._on_mode_change("livecaptions"))
        mode_layout.addWidget(self.mode_livecaptions_btn)

        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Mode description
        self.mode_desc = QLabel(t("mode_realtime_desc"))
        self.mode_desc.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        self.mode_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mode_desc)

        # Audio source selector
        source_row = QHBoxLayout()
        source_row.addWidget(QLabel(t("audio_source_label")))
        self.audio_source_dropdown = QComboBox()
        self._populate_audio_source_dropdown()
        self.audio_source_dropdown.currentTextChanged.connect(self._on_audio_source_change)
        source_row.addWidget(self.audio_source_dropdown)
        source_row.addStretch()
        layout.addLayout(source_row)

        tz_row = QHBoxLayout()
        tz_row.addWidget(QLabel("Timezone (IANA):"))
        self.timezone_dropdown = QComboBox()
        self.timezone_dropdown.setEditable(True)
        self.timezone_dropdown.addItem("system")
        self.timezone_dropdown.addItems(available_timezone_names())
        self.timezone_dropdown.currentTextChanged.connect(lambda _: self._persist_ui_settings())
        tz_row.addWidget(self.timezone_dropdown)
        tz_row.addStretch()
        layout.addLayout(tz_row)

        return card

    def _create_model_card(self):
        """Create model settings card."""
        card, layout = self._create_card(t("model_settings"))

        # Store reference for enabling/disabling
        self.model_card = card

        # Model dropdown (dynamic from registry)
        model_row = QHBoxLayout()
        self.model_label = QLabel(t("model") + ":")
        model_row.addWidget(self.model_label)
        self.model_dropdown = QComboBox()
        self._populate_model_dropdown()
        self.model_dropdown.currentTextChanged.connect(self._on_model_change)
        model_row.addWidget(self.model_dropdown)
        model_row.addStretch()
        layout.addLayout(model_row)

        # Language dropdown (for translation target, not ASR)
        lang_row = QHBoxLayout()
        self.lang_label = QLabel(t("lang") + ":")
        lang_row.addWidget(self.lang_label)
        self.lang_dropdown = QComboBox()
        self.lang_dropdown.addItems([lang[0] for lang in self.LANGUAGES])
        self.lang_dropdown.currentTextChanged.connect(lambda _: self._persist_ui_settings())
        lang_row.addWidget(self.lang_dropdown)
        lang_row.addStretch()
        layout.addLayout(lang_row)

        # Manage models button
        self.manage_models_btn = QPushButton("📦 " + t("manage_models"))
        self.manage_models_btn.setObjectName("secondary")
        self.manage_models_btn.setMaximumWidth(160)
        self.manage_models_btn.clicked.connect(self._on_manage_models)
        layout.addWidget(self.manage_models_btn)

        return card

    def _create_translation_card(self):
        """Create translation settings card."""
        card, layout = self._create_card(t("translation_settings"))

        # Translation switch
        trans_row = QHBoxLayout()
        trans_row.addWidget(QLabel(t("translation") + ":"))
        self.trans_checkbox = QCheckBox()
        self.trans_checkbox.stateChanged.connect(self._on_translation_change)
        trans_row.addWidget(self.trans_checkbox)
        self.trans_status = QLabel("OFF")
        self.trans_status.setStyleSheet("color: #888888;")
        trans_row.addWidget(self.trans_status)
        trans_row.addStretch()
        layout.addLayout(trans_row)

        # Engine dropdown
        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel(t("engine") + ":"))
        self.trans_engine_dropdown = QComboBox()
        self.trans_engine_dropdown.addItems(
            [
                t("engine_openai"),
                t("engine_google_free"),
                t("engine_bing"),
                t("engine_youdao"),
            ]
        )
        self.trans_engine_dropdown.currentTextChanged.connect(self._on_engine_change)
        engine_row.addWidget(self.trans_engine_dropdown)
        engine_row.addStretch()
        layout.addLayout(engine_row)

        # OpenAI parameter section (hidden by default, shown when OpenAI selected)
        self.openai_section = QFrame()
        self.openai_section.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border-radius: 6px;
                padding: 10px;
            }
            QLabel {
                color: #aaaaaa;
                font-size: 12px;
            }
            QLineEdit, QDoubleSpinBox, QSpinBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
                border-color: #3B8ED0;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                height: 14px;
                background-color: #444444;
                border-radius: 3px;
                margin: 2px 2px 0 0;
            }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
                background-color: #3B8ED0;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                height: 14px;
                background-color: #444444;
                border-radius: 3px;
                margin: 0 2px 2px 0;
            }
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #3B8ED0;
            }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 6px solid white;
                width: 0px;
                height: 0px;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid white;
                width: 0px;
                height: 0px;
            }
        """)
        openai_layout = QVBoxLayout(self.openai_section)
        openai_layout.setContentsMargins(10, 8, 10, 8)
        openai_layout.setSpacing(6)

        # Endpoint
        ep_row = QHBoxLayout()
        ep_row.addWidget(QLabel("Endpoint:"))
        self.openai_endpoint = QLineEdit("http://127.0.0.1:8080/v1")
        self.openai_endpoint.textChanged.connect(lambda _: self._persist_ui_settings())
        ep_row.addWidget(self.openai_endpoint)
        openai_layout.addLayout(ep_row)

        # API Key
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API Key:"))
        self.openai_api_key = QLineEdit()
        self.openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key.setPlaceholderText("optional")
        self.openai_api_key.textChanged.connect(lambda _: self._persist_ui_settings())
        key_row.addWidget(self.openai_api_key)
        openai_layout.addLayout(key_row)

        # Model Name
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))
        self.openai_model_name = QLineEdit()
        self.openai_model_name.setPlaceholderText("default")
        self.openai_model_name.textChanged.connect(lambda _: self._persist_ui_settings())
        model_row.addWidget(self.openai_model_name)
        openai_layout.addLayout(model_row)

        # System Prompt
        sys_row = QHBoxLayout()
        sys_row.addWidget(QLabel("System Prompt:"))
        self.openai_system_prompt = QLineEdit()
        self.openai_system_prompt.setPlaceholderText("default")
        self.openai_system_prompt.textChanged.connect(lambda _: self._persist_ui_settings())
        sys_row.addWidget(self.openai_system_prompt)
        openai_layout.addLayout(sys_row)

        # Temperature + Max Tokens in one row
        params_row = QHBoxLayout()
        params_row.addWidget(QLabel("Temp:"))
        self.openai_temperature = QDoubleSpinBox()
        self.openai_temperature.setRange(0.0, 2.0)
        self.openai_temperature.setSingleStep(0.1)
        self.openai_temperature.setValue(0.2)
        self.openai_temperature.valueChanged.connect(lambda _: self._persist_ui_settings())
        params_row.addWidget(self.openai_temperature)
        params_row.addStretch()
        params_row.addWidget(QLabel("Max Tokens:"))
        self.openai_max_tokens = QSpinBox()
        self.openai_max_tokens.setRange(1, 4096)
        self.openai_max_tokens.setValue(4096)
        self.openai_max_tokens.valueChanged.connect(lambda _: self._persist_ui_settings())
        params_row.addWidget(self.openai_max_tokens)
        openai_layout.addLayout(params_row)

        self.openai_section.hide()
        layout.addWidget(self.openai_section)

        # Target language dropdown
        target_row = QHBoxLayout()
        target_row.addWidget(QLabel(t("target_lang") + ":"))
        self.target_lang_dropdown = QComboBox()
        self.target_lang_dropdown.addItems(
            [
                t("target_zh_TW"),
                t("target_zh_CN"),
                t("target_en"),
                t("target_ja"),
                t("target_ko"),
                t("target_es"),
                t("target_fr"),
                t("target_de"),
            ]
        )
        self.target_lang_dropdown.currentTextChanged.connect(lambda _: self._persist_ui_settings())
        target_row.addWidget(self.target_lang_dropdown)
        target_row.addStretch()
        layout.addLayout(target_row)

        return card

    def _create_reset_card(self):
        """Create reset settings card."""
        card = QFrame()
        card.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)

        self.overlay_toggle_button = QPushButton(t("overlay_hide"))
        self.overlay_toggle_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #555555;
                color: #aaaaaa;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #3B8ED0;
            }
        """)
        self.overlay_toggle_button.clicked.connect(self._on_toggle_overlay)
        quick_row.addWidget(self.overlay_toggle_button)

        layout.addLayout(quick_row)

        self.reset_button = QPushButton("🔄 " + t("reset_settings"))
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #555555;
                color: #aaaaaa;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #3B8ED0;
            }
        """)
        self.reset_button.clicked.connect(self._on_reset_settings)
        button_row.addWidget(self.reset_button)

        self.quit_button = QPushButton("⏻ " + t("quit_app"))
        self.quit_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #555555;
                color: #aaaaaa;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #E04040;
            }
        """)
        self.quit_button.clicked.connect(self._on_quit_app)
        button_row.addWidget(self.quit_button)

        layout.addLayout(button_row)

        reset_desc = QLabel(t("reset_settings_desc"))
        reset_desc.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        reset_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(reset_desc)

        return card

    # === Event Handlers ===

    def _populate_model_dropdown(self):
        """Populate model dropdown from ModelRegistry."""
        self.model_dropdown.blockSignals(True)
        self.model_dropdown.clear()
        registry = ModelRegistry(Path("models"))
        for spec in registry.list():
            self.model_dropdown.addItem(spec.display_name, spec.id)
        self.model_dropdown.blockSignals(False)

    def _on_mode_change(self, mode: str):
        """Handle mode button click."""
        if mode == "realtime":
            self.mode_realtime_btn.setChecked(True)
            self.mode_livecaptions_btn.setChecked(False)
            self.mode_desc.setText(t("mode_realtime_desc"))
            # Swap to realtime language selection (shows in model dropdown position)
            self.model_label.setText(t("lang") + ":")  # Change label to "语言:"
            self.model_label.show()  # Ensure label is visible
            self.model_dropdown.clear()
            self._populate_model_dropdown()
            self.model_dropdown.setEnabled(True)
            self.model_dropdown.show()  # Ensure dropdown is visible
            # Hide language dropdown in realtime mode (selection is in model dropdown)
            self.lang_label.hide()
            self.lang_dropdown.hide()
            self.manage_models_btn.show()
            # Normal styling for Model card
            self.model_label.setStyleSheet("color: white;")
            self.model_card.setEnabled(True)
            self.model_card.setStyleSheet("")
        else:  # livecaptions mode
            self.mode_realtime_btn.setChecked(False)
            self.mode_livecaptions_btn.setChecked(True)
            self.mode_desc.setText(t("mode_livecaptions_desc"))
            # Disable model selection (uses Windows LiveCaptions)
            self.model_label.hide()
            self.model_dropdown.hide()
            self.lang_label.hide()
            self.lang_dropdown.hide()
            self.manage_models_btn.hide()
            self.model_label.setStyleSheet("color: #555555;")
            self.model_card.setEnabled(False)
            self.model_card.setStyleSheet("#card { background-color: rgba(42, 42, 42, 0.5); }")
        self._persist_ui_settings()

    def _on_model_change(self, model_text: str):
        """Handle model dropdown change."""
        self._persist_ui_settings()

    def _on_translation_change(self, state):
        """Handle translation checkbox change."""
        if state:
            self.trans_status.setText("ON")
            self.trans_status.setStyleSheet("color: #3B8ED0;")
        else:
            self.trans_status.setText("OFF")
            self.trans_status.setStyleSheet("color: #888888;")
        self._persist_ui_settings()

    def _on_engine_change(self, _text: str):
        """Handle translation engine change - show/hide OpenAI params."""
        if _text == t("engine_openai"):
            self.openai_section.show()
        else:
            self.openai_section.hide()
        self._persist_ui_settings()

    def _on_audio_source_change(self, _value: str):
        """Handle audio source change."""
        self._persist_ui_settings()

    def _get_selected_audio_source(self) -> str:
        """Get selected audio source key from dropdown."""
        data = self.audio_source_dropdown.currentData()
        if isinstance(data, str) and data:
            return data

        return "system"

    def _populate_audio_source_dropdown(self, preferred_source: str | None = None) -> None:
        """Populate audio source dropdown with system and microphone devices."""
        selected_source = preferred_source or self._get_selected_audio_source()
        if selected_source == "ts_tail":
            selected_source = "system"
        self.audio_source_dropdown.blockSignals(True)
        self.audio_source_dropdown.clear()

        # Keep existing logic options first.
        self.audio_source_dropdown.addItem(t("audio_source_system"), "system")
        self.audio_source_dropdown.addItem(t("audio_source_mic"), AudioCapture.MIC_DEFAULT_SOURCE)

        for mic in AudioCapture.list_microphone_devices():
            idx = mic.get("index")
            name = (mic.get("name") or "").strip()
            if idx is None or not name:
                continue
            label = t("mic_device_label", name=name)
            if mic.get("is_default"):
                label = t("mic_default_device_label", name=name)
            self.audio_source_dropdown.addItem(label, f"{AudioCapture.MIC_SOURCE_PREFIX}{idx}")

        index = self.audio_source_dropdown.findData(selected_source)
        if index < 0:
            index = self.audio_source_dropdown.findData("system")
        if index >= 0:
            self.audio_source_dropdown.setCurrentIndex(index)
        self.audio_source_dropdown.blockSignals(False)

    def _on_manage_models(self):
        """Open model manager window."""
        show_model_manager(self)

    def _on_reset_settings(self):
        """Reset all settings."""
        result = QMessageBox.question(
            self,
            t("reset_settings"),
            t("reset_settings_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            # Delete settings file
            settings = get_settings_manager()
            settings_path = settings._config_file
            if settings_path.exists():
                settings_path.unlink()

            # Restart app
            import subprocess

            subprocess.Popen([sys.executable, "-m", "aria.ui.app"])
            QApplication.quit()

    def _on_quit_app(self):
        """Quit the application."""
        if self.on_quit:
            self.on_quit()
        else:
            QApplication.quit()

    def _on_toggle_overlay(self):
        """Toggle subtitle overlay visibility."""
        if not self.on_toggle_overlay:
            return
        is_visible = self.on_toggle_overlay()
        self.overlay_toggle_button.setText(t("overlay_hide") if is_visible else t("overlay_show"))

    def _on_ui_language_change(self, lang_display: str):
        """Handle UI language change."""
        # Find language code from display name
        lang_code = None
        for code, (name, _) in LANGUAGES.items():
            if name == lang_display:
                lang_code = code
                break

        if lang_code and lang_code != get_current_language():
            set_language(lang_code)
            QMessageBox.information(self, t("restart_required"), t("restart_required"))

    def _on_start_click(self):
        """Handle start/stop button click."""
        if self._is_running:
            # Stop
            self.on_start(None)
        else:
            # Start - gather settings
            settings = self._gather_settings()
            self.on_start(settings)

    def _persist_ui_settings(self) -> None:
        """Persist current UI selections without starting."""
        if self._loading:
            return
        self._gather_settings()

    def _gather_settings(self) -> dict:
        """Gather current settings into a dictionary."""
        # Determine mode
        mode = "livecaptions" if self.mode_livecaptions_btn.isChecked() else "realtime"

        if mode == "livecaptions":
            # LiveCaptions mode: no model/language selection needed
            model_id = None
            lang_code = None
        else:
            # Realtime mode: model dropdown shows model specs from registry
            lang_code = None
            idx = self.model_dropdown.currentIndex()
            if idx >= 0:
                model_id = self.model_dropdown.itemData(idx) or "sherpa-zh-en-zipformer"
            else:
                model_id = "sherpa-zh-en-zipformer"

        # Get target language code
        target_lang = self._get_target_language_code()

        # Get translation engine - map display name to engine ID
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

        # OpenAI params (always saved, even if not using OpenAI)
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

        # Save settings
        self._save_settings(settings)

        return settings

    def _get_target_language_code(self) -> str:
        """Get target language code from dropdown."""
        target_display = self.target_lang_dropdown.currentText()

        # Map display names to NLLB codes
        target_map = {
            t("target_zh_TW"): "zho_Hant",
            t("target_zh_CN"): "zho_Hans",
            t("target_en"): "eng_Latn",
            t("target_ja"): "jpn_Jpan",
            t("target_ko"): "kor_Hang",
            t("target_es"): "spa_Latn",
            t("target_fr"): "fra_Latn",
            t("target_de"): "deu_Latn",
        }

        return target_map.get(target_display, "zho_Hant")

    def _save_settings(self, settings: dict):
        """Save settings to file."""
        sm = get_settings_manager()
        for key, value in settings.items():
            sm.set(key, value)
        sm.save()

    def _load_saved_settings(self):
        """Load saved settings from previous session."""
        sm = get_settings_manager()

        # Mode (handle legacy Chinese values and removed "precise" mode)
        mode = sm.get("mode", "realtime")
        if mode in ["實時", "realtime", "精準", "precise"]:
            mode = "realtime"
        self._on_mode_change(mode)

        # Load model selection from saved model_id
        model_id = sm.get("model_id", "sherpa-zh-en-zipformer")
        idx = self.model_dropdown.findData(model_id)
        if idx >= 0:
            self.model_dropdown.setCurrentIndex(idx)

        # Translation
        self.trans_checkbox.setChecked(sm.get("enable_translation", False))

        # Translation engine - map engine ID to display name
        engine = sm.get("translation_engine", "bing")
        engine_reverse_map = {
            "openai": t("engine_openai"),
            "google_free": t("engine_google_free"),
            "bing": t("engine_bing"),
            "youdao": t("engine_youdao"),
            # Legacy support
            "google": t("engine_google_free"),
            "baidu": t("engine_bing"),
            "alibaba": t("engine_bing"),
            "nllb": t("engine_bing"),
        }
        display_name = engine_reverse_map.get(engine, t("engine_bing"))
        self.trans_engine_dropdown.setCurrentText(display_name)
        self._on_engine_change(display_name)  # 强制同步面板显示状态

        # Target language
        target = sm.get("target_language", "zho_Hant")
        target_map = {
            "zho_Hant": t("target_zh_TW"),
            "zho_Hans": t("target_zh_CN"),
            "eng_Latn": t("target_en"),
            "jpn_Jpan": t("target_ja"),
            "kor_Hang": t("target_ko"),
            "spa_Latn": t("target_es"),
            "fra_Latn": t("target_fr"),
            "deu_Latn": t("target_de"),
        }
        if target in target_map:
            self.target_lang_dropdown.setCurrentText(target_map[target])

        tz_name = sm.get("timezone", "system") or "system"
        if not validate_timezone_name(tz_name):
            tz_name = "system"
        self.timezone_dropdown.setCurrentText(tz_name)

        # Audio source
        audio_source = sm.get("audio_source", "system")
        self._populate_audio_source_dropdown(preferred_source=audio_source)

        # Overlay toggle state
        overlay_visible = sm.get("overlay_visible", True)
        self.overlay_toggle_button.setText(t("overlay_hide") if overlay_visible else t("overlay_show"))

        # OpenAI params
        self.openai_endpoint.setText(sm.get("openai_endpoint", "http://127.0.0.1:1234/v1"))
        self.openai_api_key.setText(sm.get("openai_api_key", ""))
        self.openai_model_name.setText(sm.get("openai_model_name", ""))
        self.openai_temperature.setValue(sm.get("openai_temperature", 0.2))
        self.openai_max_tokens.setValue(sm.get("openai_max_tokens", 1024))
        self.openai_system_prompt.setText(sm.get("openai_system_prompt", ""))

    # === Public API ===

    def show_running(self):
        """Update UI to show running state."""
        self._is_running = True
        self.start_button.setText("⏹ " + t("stop"))
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #E04040;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F05050;
            }
        """)
        self.status_label.setText(t("status_running"))
        self.status_label.setStyleSheet("color: #3B8ED0;")

    def show_stopped(self):
        """Update UI to show stopped state."""
        self._is_running = False
        self.start_button.setText("🎙 " + t("start"))
        self.start_button.setStyleSheet("")  # Reset to default
        self.status_label.setText(t("status_ready"))
        self.status_label.setStyleSheet("color: #888888;")

    def _update_status_label(self, text: str, color: str):
        """Update status label (thread-safe via signal)."""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")


# Quick test
if __name__ == "__main__":
    app = QApplication(sys.argv)

    def on_start(settings):
        print(f"Start clicked: {settings}")

    window = SettingsWindow(on_start=on_start)
    window.show()

    sys.exit(app.exec())
