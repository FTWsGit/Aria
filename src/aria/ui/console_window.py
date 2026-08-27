"""
Console window: a movable, semi-transparent panel that shows the running
transcript (original + translation, interleaved one line per message) and
hosts the basic transport controls (start/stop, clear, settings, quit).

This is the app's primary window. It is intentionally separate from
`SubtitleOverlay`, which stays a minimal click-through caption strip meant
to be captured as an OBS source for viewers. This window is for the
streamer/operator: history, controls, and monitoring live in here.
"""

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)

from ..events import TranscriptMessage
from ..i18n import t
from .frameless_window import FramelessWindowMixin

MAX_MESSAGES = 200  # Cap history so the widget list doesn't grow unbounded


class _DragHeader(FramelessWindowMixin, QWidget):
    """Thin header strip; click-dragging it moves the parent window."""

    def __init__(self, parent_window: "ConsoleWindow"):
        super().__init__()
        self._window = parent_window
        self._init_drag_state()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_window_drag(event.globalPosition().toPoint(), self._window)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move_window_during_drag(event.globalPosition().toPoint(), self._window)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.end_window_drag(on_save=self._window.request_save_geometry)
        super().mouseReleaseEvent(event)


class _MessageRow(QFrame):
    """One finalized transcript line: source text, then translation below."""

    def __init__(self, msg: TranscriptMessage):
        super().__init__()
        self.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(1)

        ts = datetime.fromtimestamp(msg.timestamp).strftime("%H:%M:%S")
        prefix = f"[{ts}]"
        if msg.language:
            prefix += f" [{msg.language}]"

        original_label = QLabel(f"{prefix} {msg.original}")
        original_label.setWordWrap(True)
        original_label.setStyleSheet("color: #f0f0f0; font-size: 13px;")
        layout.addWidget(original_label)

        if msg.translation:
            translation_label = QLabel(f"> {msg.translation}")
            translation_label.setWordWrap(True)
            translation_label.setStyleSheet("color: #90EE90; font-size: 13px;")
            layout.addWidget(translation_label)


class ConsoleWindow(QWidget):
    """Main operator window: transcript history + transport controls."""

    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    clear_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()
    topmost_toggled = pyqtSignal(bool)
    auto_scroll_toggled = pyqtSignal(bool)
    geometry_changed = pyqtSignal(int, int, int, int)  # x, y, w, h
    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._running = False
        self._auto_scroll = True

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(560, 420)

        self._build_ui()
        self._apply_topmost(True)

    # -- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        container = QFrame()
        container.setObjectName("consoleContainer")
        container.setStyleSheet(
            """
            #consoleContainer {
                background-color: rgba(20, 20, 24, 220);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 20);
                color: #f0f0f0;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 40); }
            QCheckBox { color: #cccccc; font-size: 11px; spacing: 6px; }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid rgba(255, 255, 255, 90);
                border-radius: 3px;
                background-color: rgba(255, 255, 255, 15);
            }
            QCheckBox::indicator:hover { border-color: rgba(255, 255, 255, 150); }
            QCheckBox::indicator:checked {
                background-color: #3B8ED0;
                border-color: #3B8ED0;
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiI+PHBhdGggZD0iTTMgOC41TDYuNSAxMkwxMyA0IiBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMiIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
            }
            """
        )
        outer.addWidget(container)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 6, 8, 6)
        container_layout.setSpacing(4)

        container_layout.addWidget(self._build_header())
        container_layout.addWidget(self._build_toolbar())
        container_layout.addWidget(self._build_message_area(), stretch=1)

        grip_row = QHBoxLayout()
        grip_row.addStretch(1)
        grip = QSizeGrip(self)
        grip.setStyleSheet("background: transparent;")
        grip_row.addWidget(grip)
        container_layout.addLayout(grip_row)

    def _build_header(self) -> QWidget:
        header = _DragHeader(self)
        row = QHBoxLayout(header)
        row.setContentsMargins(2, 2, 2, 2)

        title = QLabel(t("console_title"))
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #f0f0f0;")
        row.addWidget(title)
        row.addStretch(1)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        row.addWidget(self._status_label)

        minimize_btn = QPushButton("_")
        minimize_btn.setToolTip(t("btn_minimize_tray"))
        minimize_btn.clicked.connect(self._on_minimize_to_tray)
        row.addWidget(minimize_btn)

        quit_btn = QPushButton(t("btn_quit"))
        quit_btn.clicked.connect(self.quit_clicked.emit)
        row.addWidget(quit_btn)

        return header

    def _build_toolbar(self) -> QWidget:
        toolbar = QWidget()
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(2, 0, 2, 0)

        self._start_stop_btn = QPushButton(t("start_button"))
        self._start_stop_btn.clicked.connect(self._on_start_stop_clicked)
        row.addWidget(self._start_stop_btn)

        clear_btn = QPushButton(t("btn_clear"))
        clear_btn.clicked.connect(self._on_clear_clicked)
        row.addWidget(clear_btn)

        settings_btn = QPushButton(t("btn_settings"))
        settings_btn.clicked.connect(self.settings_clicked.emit)
        row.addWidget(settings_btn)

        row.addStretch(1)

        self._topmost_check = QCheckBox(t("chk_topmost"))
        self._topmost_check.setChecked(True)
        self._topmost_check.toggled.connect(self._on_topmost_toggled)
        row.addWidget(self._topmost_check)

        self._auto_scroll_check = QCheckBox(t("chk_auto_scroll"))
        self._auto_scroll_check.setChecked(True)
        self._auto_scroll_check.toggled.connect(self._on_auto_scroll_toggled)
        row.addWidget(self._auto_scroll_check)

        return toolbar

    def _build_message_area(self) -> QWidget:
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 8px; background: transparent; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,60); border-radius: 4px; }"
        )

        self._message_container = QWidget()
        self._message_container.setStyleSheet("background: transparent;")
        self._message_layout = QVBoxLayout(self._message_container)
        self._message_layout.setContentsMargins(2, 2, 2, 2)
        self._message_layout.setSpacing(2)
        self._message_layout.addStretch(1)

        self._scroll.setWidget(self._message_container)
        return self._scroll

    # -- Button/checkbox handlers -----------------------------------------

    def _on_start_stop_clicked(self) -> None:
        if self._running:
            self.stop_clicked.emit()
        else:
            self.start_clicked.emit()

    def _on_clear_clicked(self) -> None:
        self.clear()
        self.clear_clicked.emit()

    def _on_auto_scroll_toggled(self, checked: bool) -> None:
        self._auto_scroll = checked
        self.auto_scroll_toggled.emit(checked)

    def _on_topmost_toggled(self, checked: bool) -> None:
        self._apply_topmost(checked)
        self.topmost_toggled.emit(checked)

    def _apply_topmost(self, topmost: bool) -> None:
        """Set base window flags, with WindowStaysOnTopHint toggled on/off.

        Deliberately NOT `Qt.WindowType.Tool` — this is the app's main
        window and should show up in the taskbar (unlike SubtitleOverlay
        and SettingsWindow, which stay auxiliary/tool windows).
        """
        was_visible = self.isVisible()
        flags = Qt.WindowType.FramelessWindowHint
        if topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

    # -- Public API --------------------------------------------------------

    def add_message(self, msg: TranscriptMessage) -> None:
        """Append one finalized transcript line to the history."""
        row = _MessageRow(msg)
        # Insert before the trailing stretch item.
        self._message_layout.insertWidget(self._message_layout.count() - 1, row)

        while self._message_layout.count() - 1 > MAX_MESSAGES:
            item = self._message_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._auto_scroll:
            bar = self._scroll.verticalScrollBar()
            bar.setValue(bar.maximum())

    def clear(self) -> None:
        """Remove all history rows (does not stop the pipeline)."""
        while self._message_layout.count() > 1:
            item = self._message_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def set_running(self, running: bool) -> None:
        self._running = running
        self._start_stop_btn.setText(t("stop_button") if running else t("start_button"))

    def set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def request_save_geometry(self) -> None:
        g = self.geometry()
        self.geometry_changed.emit(g.x(), g.y(), g.width(), g.height())

    def restore_geometry(self, x: int, y: int, w: int, h: int) -> None:
        if w > 0 and h > 0:
            self.setGeometry(x, y, w, h)

    def restore_preferences(self, topmost: bool, auto_scroll: bool) -> None:
        """Apply persisted checkbox state before the window is first shown."""
        self._topmost_check.setChecked(topmost)
        self._auto_scroll_check.setChecked(auto_scroll)
        self._apply_topmost(topmost)
        self._auto_scroll = auto_scroll

    # -- Qt overrides --------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.request_save_geometry()

    def closeEvent(self, event) -> None:
        # Closing the console minimizes the whole app to the tray, same as
        # the old settings-window behaviour, instead of quitting outright.
        event.ignore()
        self.hide()
        self.closed.emit()

    def _on_minimize_to_tray(self) -> None:
        """Hide to tray with the same notification path as closeEvent."""
        self.hide()
        self.closed.emit()
