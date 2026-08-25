"""
General tab: reset settings, quit, overlay toggle.
"""

import subprocess
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ...i18n import t
from ...settings_manager import get_settings_manager


class GeneralTabMixin:
    """Mixin providing general tab UI and event handlers."""

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
                background-color: #ffffff;
                border: 1px solid #c0c0c0;
                color: #444444;
                border-radius: 4px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #0078D4;
            }
        """)
        self.overlay_toggle_button.clicked.connect(self._on_toggle_overlay)
        quick_row.addWidget(self.overlay_toggle_button)

        layout.addLayout(quick_row)

        self.reset_button = QPushButton("🔄 " + t("reset_settings"))
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #c0c0c0;
                color: #444444;
                border-radius: 4px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #0078D4;
            }
        """)
        self.reset_button.clicked.connect(self._on_reset_settings)
        button_row.addWidget(self.reset_button)

        self.quit_button = QPushButton("⏻ " + t("quit_app"))
        self.quit_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #c0c0c0;
                color: #444444;
                border-radius: 4px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #fdf0f0;
                border-color: #E04040;
                color: #c0392b;
            }
        """)
        self.quit_button.clicked.connect(self._on_quit_app)
        button_row.addWidget(self.quit_button)

        layout.addLayout(button_row)

        reset_desc = QLabel(t("reset_settings_desc"))
        reset_desc.setStyleSheet("color: #666666; font-size: 12px;")
        reset_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(reset_desc)

        return card

    def _on_reset_settings(self):
        """Reset all settings."""
        result = QMessageBox.question(
            self,
            t("reset_settings"),
            t("reset_settings_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            settings = get_settings_manager()
            settings_path = settings.config_file_path
            if settings_path.exists():
                settings_path.unlink()

            subprocess.Popen([sys.executable, "-m", "aria.ui.app"])
            QApplication.quit()

    def _on_quit_app(self):
        """Quit the application."""
        if self.on_quit:
            self.on_quit()
        else:
            QApplication.quit()
