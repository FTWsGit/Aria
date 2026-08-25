"""
Shared Qt stylesheets for ARIA UI components.

Extracted from inline CSS strings to keep Python layout code readable.
"""

# ── Settings window main stylesheet ─────────────────────────────────

MAIN_STYLESHEET = """
    QMainWindow {
        background-color: #f3f3f3;
    }
    QLabel {
        color: #1a1a1a;
    }
    QFrame#card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
    QFrame#title_label {
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton {
        background-color: #0078D4;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 18px;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #106EBE;
    }
    QPushButton:pressed {
        background-color: #005A9E;
    }
    QPushButton#secondary {
        background-color: #ffffff;
        border: 1px solid #c0c0c0;
        color: #1a1a1a;
    }
    QPushButton#secondary:hover {
        background-color: #f0f0f0;
    }
    QComboBox {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        padding: 6px 10px;
        min-width: 180px;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 20px;
        border: none;
        background: transparent;
    }
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #1a1a1a;
        selection-background-color: #0078D4;
        selection-color: white;
        border: 1px solid #c0c0c0;
    }
    QCheckBox {
        color: #1a1a1a;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 3px;
        border: 1px solid #a0a0a0;
        background-color: #ffffff;
    }
    QCheckBox::indicator:hover {
        border-color: #0078D4;
    }
    QCheckBox::indicator:checked {
        background-color: #0078D4;
        border-color: #0078D4;
        image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiI+PHBhdGggZD0iTTMgOC41TDYuNSAxMkwxMyA0IiBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMiIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
    }
    QCheckBox::indicator:checked:hover {
        background-color: #106EBE;
        border-color: #106EBE;
    }
    QComboBox:hover {
        border-color: #0078D4;
    }
    QTabWidget::pane {
        border: 1px solid #d0d0d0;
        top: -1px;
        background: #ffffff;
    }
    QTabBar::tab {
        background: #e8e8e8;
        color: #444444;
        padding: 8px 18px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background: #ffffff;
        color: #0078D4;
        font-weight: bold;
    }
    QTabBar::tab:hover {
        background: #f0f0f0;
    }
    QScrollBar:vertical {
        background-color: transparent;
        width: 10px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:vertical {
        background-color: rgba(0, 0, 0, 0.18);
        border-radius: 5px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: rgba(0, 0, 0, 0.30);
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
"""

# ── OpenAI overlay panel ────────────────────────────────────────────

OPENAI_OVERLAY_STYLE = """
    QFrame#openai_overlay {
        background-color: #ffffff;
        border: 1px solid #d0d0d0;
        border-radius: 8px;
    }
    QLabel {
        color: #1a1a1a;
        font-size: 13px;
    }
    QLineEdit, QDoubleSpinBox, QSpinBox {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        padding: 6px 10px;
    }
    QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
        border-color: #0078D4;
    }
    QSpinBox::up-button, QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        height: 14px;
        background-color: #e8e8e8;
        border-radius: 3px;
        margin: 2px 2px 0 0;
    }
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
        background-color: #0078D4;
    }
    QSpinBox::down-button, QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        height: 14px;
        background-color: #e8e8e8;
        border-radius: 3px;
        margin: 0 2px 2px 0;
    }
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
        background-color: #0078D4;
    }
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 6px solid #444444;
        width: 0px;
        height: 0px;
    }
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid #444444;
        width: 0px;
        height: 0px;
    }
"""

# ── Subtitle overlay ────────────────────────────────────────────────

SUBTITLE_CONTAINER_STYLE = """
    #container {
        background-color: rgba(42, 42, 42, 230);
        border-radius: 12px;
    }
"""

SUBTITLE_SOURCE_STYLE = """
    QTextEdit {
        color: rgba(255, 255, 255, 140);
        font-size: 18px;
        font-weight: normal;
        background: transparent;
        border: none;
    }
"""

SUBTITLE_TRANSLATION_STYLE = """
    QTextEdit {
        color: white;
        font-size: 24px;
        font-weight: bold;
        background: transparent;
        border: none;
    }
"""
