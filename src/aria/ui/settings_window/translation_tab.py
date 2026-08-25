"""
Translation tab: translation engine settings, OpenAI overlay.
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...i18n import t
from ..styles import OPENAI_OVERLAY_STYLE


class TranslationTabMixin:
    """Mixin providing translation tab UI, OpenAI overlay, and event handlers."""

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
        self.trans_status.setStyleSheet("color: #666666;")
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

        self.openai_config_btn = QPushButton(t("configure"))
        self.openai_config_btn.setObjectName("secondary")
        self.openai_config_btn.setMaximumWidth(100)
        self.openai_config_btn.clicked.connect(self._show_openai_overlay)
        self.openai_config_btn.hide()
        engine_row.addWidget(self.openai_config_btn)

        engine_row.addStretch()
        layout.addLayout(engine_row)

        # Target language dropdown
        target_row = QHBoxLayout()
        target_row.addWidget(QLabel(t("target_lang") + ":"))
        self.target_lang_dropdown = QComboBox()
        from ...translation.language_names import get_target_language_options

        for display_name, _code in get_target_language_options():
            self.target_lang_dropdown.addItem(display_name, _code)
        self.target_lang_dropdown.currentTextChanged.connect(lambda _: self._persist_ui_settings())
        target_row.addWidget(self.target_lang_dropdown)
        target_row.addStretch()
        layout.addLayout(target_row)

        return card

    def _create_openai_overlay(self, parent: QWidget):
        """Create the OpenAI config overlay panel. Covers the content area."""
        self.openai_overlay = QFrame(parent)
        self.openai_overlay.setObjectName("openai_overlay")
        self.openai_overlay.setStyleSheet(OPENAI_OVERLAY_STYLE)
        self.openai_overlay.hide()

        overlay_layout = QVBoxLayout(self.openai_overlay)
        overlay_layout.setContentsMargins(24, 18, 24, 18)
        overlay_layout.setSpacing(10)

        # Back button
        back_btn = QPushButton("← " + t("back"))
        back_btn.setObjectName("secondary")
        back_btn.setMaximumWidth(100)
        back_btn.clicked.connect(self._hide_openai_overlay)
        overlay_layout.addWidget(back_btn)

        # Endpoint
        ep_row = QHBoxLayout()
        ep_row.addWidget(QLabel("Endpoint:"))
        self.openai_endpoint = QLineEdit("http://127.0.0.1:8080/v1")
        self.openai_endpoint.textChanged.connect(lambda _: self._persist_ui_settings())
        ep_row.addWidget(self.openai_endpoint)
        overlay_layout.addLayout(ep_row)

        # API Key
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API Key:"))
        self.openai_api_key = QLineEdit()
        self.openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key.setPlaceholderText("optional")
        self.openai_api_key.textChanged.connect(lambda _: self._persist_ui_settings())
        key_row.addWidget(self.openai_api_key)
        overlay_layout.addLayout(key_row)

        # Model Name
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))
        self.openai_model_name = QLineEdit()
        self.openai_model_name.setPlaceholderText("default")
        self.openai_model_name.textChanged.connect(lambda _: self._persist_ui_settings())
        model_row.addWidget(self.openai_model_name)
        overlay_layout.addLayout(model_row)

        # System Prompt
        sys_row = QHBoxLayout()
        sys_row.addWidget(QLabel("System Prompt:"))
        self.openai_system_prompt = QLineEdit()
        self.openai_system_prompt.setPlaceholderText("default")
        self.openai_system_prompt.textChanged.connect(lambda _: self._persist_ui_settings())
        sys_row.addWidget(self.openai_system_prompt)
        overlay_layout.addLayout(sys_row)

        # Temperature + Max Tokens
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
        overlay_layout.addLayout(params_row)

        overlay_layout.addStretch()

    def _show_openai_overlay(self):
        """Show the OpenAI config overlay, covering the tab area."""
        self.tabs.hide()
        self.openai_overlay.setGeometry(self.tabs.geometry())
        self.openai_overlay.show()
        self.openai_overlay.raise_()

    def _hide_openai_overlay(self):
        """Hide the OpenAI config overlay."""
        self.openai_overlay.hide()
        self.tabs.show()

    def _on_translation_change(self, state):
        """Handle translation checkbox change."""
        if state:
            self.trans_status.setText("ON")
            self.trans_status.setStyleSheet("color: #0078D4;")
        else:
            self.trans_status.setText("OFF")
            self.trans_status.setStyleSheet("color: #666666;")
        self._persist_ui_settings()

    def _on_engine_change(self, _text: str):
        """Handle translation engine change - show/hide OpenAI configure button."""
        if _text == t("engine_openai"):
            self.openai_config_btn.show()
        else:
            self.openai_config_btn.hide()
            self._hide_openai_overlay()
        self._persist_ui_settings()
