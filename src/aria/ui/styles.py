"""
Shared Qt stylesheets for ARIA UI components.

Extracted from inline CSS strings to keep Python layout code readable.
"""

# ── OpenAI overlay panel ────────────────────────────────────────────

OPENAI_OVERLAY_STYLE = """
    QFrame#openai_overlay {
        background-color: #ffffff;
        border: 1px solid #d0d0d0;
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
