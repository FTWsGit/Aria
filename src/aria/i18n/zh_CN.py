# 简体中文 (Simplified Chinese)

TRANSLATIONS = {
    # Window title
    "window_title": "ARIA",
    "subtitle": "实时语音转文字工具",
    
    # Language selector
    "language": "语言",
    "lang_zh_TW": "繁體中文",
    "lang_zh_CN": "简体中文",
    "lang_en": "English",
    
    # Recognition settings
    "recognition_settings": "识别设置",
    "mode_realtime": "即时",
    "mode_livecaptions": "内建字幕",
    "mode_realtime_desc": "纯流式 Sherpa-ONNX 语音识别",
    "mode_livecaptions_desc": "使用 Windows 11 内建实时字幕，需 22H2+ 版本",
    
    # Translation settings
    "translation_settings": "翻译设置",
    "translation": "翻译",
    "engine": "引擎",
    "target_lang": "译文",
    "engine_google": "Google 云端",
    "engine_nllb": "NLLB 本地",
    
    # Model settings
    "model_settings": "模型设置",
    "model": "模型",
    "lang": "语言",
    "manage_models": "📦 管理模型",
    
    
    
    # Start button
    "start_button": "🚀 启动字幕",
    "stop_button": "⏹ 停止字幕",
    "loading": "🔄 载入中...",
    
    # Status
    "status_ready": "准备就绪",
    "status_running": "识别中...",
    "status_loading_model": "正在载入模型 (首次可能较久)...",
    
    # Footer
    "footer": "支持任何系统音频",
    
    # Model manager
    "model_manager_title": "模型管理",
    "model_path": "存放位置",
    "open_folder": "📂 打开",
    "recognition_models": "🎙️ 语音识别模型",
    "realtime_models": "⚡ 实时识别模型",
    "translation_models": "🌐 翻译模型",
    "download": "下载",
    "delete": "删除",
    "downloading": "下载中...",
    "retry": "重试",
    "complete": "完成",
    
    # Download dialog
    "download_title": "下载模型",
    "downloading_models": "📥 正在下载模型...",
    "download_in_progress": "下载进行中",
    "download_cancel_confirm": "取消下载将删除已下载的部分并关闭 ARIA。\n\n确定要取消吗？",
    
    # Model not downloaded dialog
    "model_not_downloaded_title": "模型未下载",
    "model_not_downloaded_msg": "以下模型尚未下载：\n\n{models}\n\n是否立即下载？",
    
    # Overlay
    "overlay_waiting": "字幕已启动，等待语音...",
    "overlay_translation_waiting": "等待翻译...",
    
    # Languages
    "auto_detect": "自动检测",
    "lang_chinese": "中文 (繁/简)",
    "lang_english": "英文",
    "lang_japanese": "日文",
    "lang_korean": "韩文",
    "lang_cantonese": "粤语",
    "lang_spanish": "西班牙文",
    "lang_french": "法文",
    "lang_german": "德文",
    "lang_russian": "俄语",
    
    # Target languages
    "target_zh_TW": "繁体中文",
    "target_zh_CN": "简体中文",
    "target_en": "English",
    "target_ja": "日本語",
    "target_ko": "한국어",
    "target_es": "Español",
    "target_fr": "Français",
    "target_de": "Deutsch",
    
    # Translation engines
    "engine_google_free": "Google",
    "engine_baidu": "百度翻译",
    "engine_youdao": "有道翻译 (仅中英)",
    "engine_bing": "Bing",
    "engine_alibaba": "阿里翻译",
    "translation_disclaimer": "",
    
    # Misc
    "yes": "是",
    "no": "否",
    "restart_required": "语言更改将在重启程序后生效",
    "already_running": "ARIA 已在运行中。\nARIA is already running.",
    "reset_settings": "重置设置",
    "quit_app": "退出程序",
    "reset_settings_confirm": "这将重置所有设置，包括字幕框位置。\nARIA 将会重启。是否继续？",
    "reset_settings_desc": "修复看不到字幕框或恢复默认设置",
    
    # Tray notifications
    "tray_minimized_title": "程序已最小化到系统托盘",
    "tray_minimized_msg": "右键点击托盘图标可以控制字幕或退出程序",
    
    # Model manager - model names
    "model_name_sherpa_zh_en": "Sherpa-ONNX",
    
    "model_name_nllb": "NLLB 翻译模型",
    
    # Model manager - descriptions
    "model_desc_sherpa_zh_en": "流式语音识别",
    
    "model_desc_nllb": "离线多语言翻译 (600M 版本)",
    
    # Download status messages
    "download_status_downloading": "正在下载 {name}...",
    "download_status_verifying": "验证中...",
    "download_status_extracting": "解压缩中...",
    "download_status_complete": "完成",
    "download_status_error": "错误: {error}",
    "download_status_progress": "下载中... {downloaded}/{total}MB",
    "download_status_install_hf": "请安装 huggingface_hub: pip install huggingface_hub",
    "cancel_download": "取消下载",
    "download_waiting": "等待下载...",
    "download_progress_note": "进度条可能不准，会随网络状况跳动",
}
