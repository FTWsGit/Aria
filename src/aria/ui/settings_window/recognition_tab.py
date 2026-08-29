"""
Recognition tab: ASR/LiveCaptions mode, audio source, timezone, VAD.
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...audio.capture import AudioCapture
from ...i18n import t


class RecognitionTabMixin:
    """Mixin providing recognition tab UI and event handlers."""

    def _create_recognition_tab(self):
        """Create the recognition settings page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnMinimumWidth(1, 180)

        # Mode selector (ASR / LiveCaptions)
        grid.addWidget(QLabel(t("recognition_settings") + ":"), 0, 0)
        mode_widget = QWidget()
        mode_row = QHBoxLayout(mode_widget)
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.setSpacing(6)

        self.mode_asr_btn = QPushButton(t("mode_asr"))
        self.mode_asr_btn.setCheckable(True)
        self.mode_asr_btn.setChecked(True)
        self.mode_asr_btn.clicked.connect(lambda: self._on_mode_change("asr"))
        mode_row.addWidget(self.mode_asr_btn)

        self.mode_livecaptions_btn = QPushButton(t("mode_livecaptions"))
        self.mode_livecaptions_btn.setCheckable(True)
        self.mode_livecaptions_btn.clicked.connect(lambda: self._on_mode_change("livecaptions"))
        mode_row.addWidget(self.mode_livecaptions_btn)

        mode_row.addStretch()
        grid.addWidget(mode_widget, 0, 1)

        # Mode description spans below
        self.mode_desc = QLabel(t("mode_asr_desc"))
        grid.addWidget(self.mode_desc, 1, 0, 1, 2)

        # Audio source selector
        grid.addWidget(QLabel(t("audio_source_label")), 2, 0)
        self.audio_source_dropdown = QComboBox()
        self._populate_audio_source_dropdown()
        self.audio_source_dropdown.currentTextChanged.connect(self._on_audio_source_change)
        grid.addWidget(self.audio_source_dropdown, 2, 1)

        # Timezone
        grid.addWidget(QLabel(t("timezone_label")), 3, 0)
        self.timezone_dropdown = QComboBox()
        self.timezone_dropdown.setEditable(True)
        self.timezone_dropdown.addItem("system")
        from ...timezone_utils import available_timezone_names

        self.timezone_dropdown.addItems(available_timezone_names())
        self.timezone_dropdown.currentTextChanged.connect(lambda _: self._persist_ui_settings())
        grid.addWidget(self.timezone_dropdown, 3, 1)

        layout.addLayout(grid)
        layout.addStretch(1)

        # === VAD section ===
        vad_check = QCheckBox(t("vad_enable_label"))
        vad_check.setChecked(False)
        vad_check.toggled.connect(self._on_vad_enable_toggle)
        self.vad_checkbox = vad_check
        layout.addWidget(vad_check)

        vad_model_row = QHBoxLayout()
        vad_model_row.setContentsMargins(0, 0, 0, 0)
        vad_model_row.setSpacing(6)
        vad_model_row.addWidget(QLabel(t("vad_model_label") + ":"))
        self.vad_model_dropdown = QComboBox()
        self._populate_vad_model_dropdown()
        self.vad_model_dropdown.currentTextChanged.connect(lambda _: self._persist_ui_settings())
        vad_model_row.addWidget(self.vad_model_dropdown, 1)
        self.vad_model_row = vad_model_row
        layout.addLayout(vad_model_row)

        # Advanced VAD settings (collapsible)
        self.vad_advanced_group = QGroupBox(t("vad_advanced_label"))
        self.vad_advanced_group.setCheckable(True)
        self.vad_advanced_group.setChecked(False)
        self.vad_advanced_group.toggled.connect(lambda _: self._persist_ui_settings())

        adv_grid = QGridLayout(self.vad_advanced_group)
        adv_grid.setContentsMargins(12, 10, 12, 10)
        adv_grid.setSpacing(6)

        self.vad_threshold_spin = QDoubleSpinBox()
        self.vad_threshold_spin.setRange(0.05, 0.95)
        self.vad_threshold_spin.setSingleStep(0.05)
        self.vad_threshold_spin.setDecimals(2)
        self.vad_threshold_spin.setValue(0.5)
        self.vad_threshold_spin.valueChanged.connect(lambda _: self._persist_ui_settings())
        adv_grid.addWidget(QLabel(t("vad_threshold_label")), 0, 0)
        adv_grid.addWidget(self.vad_threshold_spin, 0, 1)

        self.vad_min_silence_spin = QDoubleSpinBox()
        self.vad_min_silence_spin.setRange(0.1, 5.0)
        self.vad_min_silence_spin.setSingleStep(0.05)
        self.vad_min_silence_spin.setDecimals(2)
        self.vad_min_silence_spin.setValue(0.5)
        self.vad_min_silence_spin.valueChanged.connect(lambda _: self._persist_ui_settings())
        adv_grid.addWidget(QLabel(t("vad_min_silence_label")), 1, 0)
        adv_grid.addWidget(self.vad_min_silence_spin, 1, 1)

        self.vad_min_speech_spin = QDoubleSpinBox()
        self.vad_min_speech_spin.setRange(0.05, 2.0)
        self.vad_min_speech_spin.setSingleStep(0.05)
        self.vad_min_speech_spin.setDecimals(2)
        self.vad_min_speech_spin.setValue(0.25)
        self.vad_min_speech_spin.valueChanged.connect(lambda _: self._persist_ui_settings())
        adv_grid.addWidget(QLabel(t("vad_min_speech_label")), 2, 0)
        adv_grid.addWidget(self.vad_min_speech_spin, 2, 1)

        self.vad_max_speech_spin = QDoubleSpinBox()
        self.vad_max_speech_spin.setRange(1.0, 60.0)
        self.vad_max_speech_spin.setSingleStep(1.0)
        self.vad_max_speech_spin.setDecimals(1)
        self.vad_max_speech_spin.setValue(20.0)
        self.vad_max_speech_spin.valueChanged.connect(lambda _: self._persist_ui_settings())
        adv_grid.addWidget(QLabel(t("vad_max_speech_label")), 3, 0)
        adv_grid.addWidget(self.vad_max_speech_spin, 3, 1)

        self.vad_split_punctuation_check = QCheckBox(t("vad_split_punctuation_label"))
        self.vad_split_punctuation_check.setChecked(True)
        self.vad_split_punctuation_check.toggled.connect(lambda _: self._persist_ui_settings())
        adv_grid.addWidget(self.vad_split_punctuation_check, 4, 0, 1, 2)

        layout.addWidget(self.vad_advanced_group)

        return page

    def _on_mode_change(self, mode: str):
        """Handle mode button click."""
        if mode == "asr":
            self.mode_asr_btn.setChecked(True)
            self.mode_livecaptions_btn.setChecked(False)
            self.mode_desc.setText(t("mode_asr_desc"))
            self.model_label.show()
            self.model_dropdown.clear()
            self._populate_model_dropdown()
            self.model_dropdown.setEnabled(True)
            self.model_dropdown.show()
            self.model_list_group.setEnabled(True)
            self.vad_checkbox.show()
            self._update_vad_controls_visibility()
            self.vad_advanced_group.show()
        else:
            self.mode_asr_btn.setChecked(False)
            self.mode_livecaptions_btn.setChecked(True)
            self.mode_desc.setText(t("mode_livecaptions_desc"))
            self.model_label.hide()
            self.model_dropdown.hide()
            self.model_list_group.setEnabled(False)
            self.vad_checkbox.hide()
            self._hide_vad_model_row()
            self.vad_advanced_group.hide()
        self._persist_ui_settings()

    def _on_audio_source_change(self, _value: str):
        """Handle audio source change."""
        self._persist_ui_settings()

    def _on_vad_enable_toggle(self, checked: bool):
        """Handle VAD enable checkbox toggle."""
        self._update_vad_controls_visibility()
        self._persist_ui_settings()

    def _update_vad_controls_visibility(self):
        """Show/hide VAD model and advanced controls based on checkbox state."""
        enabled = self.vad_checkbox.isChecked()
        if enabled:
            self._show_vad_model_row()
        else:
            self._hide_vad_model_row()

    def _show_vad_model_row(self):
        """Show VAD model dropdown row."""
        for i in range(self.vad_model_row.count()):
            w = self.vad_model_row.itemAt(i)
            if w and w.widget():
                w.widget().show()

    def _hide_vad_model_row(self):
        """Hide VAD model dropdown row."""
        for i in range(self.vad_model_row.count()):
            w = self.vad_model_row.itemAt(i)
            if w and w.widget():
                w.widget().hide()

    def _populate_vad_model_dropdown(self):
        """Populate VAD model dropdown from registry."""
        if not hasattr(self, "_model_registry"):
            return
        self.vad_model_dropdown.blockSignals(True)
        self.vad_model_dropdown.clear()
        vad_models = self._model_registry.list(kind="vad")
        if not vad_models:
            self.vad_model_dropdown.addItem(t("not_downloaded"), None)
            self.vad_model_dropdown.setEnabled(False)
        else:
            for spec in vad_models:
                self.vad_model_dropdown.addItem(spec.display_name, spec.id)
            self.vad_model_dropdown.setEnabled(True)
        self.vad_model_dropdown.blockSignals(False)

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
