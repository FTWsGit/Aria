"""
Main Application using PyQt6 - Coordinates settings window, overlay, and pipeline.
"""

import os
import signal
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from ..events import SubtitleEvent, TranscriptMessage
from ..i18n import t
from ..logger import exception, set_log_verbosity, start_simple_log_session
from ..model_manager.manager import ModelManager
from ..model_manager.registry import ModelRegistry
from ..pipelines import LiveCaptionsPipeline, StreamingPipeline
from ..settings_manager import get_settings_manager
from ..timezone_utils import set_app_timezone_name
from .console_window import ConsoleWindow
from .pipeline_factory import PipelineFactory
from .settings_window import SettingsWindow
from .subtitle_overlay import SubtitleOverlay
from .system_tray import SystemTray


class PipelineSignals(QObject):
    """Signals for thread-safe communication from pipeline to UI."""

    subtitle = pyqtSignal(object)  # SubtitleEvent
    message = pyqtSignal(object)  # TranscriptMessage
    started = pyqtSignal()
    error = pyqtSignal(str)


class App:
    """Main application coordinator.

    Manages the settings window, subtitle overlay, system tray, and transcription pipeline.
    """

    def __init__(self):
        """Initialize the application."""
        self._settings_window: SettingsWindow | None = None
        self._console: ConsoleWindow | None = None
        self._overlay: SubtitleOverlay | None = None
        self._pipeline: StreamingPipeline | LiveCaptionsPipeline | None = None
        self._tray: SystemTray | None = None
        self._is_running = False
        self._last_settings: dict | None = None
        self._is_livecaptions_mode = False
        self._enable_translation = False
        self._overlay_visible = True

        # Model registry and manager
        self._registry = ModelRegistry(Path("models"))
        self._model_manager = ModelManager(self._registry)

        # Pipeline signals for thread-safe updates
        self._signals = PipelineSignals()
        self._signals.subtitle.connect(self._on_subtitle)
        self._signals.message.connect(self._on_message)
        self._signals.started.connect(self._on_pipeline_started)
        self._signals.error.connect(self._on_error)

    def run(self) -> None:
        """Run the application."""
        # Create QApplication
        self._app = QApplication(sys.argv)
        self._app.setApplicationName("ARIA")
        self._app.setFont(QFont("Segoe UI", 9))
        # Closing an auxiliary window (settings) must never quit the app;
        # only the console's Quit button / tray Quit should do that.
        self._app.setQuitOnLastWindowClosed(False)

        # Create settings window (hidden until opened from the console)
        sm = get_settings_manager()
        self._overlay_visible = sm.get("overlay_visible", True)
        set_log_verbosity(sm.get("log_verbosity", "verbose"))
        set_app_timezone_name(sm.get("timezone", "system"))

        self._settings_window = SettingsWindow(
            on_quit=self._cleanup_and_quit,
            on_toggle_overlay=self._toggle_overlay_visibility,
        )

        # Create console window: the app's primary, always-visible window.
        self._console = ConsoleWindow()
        self._console.start_clicked.connect(self._on_console_start)
        self._console.stop_clicked.connect(self._stop)
        self._console.settings_clicked.connect(self._on_show_settings)
        self._console.quit_clicked.connect(self._cleanup_and_quit)
        self._console.topmost_toggled.connect(self._on_console_topmost_toggled)
        self._console.auto_scroll_toggled.connect(self._on_console_auto_scroll_toggled)
        self._console.geometry_changed.connect(self._on_console_geometry_changed)
        self._console.closed.connect(self._on_console_closed)

        self._console.restore_preferences(
            topmost=sm.get("console_topmost", True),
            auto_scroll=sm.get("console_auto_scroll", True),
        )
        x, y, w, h = (
            sm.get("console_x", -1),
            sm.get("console_y", -1),
            sm.get("console_w", -1),
            sm.get("console_h", -1),
        )
        if x >= 0 and y >= 0:
            self._console.restore_geometry(x, y, w, h)

        self._console.show()

        # Create and start system tray
        self._tray = SystemTray(on_show=self._on_tray_show, on_toggle=self._on_tray_toggle, on_quit=self._on_tray_quit)
        self._tray.start()

        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, lambda sig, frame: self._cleanup_and_quit())
        # Qt event loop blocks Python signal delivery; a timer forces periodic checks
        self._sigint_timer = QTimer()
        self._sigint_timer.timeout.connect(lambda: None)
        self._sigint_timer.start(500)

        # Start the Qt event loop
        sys.exit(self._app.exec())

    def _on_console_closed(self) -> None:
        """Console window was closed - minimize to tray."""
        if self._tray:
            self._tray.show_notification(t("tray_minimized_title"), t("tray_minimized_msg"))

    def _on_show_settings(self) -> None:
        """Open (or raise) the settings window from the console's Settings button."""
        self._settings_window.show()
        self._settings_window.activateWindow()

    def _on_console_start(self) -> None:
        """Console's start button: gather settings and start the pipeline."""
        self._on_start(self._settings_window.get_settings())

    def _on_console_topmost_toggled(self, checked: bool) -> None:
        sm = get_settings_manager()
        sm.set("console_topmost", checked)
        sm.save()

    def _on_console_auto_scroll_toggled(self, checked: bool) -> None:
        sm = get_settings_manager()
        sm.set("console_auto_scroll", checked)
        sm.save()

    def _on_console_geometry_changed(self, x: int, y: int, w: int, h: int) -> None:
        sm = get_settings_manager()
        sm.set("console_x", x)
        sm.set("console_y", y)
        sm.set("console_w", w)
        sm.set("console_h", h)
        sm.save()

    def _on_tray_show(self) -> None:
        """Handle tray 'show' click."""
        self._console.show()
        self._console.activateWindow()

    def _on_tray_toggle(self) -> None:
        """Handle tray 'toggle' click."""
        if self._is_running:
            self._stop()
        else:
            if self._last_settings:
                self._on_start(self._last_settings)

    def _on_tray_quit(self) -> None:
        """Handle tray 'quit' click."""
        self._cleanup_and_quit()

    def _cleanup_and_quit(self) -> None:
        """Clean up and quit the application."""
        self._stop()
        if self._tray:
            self._tray.stop()
        self._app.quit()

    def _on_start(self, settings: dict) -> None:
        """Handle start/stop button click."""
        if settings is None:
            self._stop()
            return

        if self._is_running:
            self._stop()
            return

        # Save settings for tray toggle
        self._last_settings = settings
        # Re-sync overlay visibility from persisted settings to avoid stale state.
        sm = get_settings_manager()
        self._overlay_visible = sm.get("overlay_visible", self._overlay_visible)
        set_app_timezone_name(settings.get("timezone", "system"))
        # Create a new simple log file for this start run.
        start_simple_log_session()

        # Check mode
        mode = settings.get("mode", "asr")
        self._is_livecaptions_mode = mode == "livecaptions"
        self._enable_translation = settings.get("enable_translation", False)

        # Check if all required models are available
        if not self._check_all_required_models(settings):
            return

        # Create the merged overlay (original + translation, one window)
        if self._overlay is None:
            self._overlay = SubtitleOverlay(on_close=self._stop)
        self._overlay.set_multiline_mode(True)

        # Apply hidden state immediately so start won't pop the overlay when disabled.
        if not self._overlay_visible:
            self._overlay.hide()

        # Defensive: clean up any leftover pipeline from a previous error path
        self._stop_pipeline()

        # Create pipeline
        def create_pipeline():
            try:
                if self._is_livecaptions_mode:
                    self._pipeline = PipelineFactory.create_livecaptions_pipeline(settings, self._signals)
                else:
                    self._pipeline = PipelineFactory.create_streaming_pipeline(
                        settings,
                        self._registry,
                        self._model_manager,
                        self._signals,
                        lambda msg: self._signals.error.emit(msg),
                    )

                self._pipeline.start()
                self._signals.started.emit()

            except Exception:
                exception("Pipeline creation failed")
                self._signals.error.emit("error_pipeline_startup")

        # Start pipeline in background thread
        threading.Thread(target=create_pipeline, daemon=True).start()

        # Show loading state
        self._console.set_status(t("status_loading_model"))

    def _on_pipeline_started(self) -> None:
        """Called when pipeline has started."""
        self._is_running = True
        self._console.set_running(True)
        self._console.set_status(t("status_running"))

        # Show overlays based on mode
        if not self._overlay_visible:
            if self._overlay:
                self._overlay.hide()
            if self._tray:
                self._tray.update_status(True)
            return

        if self._overlay:
            self._overlay.show()
            if self._enable_translation:
                self._overlay.update_subtitle(
                    t("overlay_waiting"),
                    "",
                    committed_translation=t("overlay_translation_waiting"),
                    draft_translation="",
                )
            else:
                self._overlay.update_subtitle(t("overlay_waiting"), "")

        # Update tray
        if self._tray:
            self._tray.update_status(True)

    def _on_subtitle(self, event: SubtitleEvent) -> None:
        """Handle subtitle events from pipeline."""
        if not self._is_running:
            return
        if not self._overlay_visible or not self._overlay:
            return

        # Windows LiveCaptions and Sherpa ASR both feed the same merged
        # overlay now: original text (dimmed) + translation (prominent).
        if (
            getattr(event, "committed_translation", None) is not None
            or getattr(event, "draft_translation", None) is not None
        ):
            self._overlay.update_subtitle(
                event.text,
                event.language,
                committed_translation=event.committed_translation,
                draft_translation=event.draft_translation,
            )
        else:
            self._overlay.update_subtitle(event.text, event.language)

    def _on_message(self, msg: TranscriptMessage) -> None:
        """Handle a finalized transcript line from the pipeline."""
        if not self._is_running or not self._console:
            return
        self._console.add_message(msg)

    def _stop_pipeline(self) -> None:
        """Stop and release the pipeline instance."""
        if self._pipeline:
            self._pipeline.stop()
            self._pipeline = None

    def _on_error(self, error: str) -> None:
        """Handle pipeline error."""
        self._is_running = False
        self._stop_pipeline()
        self._console.set_running(False)
        display_msg = t(error)
        self._console.set_status(display_msg)

        if self._tray:
            self._tray.update_status(False)

    def _stop(self) -> None:
        """Stop the pipeline and overlay."""
        self._is_running = False

        self._stop_pipeline()

        if self._overlay:
            self._overlay.hide()

        self._console.set_running(False)
        self._console.set_status(t("status_ready"))

        if self._tray:
            self._tray.update_status(False)

    def _check_all_required_models(self, settings: dict) -> bool:
        """Check if all required models are available and prompt to download if not."""
        mode = settings.get("mode", "asr")
        if mode == "livecaptions":
            return True

        model_id = settings.get("model_id") or "None"
        try:
            spec = self._registry.get(model_id)
        except KeyError:
            return True

        if not self._model_manager.is_downloaded(spec):
            from PyQt6.QtWidgets import QMessageBox, QPushButton

            msg = t("model_required_download_msg", model_id=model_id)
            dlg = QMessageBox(QMessageBox.Icon.Warning, t("model_required_download_title"), msg)
            btn_open = QPushButton(t("open_model_manager_btn"))
            dlg.addButton(btn_open, QMessageBox.ButtonRole.AcceptRole)
            dlg.addButton(QMessageBox.StandardButton.Cancel)
            dlg.setDefaultButton(btn_open)

            def on_btn_clicked():
                if dlg.clickedButton() is btn_open:
                    self._settings_window._on_manage_models()
                dlg.close()

            btn_open.clicked.connect(on_btn_clicked)
            dlg.exec()
            return False

        return True

    def _toggle_overlay_visibility(self) -> bool:
        """Toggle subtitle overlay visibility and persist setting."""
        self._overlay_visible = not self._overlay_visible
        sm = get_settings_manager()
        sm.set("overlay_visible", self._overlay_visible)
        sm.save()

        if self._overlay:
            if self._overlay_visible and self._is_running:
                self._overlay.show()
            else:
                self._overlay.hide()

        return self._overlay_visible


def run_app():
    """Entry point for the GUI application."""
    # Set environment
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    # Run app
    app = App()
    app.run()


if __name__ == "__main__":
    run_app()
