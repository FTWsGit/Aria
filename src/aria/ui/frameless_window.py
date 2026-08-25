"""
Frameless window drag mixin.

Provides mouse-press/move/release drag logic for frameless windows.
SubtitleOverlay applies it to the whole window; ConsoleWindow applies
it to a dedicated drag-header widget.
"""

from collections.abc import Callable

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QWidget


class FramelessWindowMixin:
    """Mixin that adds frameless-window drag behaviour.

    Usage:
        class MyWindow(FramelessWindowMixin, QWidget):
            def __init__(self):
                super().__init__()
                self._init_drag_state()

            def mousePressEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    self.start_window_drag(event.globalPosition().toPoint(), self)
    """

    def _init_drag_state(self) -> None:
        """Initialise drag-offset tracking.  Call in __init__."""
        self._drag_offset: QPoint | None = None

    # ---- drag mechanics --------------------------------------------------

    def start_window_drag(self, global_pos: QPoint, window: QWidget) -> None:
        """Record the offset between the mouse and the window origin."""
        self._drag_offset = global_pos - window.pos()

    def move_window_during_drag(self, global_pos: QPoint, window: QWidget) -> bool:
        """Move *window* to follow the mouse.  Returns True while dragging."""
        if self._drag_offset is None:
            return False
        window.move(global_pos - self._drag_offset)
        return True

    def end_window_drag(self, on_save: Callable[[], None] | None = None) -> None:
        """Clear drag state and optionally persist the new position."""
        self._drag_offset = None
        if on_save:
            on_save()
