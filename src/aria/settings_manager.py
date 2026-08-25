"""
Settings persistence for Real-time Subtitles.

Saves and loads user settings to a JSON file.
"""

import json
from pathlib import Path

# 设置项索引（全仓库实际使用的 key）
# === 已登记（在 DEFAULT_SETTINGS 中有默认值） ===
#   mode              — 识别模式 (asr / livecaptions)
#   min_duration      — 最小显示时长 (ms)
#   enable_translation — 是否启用翻译
#   translation_engine — 翻译引擎 (bing / google_free / openai / youdao)
#   target_language   — 目标语言代码
#   audio_source      — 音频源 (system / microphone)
#   timezone          — 时区
#   overlay_visible   — 悬浮窗可见性
#   log_verbosity     — 日志详略
#   openai_endpoint   — OpenAI 兼容端点
#   openai_api_key    — OpenAI API Key
#   openai_model_name — OpenAI 模型名
#   openai_temperature — OpenAI 温度
#   openai_max_tokens — OpenAI 最大 token 数
#   openai_system_prompt — OpenAI 系统提示词
#   ui_language       — UI 语言代码
#
# === 未登记（在各处用 .get() 兜底，无 DEFAULT_SETTINGS 条目） ===
#   model_id          — ASR 模型 ID（settings_window.py / app.py）
#   language          — UI 语言（settings_window.py 保存时写入，i18n 读时用 ui_language）
#   console_topmost   — 控制台窗口置顶（app.py）
#   console_auto_scroll — 控制台自动滚动（app.py）
#   console_x         — 控制台窗口 X 坐标（app.py）
#   console_y         — 控制台窗口 Y 坐标（app.py）
#   console_w         — 控制台窗口宽度（app.py）
#   console_h         — 控制台窗口高度（app.py）
#   overlay_x         — 悬浮窗 X 坐标（subtitle_overlay.py，position_key="overlay"）
#   overlay_y         — 悬浮窗 Y 坐标（subtitle_overlay.py，position_key="overlay"）

class SettingsManager:
    """Manages saving and loading user settings."""

    DEFAULT_SETTINGS = {
        "mode": "asr",
        "min_duration": 100,
        "enable_translation": True,
        "translation_engine": "bing",
        "target_language": "zho_Hans",
        "audio_source": "system",
        "timezone": "system",
        "overlay_visible": True,
        "log_verbosity": "verbose",
        "openai_endpoint": "http://127.0.0.1:1234/v1",
        "openai_api_key": "",
        "openai_model_name": "",
        "openai_temperature": 0.2,
        "openai_max_tokens": 1024,
        "openai_system_prompt": "",
        "ui_language": "zh_CN",
    }

    def __init__(self):
        """Initialize settings manager."""
        self._config_dir = Path.home() / ".config" / "aria"
        self._config_file = self._config_dir / "settings.json"
        self._settings = self.DEFAULT_SETTINGS.copy()
        self._load()

    def _load(self) -> None:
        """Load settings from file."""
        if self._config_file.exists():
            try:
                with open(self._config_file, encoding="utf-8") as f:
                    saved = json.load(f)
                # Merge with defaults (in case new settings were added)
                self._settings = {**self.DEFAULT_SETTINGS, **saved}
                from .logger import info

                info(f"Settings: Loaded from {self._config_file}")
            except Exception as e:
                from .logger import warning

                warning(f"Settings: Failed to load: {e}")
                self._settings = self.DEFAULT_SETTINGS.copy()
        else:
            from .logger import info

            info("Settings: Using defaults (no saved settings)")

    def save(self) -> None:
        """Save settings to file."""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            from .logger import debug

            debug(f"Settings: Saved to {self._config_file}")
        except Exception as e:
            from .logger import error

            error(f"Settings: Failed to save: {e}")

    def get(self, key: str, default=None):
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a setting value."""
        self._settings[key] = value

    def update(self, settings: dict) -> None:
        """Update multiple settings at once."""
        self._settings.update(settings)

    def get_all(self) -> dict:
        """Get all settings."""
        return self._settings.copy()


# Global instance
_instance: SettingsManager | None = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _instance
    if _instance is None:
        _instance = SettingsManager()
    return _instance
