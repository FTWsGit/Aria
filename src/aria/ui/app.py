"""
Main Application using PyQt6 - Coordinates settings window, overlay, and pipeline.
"""

import os
import sys
import threading

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from ..events import SubtitleEvent
from ..i18n import t
from ..livecaptions.pipeline import LiveCaptionsPipeline
from ..logger import set_console_mode, start_simple_log_session
from ..pipeline import StreamingPipeline
from ..settings_manager import get_settings_manager
from ..timezone_utils import set_app_timezone_name
from .settings_window import SettingsWindow
from .subtitle_overlay import SubtitleOverlay
from .system_tray import SystemTray


class PipelineSignals(QObject):
    """Signals for thread-safe communication from pipeline to UI."""
    subtitle = pyqtSignal(object)  # SubtitleEvent
    started = pyqtSignal()
    error = pyqtSignal(str)


class App:
    """Main application coordinator.
    
    Manages the settings window, subtitle overlay, system tray, and transcription pipeline.
    """
    
    def __init__(self):
        """Initialize the application."""
        self._settings_window: SettingsWindow | None = None
        self._overlay: SubtitleOverlay | None = None
        self._translation_overlay: SubtitleOverlay | None = None
        self._pipeline: StreamingPipeline | LiveCaptionsPipeline | None = None
        self._tray: SystemTray | None = None
        self._is_running = False
        self._last_settings: dict | None = None
        self._is_livecaptions_mode = False
        self._enable_translation = False
        self._overlay_visible = True
        
        # Pipeline signals for thread-safe updates
        self._signals = PipelineSignals()
        self._signals.subtitle.connect(self._on_subtitle)
        self._signals.started.connect(self._on_pipeline_started)
        self._signals.error.connect(self._on_error)
    
    def run(self) -> None:
        """Run the application."""
        # Create QApplication
        self._app = QApplication(sys.argv)
        self._app.setApplicationName("ARIA")
        self._app.setFont(QFont("Segoe UI", 9))
        
        # Create settings window
        sm = get_settings_manager()
        self._overlay_visible = sm.get("overlay_visible", True)
        set_console_mode(sm.get("console_mode", "verbose"))
        set_app_timezone_name(sm.get("timezone", "system"))

        self._settings_window = SettingsWindow(
            on_start=self._on_start,
            on_quit=self._cleanup_and_quit,
            on_toggle_overlay=self._toggle_overlay_visibility,
        )
        self._settings_window.show()
        
        # Handle window close
        self._settings_window.closeEvent = self._on_window_close
        
        # Create and start system tray
        self._tray = SystemTray(
            on_show=self._on_tray_show,
            on_toggle=self._on_tray_toggle,
            on_quit=self._on_tray_quit
        )
        self._tray.start()
        
        # Start the Qt event loop
        sys.exit(self._app.exec())
    
    def _on_window_close(self, event) -> None:
        """Handle window close - minimize to tray."""
        event.ignore()
        self._settings_window.hide()
        
        if self._tray:
            self._tray.show_notification(
                t("tray_minimized_title"),
                t("tray_minimized_msg")
            )
    
    def _on_tray_show(self) -> None:
        """Handle tray 'show' click."""
        self._settings_window.show()
        self._settings_window.activateWindow()
    
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
        mode = settings.get("mode", "realtime")
        self._is_livecaptions_mode = (mode == "livecaptions")
        self._enable_translation = settings.get("enable_translation", False)
        
        # Check if all required models are available
        if not self._check_all_required_models(settings):
            return
        
        # Create overlays based on mode
        if self._is_livecaptions_mode:
            # LiveCaptions mode: only create translation overlay if needed
            # (original subtitles shown by Windows LiveCaptions)
            if self._enable_translation:
                if self._translation_overlay is None:
                    self._translation_overlay = SubtitleOverlay(
                        position_key="translation_overlay",
                        on_close=self._stop
                    )
                    self._translation_overlay.set_translation_mode(True)
                    self._translation_overlay.set_multiline_mode(True)
            elif self._translation_overlay is not None:
                self._translation_overlay.close()
                self._translation_overlay = None
        else:
            # Other modes: create both original and translation overlays
            if self._overlay is None:
                self._overlay = SubtitleOverlay(on_close=self._stop)
            
            # Create translation overlay if enabled
            if self._enable_translation and self._translation_overlay is None:
                self._translation_overlay = SubtitleOverlay(
                    position_key="translation_overlay",
                    on_close=self._stop
                )
                self._translation_overlay.set_translation_mode(True)
            elif not self._enable_translation and self._translation_overlay is not None:
                self._translation_overlay.close()
                self._translation_overlay = None
            
            # Set overlay mode (realtime)
            self._overlay.set_multiline_mode(True)
            if self._translation_overlay:
                self._translation_overlay.set_multiline_mode(True)

        # Apply hidden state immediately so start won't pop overlays when disabled.
        if not self._overlay_visible:
            if self._overlay:
                self._overlay.hide()
            if self._translation_overlay:
                self._translation_overlay.hide()
        
        # Create pipeline
        def create_pipeline():
            try:
                if self._is_livecaptions_mode:
                    # Use Windows LiveCaptions
                    self._pipeline = LiveCaptionsPipeline(
                        on_subtitle=lambda e: self._signals.subtitle.emit(e),
                        enable_translation=self._enable_translation,
                        translation_engine=settings.get("translation_engine", "google"),
                        target_language=settings.get("target_language", "zho_Hant"),
                        auto_hide_window=False,  # Keep Windows LiveCaptions window visible
                        openai_endpoint=settings.get("openai_endpoint", "http://127.0.0.1:1234/v1"),
                        openai_api_key=settings.get("openai_api_key", ""),
                        openai_model_name=settings.get("openai_model_name", ""),
                        openai_temperature=settings.get("openai_temperature", 0.2),
                        openai_max_tokens=settings.get("openai_max_tokens", 1024),
                        openai_system_prompt=settings.get("openai_system_prompt", ""),
                    )
                else:
                    # Use Sherpa-ONNX streaming pipeline (auto-discovers model files)
                    model_dir = settings.get("model_dir") or None
                    self._pipeline = StreamingPipeline(
                        model_dir=model_dir,
                        on_subtitle=lambda e: self._signals.subtitle.emit(e),
                        enable_translation=self._enable_translation,
                        translation_engine=settings.get("translation_engine", "google"),
                        target_language=settings.get("target_language", "zho_Hant"),
                        audio_source=settings.get("audio_source", "system"),
                        openai_endpoint=settings.get("openai_endpoint", "http://127.0.0.1:1234/v1"),
                        openai_api_key=settings.get("openai_api_key", ""),
                        openai_model_name=settings.get("openai_model_name", ""),
                        openai_temperature=settings.get("openai_temperature", 0.2),
                        openai_max_tokens=settings.get("openai_max_tokens", 1024),
                        openai_system_prompt=settings.get("openai_system_prompt", ""),
                    )
                
                self._pipeline.start()
                self._signals.started.emit()
                
            except Exception as e:
                self._signals.error.emit(str(e))
        
        # Start pipeline in background thread
        threading.Thread(target=create_pipeline, daemon=True).start()
        
        # Show loading state
        self._settings_window.status_label.setText(t("status_loading_model"))
        self._settings_window.status_label.setStyleSheet("color: #888888;")
    
    def _on_pipeline_started(self) -> None:
        """Called when pipeline has started."""
        self._is_running = True
        self._settings_window.show_running()
        
        # Show overlays based on mode
        if not self._overlay_visible:
            if self._overlay:
                self._overlay.hide()
            if self._translation_overlay:
                self._translation_overlay.hide()
            if self._tray:
                self._tray.update_status(True)
            return

        if self._is_livecaptions_mode:
            # LiveCaptions mode: only show translation overlay
            if self._translation_overlay:
                self._translation_overlay.show()
                self._translation_overlay.update_subtitle(t("overlay_translation_waiting"), "")
        else:
            # Other modes: show original subtitle overlay
            if self._overlay:
                self._overlay.show()
                self._overlay.update_subtitle(t("overlay_waiting"), "")
            
            if self._translation_overlay:
                self._translation_overlay.show()
                self._translation_overlay.update_subtitle(t("overlay_translation_waiting"), "")
        
        # Update tray
        if self._tray:
            self._tray.update_status(True)
    
    def _on_subtitle(self, event: SubtitleEvent) -> None:
        """Handle subtitle events from pipeline."""
        if not self._is_running:
            return
        if not self._overlay_visible:
            return
        
        # For LiveCaptions mode, only update translation overlay
        if self._is_livecaptions_mode:
            # Windows LiveCaptions shows the original text
            # We only need to handle translation
            if self._translation_overlay:
                # 隱藏原文框（LiveCaptions 已顯示）
                if hasattr(self._translation_overlay, 'subtitle_label'):
                    self._translation_overlay.subtitle_label.hide()
                
                # 使用新的雙緩衝字段
                if (getattr(event, 'committed_translation', None) is not None or 
                    getattr(event, 'draft_translation', None) is not None):
                    self._translation_overlay.update_subtitle(
                        "",
                        "",
                        None,
                        committed_translation=event.committed_translation,
                        draft_translation=event.draft_translation
                    )
                elif event.translated_text:
                    # 向後兼容舊格式
                    self._translation_overlay.update_subtitle("", "", translated_text=event.translated_text)
            return
        
        text = event.text
        language = event.language
        display_text = text
        
        # Update overlay
        if self._overlay:
            self._overlay.update_subtitle(display_text, language)
        
        # Update translation overlay
        if self._translation_overlay:
            # Check for dual-buffer fields (New Streaming/LiveCaptions logic)
            if (getattr(event, 'committed_translation', None) is not None or 
                getattr(event, 'draft_translation', None) is not None):
                
                self._translation_overlay.update_subtitle(
                    "",
                    "",
                    None,
                    committed_translation=event.committed_translation,
                    draft_translation=event.draft_translation
                )

    def _on_error(self, error: str) -> None:
        """Handle pipeline error."""
        self._is_running = False
        self._settings_window.show_stopped()
        self._settings_window.status_label.setText(f"Error: {error}")
        self._settings_window.status_label.setStyleSheet("color: red;")
        
        if self._tray:
            self._tray.update_status(False)
    
    def _stop(self) -> None:
        """Stop the pipeline and overlay."""
        self._is_running = False

        if self._pipeline:
            self._pipeline.stop()
            self._pipeline = None
        
        if self._overlay:
            self._overlay.hide()
        
        if self._translation_overlay:
            self._translation_overlay.hide()
        
        self._settings_window.show_stopped()
        
        if self._tray:
            self._tray.update_status(False)
    
    def _check_all_required_models(self, settings: dict) -> bool:
        """Check if all required models are available and prompt to download if not."""
        # Realtime mode: Sherpa-ONNX model is auto-discovered from disk.
        # LiveCaptions mode: no models needed.
        # Translation models are no longer managed by ARIA.
        return True

    def _toggle_overlay_visibility(self) -> bool:
        """Toggle subtitle overlay visibility and persist setting."""
        self._overlay_visible = not self._overlay_visible
        sm = get_settings_manager()
        sm.set("overlay_visible", self._overlay_visible)
        sm.save()

        if self._overlay:
            if self._overlay_visible and self._is_running and not self._is_livecaptions_mode:
                self._overlay.show()
            else:
                self._overlay.hide()

        if self._translation_overlay:
            if self._overlay_visible and self._is_running:
                self._translation_overlay.show()
            else:
                self._translation_overlay.hide()

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
