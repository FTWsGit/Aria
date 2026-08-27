"""
Shared Qt stylesheets for ARIA UI components.

Extracted from inline CSS strings to keep Python layout code readable.
"""

# ── OpenAI overlay panel ────────────────────────────────────────────

# palette() 角色跟随系统明暗主题，避免深色模式下出现浅字浅底
OPENAI_OVERLAY_STYLE = """
    QFrame#openai_overlay {
        background-color: palette(window);
        border: 1px solid palette(mid);
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
