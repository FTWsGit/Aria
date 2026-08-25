"""
Recognition tab: ASR mode, model selection, audio source.
"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)

from ...audio.capture import AudioCapture
from ...i18n import t
from ...model_manager.registry import ModelRegistry
from ..model_manager_window import show_model_manager


class RecognitionTabMixin:
    """Mixin providing recognition tab UI and event handlers."""

    def _create_recognition_card(self):
        """Create recognition settings card."""
        card, layout = self._create_card(t("recognition_settings"))
        card.setMinimumHeight(250)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Mode selector (Precise / asr)
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(10)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.addStretch()

        self.mode_asr_btn = QPushButton(t("mode_asr"))
        self.mode_asr_btn.setMinimumWidth(92)
        self.mode_asr_btn.setMinimumHeight(38)
        self.mode_asr_btn.setCheckable(True)
        self.mode_asr_btn.setChecked(True)
        self.mode_asr_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #c0c0c0;
                color: #444444;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #0078D4;
            }
            QPushButton:checked {
                background-color: #0078D4;
                border: none;
                color: white;
            }
            QPushButton:checked:hover {
                background-color: #106EBE;
            }
        """)
        self.mode_asr_btn.clicked.connect(lambda: self._on_mode_change("asr"))
        mode_layout.addWidget(self.mode_asr_btn)

        self.mode_livecaptions_btn = QPushButton(t("mode_livecaptions"))
        self.mode_livecaptions_btn.setMinimumWidth(92)
        self.mode_livecaptions_btn.setMinimumHeight(38)
        self.mode_livecaptions_btn.setCheckable(True)
        self.mode_livecaptions_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #c0c0c0;
                color: #444444;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #0078D4;
            }
            QPushButton:checked {
                background-color: #0078D4;
                border: none;
                color: white;
            }
            QPushButton:checked:hover {
                background-color: #106EBE;
            }
        """)
        self.mode_livecaptions_btn.clicked.connect(lambda: self._on_mode_change("livecaptions"))
        mode_layout.addWidget(self.mode_livecaptions_btn)

        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Mode description
        self.mode_desc = QLabel(t("mode_asr_desc"))
        self.mode_desc.setStyleSheet("color: #666666; font-size: 12px;")
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
        from ...timezone_utils import available_timezone_names

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
        if mode == "asr":
            self.mode_asr_btn.setChecked(True)
            self.mode_livecaptions_btn.setChecked(False)
            self.mode_desc.setText(t("mode_asr_desc"))
            self.model_label.setText(t("model") + ":")
            self.model_label.show()
            self.model_dropdown.clear()
            self._populate_model_dropdown()
            self.model_dropdown.setEnabled(True)
            self.model_dropdown.show()
            self.lang_label.hide()
            self.lang_dropdown.hide()
            self.manage_models_btn.show()
            self.model_label.setStyleSheet("color: white;")
            self.model_card.setEnabled(True)
            self.model_card.setStyleSheet("")
        else:
            self.mode_asr_btn.setChecked(False)
            self.mode_livecaptions_btn.setChecked(True)
            self.mode_desc.setText(t("mode_livecaptions_desc"))
            self.model_label.setText(t("model") + ":")
            self.model_label.hide()
            self.model_dropdown.hide()
            self.lang_label.hide()
            self.lang_dropdown.hide()
            self.manage_models_btn.hide()
            self.model_label.setStyleSheet("color: #555555;")
            self.model_card.setEnabled(False)
            self.model_card.setStyleSheet("#card { background-color: rgba(240, 240, 240, 0.8); }")
        self._persist_ui_settings()

    def _on_model_change(self, model_text: str):
        """Handle model dropdown change."""
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
