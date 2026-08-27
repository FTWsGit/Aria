"""
General tab: reset settings, quit, overlay toggle.
"""

import subprocess
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...i18n import t
from ...settings_manager import get_settings_manager


class GeneralTabMixin:
    """Mixin providing general tab UI and event handlers."""

    def _create_general_tab(self):
        """Create the general settings page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        self.overlay_toggle_button = QPushButton(t("overlay_hide"))
        self.overlay_toggle_button.clicked.connect(self._on_toggle_overlay)
        overlay_row = QHBoxLayout()
        overlay_row.setSpacing(10)
        overlay_row.addWidget(self.overlay_toggle_button)
        overlay_row.addStretch()
        layout.addLayout(overlay_row)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.reset_button = QPushButton(t("reset_settings"))
        self.reset_button.clicked.connect(self._on_reset_settings)
        button_row.addWidget(self.reset_button)

        self.quit_button = QPushButton(t("quit_app"))
        self.quit_button.clicked.connect(self._on_quit_app)
        button_row.addWidget(self.quit_button)

        button_row.addStretch()
        layout.addLayout(button_row)

        reset_desc = QLabel(t("reset_settings_desc"))
        reset_desc.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(reset_desc)

        layout.addStretch(1)

        return page

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
