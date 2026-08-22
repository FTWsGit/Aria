# 繁體中文 (Traditional Chinese) - Default language

TRANSLATIONS = {
    # Window title
    "window_title": "ARIA",
    "subtitle": "即時語音轉文字工具",
    
    # Language selector
    "language": "語言",
    "lang_zh_TW": "繁體中文",
    "lang_zh_CN": "简体中文",
    "lang_en": "English",
    
    # Recognition settings
    "recognition_settings": "辨識設定",
    "mode_realtime": "即時",
    "mode_livecaptions": "內建字幕",
    "mode_realtime_desc": "純流式 Sherpa-ONNX 語音辨識",
    "mode_livecaptions_desc": "使用 Windows 11 內建即時字幕，需 22H2+ 版本",
    
    # Translation settings
    "translation_settings": "翻譯設定",
    "translation": "翻譯",
    "engine": "引擎",
    "target_lang": "譯文",
    "engine_google": "Google 雲端",
    "engine_nllb": "NLLB 本地",
    
    # Model settings
    "model_settings": "模型設定",
    "model": "模型",
    "lang": "語言",
    "manage_models": "📦 管理模型",
    
    
    
    # Start button
    "start_button": "🚀 啟動字幕",
    "stop_button": "⏹ 停止字幕",
    "loading": "🔄 載入中...",
    
    # Status
    "status_ready": "準備就緒",
    "status_running": "辨識中...",
    "status_loading_model": "正在載入模型 (首次可能較久)...",
    
    # Footer
    "footer": "支援任何系統音訊",
    
    # Model manager
    "model_manager_title": "模型管理",
    "model_path": "存放位置",
    "open_folder": "📂 開啟",
    "recognition_models": "🎙️ 語音辨識模型",
    "realtime_models": "⚡ 實時辨識模型",
    "translation_models": "🌐 翻譯模型",
    "download": "下載",
    "delete": "刪除",
    "downloading": "下載中...",
    "retry": "重試",
    "complete": "完成",
    
    # Download dialog
    "download_title": "下載模型",
    "downloading_models": "📥 正在下載模型...",
    "download_in_progress": "下載進行中",
    "download_cancel_confirm": "取消下載將刪除已下載的部分並關閉 ARIA。\n\n確定要取消嗎？",
    
    # Model not downloaded dialog
    "model_not_downloaded_title": "模型未下載",
    "model_not_downloaded_msg": "以下模型尚未下載：\n\n{models}\n\n是否立即下載？",
    
    # Overlay
    "overlay_waiting": "字幕已啟動，等待語音...",
    "overlay_translation_waiting": "等待翻譯...",
    
    # Languages
    "auto_detect": "自動偵測",
    "lang_chinese": "中文 (繁/簡)",
    "lang_english": "英文",
    "lang_japanese": "日文",
    "lang_korean": "韓文",
    "lang_cantonese": "粵語",
    "lang_spanish": "西班牙文",
    "lang_french": "法文",
    "lang_german": "德文",
    "lang_russian": "俄文",
    
    # Target languages
    "target_zh_TW": "繁體中文",
    "target_zh_CN": "简体中文",
    "target_en": "English",
    "target_ja": "日本語",
    "target_ko": "한국어",
    "target_es": "Español",
    "target_fr": "Français",
    "target_de": "Deutsch",
    
    # Translation engines
    "engine_google_free": "Google",
    "engine_baidu": "百度翻譯",
    "engine_youdao": "有道翻譯 (僅中英)",
    "engine_bing": "Bing",
    "engine_alibaba": "阿里翻譯",
    "translation_disclaimer": "",
    
    # Misc
    "yes": "是",
    "no": "否",
    "restart_required": "語言變更將在重啟程式後生效",
    "already_running": "ARIA 已經在執行中。\nARIA is already running.",
    "reset_settings": "重置設定",
    "quit_app": "退出程式",
    "reset_settings_confirm": "這將重置所有設定，包括字幕框位置。\nARIA 將會重啟。是否繼續？",
    "reset_settings_desc": "修復看不到字幕框或恢復預設設定",
    
    # Tray notifications
    "tray_minimized_title": "程式已最小化到系統托盤",
    "tray_minimized_msg": "右鍵點擊托盤圖示可以控制字幕或退出程式",
    
    # Model manager - model names
    "model_name_sherpa_zh_en": "Sherpa-ONNX",
    
    "model_name_nllb": "NLLB 翻譯模型",
    
    # Model manager - descriptions
    "model_desc_sherpa_zh_en": "流式語音辨識",
    
    "model_desc_nllb": "離線多語言翻譯 (600M 版本)",
    
    # Download status messages
    "download_status_downloading": "正在下載 {name}...",
    "download_status_verifying": "驗證中...",
    "download_status_extracting": "解壓縮中...",
    "download_status_complete": "完成",
    "download_status_error": "錯誤: {error}",
    "download_status_progress": "下載中... {downloaded}/{total}MB",
    "download_status_install_hf": "請安裝 huggingface_hub: pip install huggingface_hub",
    "cancel_download": "取消下載",
    "download_waiting": "等待下載...",
    "download_progress_note": "進度條可能不準，依網路狀況會跳動",
}
