"""
Model tab: ASR model selection, download/delete management, progress display.
"""

import os
import subprocess
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...i18n import t
from ...model_manager import ModelManager, ModelStatus
from ...model_manager.registry import ModelRegistry


class ModelTabMixin:
    """Mixin providing model tab UI and event handlers."""

    # Signal for thread-safe model download progress updates.
    model_download_progress = pyqtSignal(str, float, str)

    def _create_model_tab(self):
        """Create the model tab page: selection dropdown + managed model list."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        # Model registry and manager (shared across methods)
        self._model_registry = ModelRegistry(Path("models"))
        self._model_manager = ModelManager(self._model_registry)

        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnMinimumWidth(1, 180)
        self.model_label = QLabel(t("model") + ":")
        grid.addWidget(self.model_label, 0, 0)
        self.model_dropdown = QComboBox()
        self._populate_model_dropdown()
        self.model_dropdown.currentTextChanged.connect(self._on_model_change)
        grid.addWidget(self.model_dropdown, 0, 1)
        layout.addLayout(grid)

        # Managed model list
        self._model_rows: dict[str, dict] = {}
        layout.addWidget(self._create_model_list_section())

        # Secondary action
        open_folder_btn = QPushButton(t("open_models_folder"))
        open_folder_btn.clicked.connect(self._open_models_folder)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(open_folder_btn)
        layout.addLayout(btn_row)

        # Connect download progress signal
        self.model_download_progress.connect(self._on_model_download_progress)

        return page

    def _create_model_list_section(self) -> QGroupBox:
        """Create the managed model list section."""
        group = QGroupBox(t("streaming_models"))
        self.model_list_group = group
        rows_layout = QVBoxLayout(group)
        rows_layout.setContentsMargins(12, 10, 12, 10)
        rows_layout.setSpacing(6)

        for spec in self._model_registry.list():
            rows_layout.addWidget(self._create_model_row(spec))

        return group

    def _create_model_row(self, spec) -> QFrame:
        """Create a single model row: name · language · size | status/action."""
        row = QFrame()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 6, 8, 6)
        row_layout.setSpacing(8)

        row_layout.addWidget(QLabel(spec.display_name))

        meta_bits = []
        if spec.language:
            meta_bits.append(spec.language)
        if spec.size_mb > 0:
            meta_bits.append(spec.get_size_display())
        if meta_bits:
            meta_label = QLabel(" · ".join(meta_bits))
            meta_label.setStyleSheet("color: gray;")
            row_layout.addWidget(meta_label)

        row_layout.addStretch()

        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)
        progress_bar.hide()
        row_layout.addWidget(progress_bar)

        status = self._model_manager.get_status(spec)

        if status == ModelStatus.DOWNLOADED:
            row_layout.addWidget(QLabel(t("downloaded")))
            delete_btn = QPushButton(t("delete"))
            delete_btn.setMaximumWidth(80)
            delete_btn.clicked.connect(lambda checked, s=spec: self._on_delete_clicked(s))
            row_layout.addWidget(delete_btn)
        elif status == ModelStatus.DOWNLOADING:
            progress_bar.show()
            progress_bar.setValue(int(self._model_manager.get_progress(spec) * 100))
        else:
            row_layout.addWidget(QLabel(t("not_downloaded")))
            download_btn = QPushButton(t("download"))
            download_btn.setMaximumWidth(80)
            download_btn.clicked.connect(lambda checked, s=spec: self._on_download_clicked(s))
            row_layout.addWidget(download_btn)

        # Store references for progress updates
        self._model_rows[spec.id] = {
            "row": row,
            "progress_bar": progress_bar,
        }

        return row

    def _on_download_clicked(self, spec):
        """Start downloading a model."""
        if not self._model_rows.get(spec.id):
            return

        def progress_callback(model_id: str, progress: float, status_text: str):
            self.model_download_progress.emit(model_id, progress, status_text)

        self._model_manager.download(spec, progress_callback)
        self._refresh_model_row(spec.id)

    def _on_delete_clicked(self, spec):
        """Delete a downloaded model after confirmation."""
        if spec.source.get("type") == "manual":
            return

        answer = QMessageBox.question(
            self,
            t("delete"),
            t("delete_model_confirm", name=spec.display_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        if self._model_manager.delete(spec):
            self._refresh_model_row(spec.id)

    def _on_model_download_progress(self, model_id: str, progress: float, _status_text: str):
        """Handle model download progress update (UI thread)."""
        row_info = self._model_rows.get(model_id)
        if not row_info:
            return

        progress_bar = row_info["progress_bar"]

        if progress >= 1.0:
            progress_bar.setValue(100)
            progress_bar.hide()
            self._refresh_model_row(model_id)
        elif progress < 0:
            progress_bar.hide()
            self._refresh_model_row(model_id)
        else:
            progress_bar.show()
            progress_bar.setValue(int(progress * 100))

    def _refresh_model_row(self, model_id: str):
        """Refresh a single model row to reflect current status."""
        row_info = self._model_rows.get(model_id)
        if not row_info:
            return

        old_row = row_info["row"]
        parent_layout = old_row.parent().layout()
        if not parent_layout:
            return

        # Find index of old row
        idx = -1
        for i in range(parent_layout.count()):
            if parent_layout.itemAt(i) and parent_layout.itemAt(i).widget() is old_row:
                idx = i
                break

        if idx < 0:
            return

        # Remove old row
        parent_layout.removeWidget(old_row)
        old_row.deleteLater()

        # Create new row
        spec = self._model_registry.get(model_id)
        new_row = self._create_model_row(spec)
        parent_layout.insertWidget(idx, new_row)

    def _open_models_folder(self):
        """Open the models folder in file explorer."""
        models_dir = self._model_manager.cache_dir
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)

        if os.name == "nt":
            os.startfile(str(models_dir))
        else:
            subprocess.run(["xdg-open", str(models_dir)])

    def _populate_model_dropdown(self):
        """Populate model dropdown from ModelRegistry (ASR models only)."""
        self.model_dropdown.blockSignals(True)
        self.model_dropdown.clear()
        for spec in self._model_registry.list():
            if spec.kind not in ("asr_streaming", "asr_chunked"):
                continue
            self.model_dropdown.addItem(spec.display_name, spec.id)
        self.model_dropdown.blockSignals(False)

    def _on_model_change(self, _text: str):
        """Handle model dropdown change."""
        self._persist_ui_settings()
