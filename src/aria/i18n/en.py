# English

TRANSLATIONS = {
    # Window title
    "window_title": "ARIA",
    "subtitle": "Real-time Speech-to-Text Tool",
    # Language selector
    "language": "Language",
    "lang_zh_CN": "简体中文",
    "lang_en": "English",
    # Recognition settings
    "recognition_settings": "Recognition",
    "mode_asr": "ASR Transcribe",
    "mode_livecaptions": "Windows Live Captions",
    "mode_asr_desc": "Streaming Transcribe via ASR Model",
    "mode_livecaptions_desc": "Use Windows 11 built-in Live Captions, requires 22H2+",
    # Translation settings
    "translation_settings": "Translation",
    "translation": "Translate",
    "engine": "Engine",
    "target_lang": "Target",
    "translation_context_label": "Context sentences (0=off)",
    "engine_google": "Google Cloud",
    # Model settings
    "model_settings": "Model Settings",
    "model": "Model",
    "lang": "Language",
    "manage_models": "📦 Manage Models",
    # Start button
    "start_button": "Start Subtitles",
    "stop_button": "⏹ Stop Subtitles",
    "loading": "🔄 Loading...",
    # Status
    "status_ready": "Ready",
    "status_running": "Recognizing...",
    "status_loading_model": "Loading model (may take a while first time)...",
    # Footer
    "footer": "Supports any system audio",
    # Model manager
    "model_manager_title": "Model Manager",
    "model_path": "Location",
    "open_folder": "📂 Open",
    "recognition_models": "🎙️ Speech Recognition Models",
    "translation_models": "🌐 Translation Models",
    "download": "Download",
    "delete": "Delete",
    "downloading": "Downloading...",
    "retry": "Retry",
    "complete": "Complete",
    # Download dialog
    "download_title": "Download Model",
    "downloading_models": "📥 Downloading models...",
    "download_in_progress": "Download in Progress",
    "download_cancel_confirm": "Cancelling will delete the partial download and close ARIA.\n\nAre you sure you want to cancel?",
    # Model not downloaded dialog
    "model_not_downloaded_title": "Model Not Downloaded",
    "model_not_downloaded_msg": "The following models are not downloaded:\n\n{models}\n\nDownload now?",
    # Overlay
    "overlay_waiting": "Subtitles started, waiting for audio...",
    "overlay_translation_waiting": "Waiting for translation...",
    # Languages
    "auto_detect": "Auto Detect",
    "lang_chinese": "Chinese (Trad/Simp)",
    "lang_english": "English",
    "lang_japanese": "Japanese",
    "lang_korean": "Korean",
    "lang_cantonese": "Cantonese",
    "lang_spanish": "Spanish",
    "lang_french": "French",
    "lang_german": "German",
    "lang_russian": "Russian",
    # Target languages
    "target_zh_TW": "Traditional Chinese",
    "target_zh_CN": "Simplified Chinese",
    "target_en": "English",
    "target_ja": "Japanese",
    "target_ko": "Korean",
    "target_es": "Spanish",
    "target_fr": "French",
    "target_de": "German",
    # Translation engines
    "engine_google_free": "Google",
    "engine_youdao": "Youdao (CN↔EN only)",
    "engine_openai": "OpenAI-compatible",
    "engine_bing": "Bing",
    "translation_disclaimer": "",
    # Misc
    "yes": "Yes",
    "no": "No",
    "restart_required": "Language change will take effect after restart",
    "already_running": "ARIA is already running.",
    "reset_settings": "Reset Settings",
    "quit_app": "Quit",
    "reset_settings_confirm": "This will reset all settings including overlay positions.\nARIA will restart. Continue?",
    "reset_settings_desc": "Fix can't see overlay or restore defaults",
    # Tray notifications
    "tray_minimized_title": "Minimized to system tray",
    "tray_minimized_msg": "Right-click the tray icon to control subtitles or quit",
    # Download status messages
    "download_status_downloading": "Downloading {name}...",
    "download_status_verifying": "Verifying...",
    "download_status_extracting": "Extracting...",
    "download_status_complete": "Complete",
    "download_status_error": "Error: {error}",
    "download_status_progress": "Downloading... {downloaded}/{total}MB",
    "download_status_install_hf": "Please install huggingface_hub: pip install huggingface_hub",
    "cancel_download": "Cancel Download",
    "download_waiting": "Waiting to download...",
    "download_progress_note": "Progress may be inaccurate and can jump based on network",
    # Error messages
    "error_asr_backend_failed": "ASR service error, stopped automatically",
    "error_translation_unavailable": "Translation service temporarily unavailable",
    "error_pipeline_startup": "Failed to start ASR service, check configuration",
    "error_no_models_available": "No recognition models available. Please download a model in Model Manager first.",
    "model_required_download_title": "Model Not Downloaded",
    "model_required_download_msg": "Model '{model_id}' has not been downloaded.\nPlease download it in Model Manager first.",
    # Tray menu
    "tray_show_settings": "Show Main Window",
    "tray_toggle_subtitles": "Start/Stop Subtitles",
    "tray_quit": "Quit",
    # Audio source
    "audio_source_system": "System Audio",
    "audio_source_mic": "Microphone (System Default)",
    "audio_source_label": "Audio Source:",
    "timezone_label": "Timezone (IANA):",
    # Overlay toggle
    "overlay_hide": "Hide Subtitle Overlay",
    "overlay_show": "Show Subtitle Overlay",
    # Mic device
    "mic_device_label": "Microphone: {name}",
    "mic_default_device_label": "Microphone (default device): {name}",
    # Download
    "download_status_waiting": "Downloading, please wait...",
    # Streaming models section
    "streaming_models": "Streaming Models",
    "open_models_folder": "Open Models Folder",
    "close": "Close",
    "configure": "Configure",
    "back": "Back",
    # Console window
    "console_title": "ARIA Console",
    "btn_clear": "Clear",
    "btn_settings": "Settings",
    "btn_quit": "Quit",
    "btn_minimize_tray": "Minimize to Tray",
    "chk_topmost": "Always on Top",
    "chk_auto_scroll": "Auto Scroll",
    # Settings window tabs
    "tab_recognition": "Recognition",
    "tab_translation": "Translation",
    "tab_general": "General",
    "settings_window_title": "ARIA Settings",
    # Model tab
    "tab_models": "Models",
    "downloaded": "Downloaded",
    "not_downloaded": "Not downloaded",
    "delete_model_confirm": 'Delete model "{name}"?\nThe downloaded files will be removed from disk.',
    # VAD
    "vad_enable_label": "Enable VAD (skip silence, sentence-based commit)",
    "vad_model_label": "VAD model",
    "vad_advanced_label": "Advanced",
    "vad_threshold_label": "Speech threshold",
    "vad_min_silence_label": "Min silence duration (s)",
    "vad_min_speech_label": "Min speech duration (s)",
    "vad_max_speech_label": "Max speech duration (s)",
    "vad_split_punctuation_label": "Split segment by punctuation",
    "warning_vad_unavailable_fallback": "VAD model unavailable, falling back to non-VAD mode",
}
