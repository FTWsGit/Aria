"""
Model Manager Window using PyQt6.
"""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..i18n import t
from ..model_manager import ModelManager, ModelStatus
from ..model_manager.registry import ModelRegistry, ModelSpec


class ModelRow(QFrame):
    """A single row displaying a model's status and actions."""

    progress_updated = pyqtSignal(float, str)

    def __init__(
        self,
        model: ModelSpec,
        manager: ModelManager,
        on_status_change: Callable | None = None,
    ):
        super().__init__()

        self.model = model
        self.manager = manager
        self.on_status_change = on_status_change

        self.setObjectName("model_row")
        self.setStyleSheet("""
            #model_row {
                background-color: #333333;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        self._create_ui()
        self._update_status()

        # Connect signal
        self.progress_updated.connect(self._update_progress_ui)

    def _create_ui(self):
        """Create the row UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)

        # Top row: name and size
        top_row = QHBoxLayout()

        # Model name with emoji if recommended
        name = self.model.display_name
        if "large-v3" in self.model.id and "turbo" not in self.model.id:
            name = "⭐ " + name  # Recommended

        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: white;")
        top_row.addWidget(self.name_label)

        top_row.addStretch()

        # Size
        size_label = QLabel(f"({self.model.get_size_display()})")
        size_label.setStyleSheet("color: #888888;")
        top_row.addWidget(size_label)

        layout.addLayout(top_row)

        # Description
        desc = self.model.language
        if desc:
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #444444;
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3B8ED0;
                border-radius: 4px;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Status text
        self.status_text = QLabel("")
        self.status_text.setStyleSheet("color: #888888; font-size: 11px;")
        self.status_text.hide()
        layout.addWidget(self.status_text)

        # Progress disclaimer
        self.progress_note = QLabel(t("download_progress_note"))
        self.progress_note.setStyleSheet("color: #666666; font-size: 10px;")
        self.progress_note.hide()
        layout.addWidget(self.progress_note)

        # Action button
        button_row = QHBoxLayout()
        button_row.addStretch()

        self.action_button = QPushButton(t("download"))
        self.action_button.setMaximumWidth(120)
        self.action_button.clicked.connect(self._on_action)
        button_row.addWidget(self.action_button)

        layout.addLayout(button_row)

    def _update_status(self):
        """Update UI based on model status."""
        status = self.manager.get_status(self.model)

        if status == ModelStatus.DOWNLOADED:
            self.action_button.setText(t("downloaded"))
            self.action_button.setEnabled(False)
            self.action_button.setStyleSheet("""
                QPushButton {
                    background-color: #2a5a2a;
                    color: #90EE90;
                    border-radius: 6px;
                }
            """)
            self.progress_bar.hide()
            self.status_text.hide()
            self.progress_note.hide()
        elif status == ModelStatus.DOWNLOADING:
            self.action_button.setText(t("downloading"))
            self.action_button.setEnabled(False)
            self.progress_bar.show()
            self.status_text.show()
            self.progress_note.show()
        else:
            self.action_button.setText(t("download"))
            self.action_button.setEnabled(True)
            self.action_button.setStyleSheet("""
                QPushButton {
                    background-color: #3B8ED0;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #4AA3E0;
                }
            """)
            self.progress_bar.hide()
            self.status_text.hide()
            self.progress_note.hide()

    def _on_action(self):
        """Handle action button click."""
        status = self.manager.get_status(self.model)
        if status == ModelStatus.NOT_DOWNLOADED:
            self._start_download()

    def _start_download(self):
        """Start downloading the model."""
        self.action_button.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.status_text.show()
        self.progress_note.show()

        def progress_callback(model_id: str, progress: float, status_text: str):
            self.progress_updated.emit(progress, status_text)

        # Start download in background
        self.manager.download(self.model, progress_callback)

    def _update_progress_ui(self, progress: float, status_text: str):
        """Update progress display (called from signal)."""
        self.progress_bar.setValue(int(progress * 100))
        self.status_text.setText(status_text)
        self.progress_note.show()

        if progress >= 1.0:
            self._update_status()
            if self.on_status_change:
                self.on_status_change()


class ModelManagerWindow(QDialog):
    """Window for managing model downloads."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(t("model_manager_title"))
        self.setFixedSize(650, 550)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #3B8ED0;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4AA3E0;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)

        self.registry = ModelRegistry(Path("models"))
        self.manager = ModelManager(self.registry)
        self.model_rows: dict[str, ModelRow] = {}

        self._create_ui()

    def _create_ui(self):
        """Create the window UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("📦 " + t("model_manager_title"))
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Scroll area for models
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background-color: #2a2a2a;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 5px;
                min-height: 20px;
            }
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)

        # Streaming models section
        self._create_model_section(scroll_layout, t("streaming_models"))

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Footer buttons
        footer = QHBoxLayout()

        open_folder_btn = QPushButton("📁 " + t("open_models_folder"))
        open_folder_btn.clicked.connect(self._open_models_folder)
        footer.addWidget(open_folder_btn)

        footer.addStretch()

        close_btn = QPushButton(t("close"))
        close_btn.clicked.connect(self.close)
        footer.addWidget(close_btn)

        layout.addLayout(footer)

    def _create_model_section(self, parent_layout, title: str):
        """Create a section for a group of models."""
        # Section title
        section_title = QLabel(title)
        section_title.setFont(QFont("", 13, QFont.Weight.Bold))
        section_title.setStyleSheet("color: #888888; margin-top: 10px;")
        parent_layout.addWidget(section_title)

        # Get models from registry
        for spec in self.registry.list():
            row = ModelRow(spec, self.manager, self._on_status_change)
            self.model_rows[spec.id] = row
            parent_layout.addWidget(row)

    def _on_status_change(self):
        """Called when any model's status changes."""

    def _open_models_folder(self):
        """Open the models folder in file explorer."""
        models_dir = self.manager.models_dir
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)

        # Open in file explorer
        if os.name == "nt":
            os.startfile(str(models_dir))
        else:
            subprocess.run(["xdg-open", str(models_dir)])


def show_model_manager(parent=None):
    """Show the model manager window."""
    dialog = ModelManagerWindow(parent)
    dialog.exec()
