# ARIA v2

[English version](README.md)

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" alt="Windows">
  <img src="https://img.shields.io/badge/license-GPLv3-blue.svg" alt="GPLv3 License">
</p>

ARIA 是一套 Windows 实时字幕工具。它能捕获系统播放的声音，将视频、浏览器、游戏或通话中的语音转为字幕，并以可拖动的悬浮窗口显示；需要时也能另外显示翻译字幕。

![ARIA 主窗口](README.assets/home_page.png)

## 下载

| 版本 | 大小 | 内容 | 系统要求 | 下载 |
|---|---:|---|---|---|
| **Lite** | 约 600 MB | Windows 实时辅助字幕模式与翻译悬浮窗口 | Windows 11 22H2 或更高版本 | [Google Drive](https://drive.google.com/drive/folders/1rRQrj0IPX7rnQxA30WvmxhH-5c6fWZa8?usp=drive_link) · [百度网盘](https://pan.baidu.com/s/1KkSlAv7X5yi90hTYuWZoPQ?pwd=j5ip) |
| **完整版** | 约 7.6 GB | 精确、实时、实时辅助字幕三种模式与离线模型 | Windows 10 或 11；精确模式建议使用 NVIDIA 显卡 | [Google Drive](https://drive.google.com/drive/folders/1rdxunARIa3-68VV4xAKlbzh_dv_wI130?usp=drive_link) · [百度网盘](https://pan.baidu.com/s/1yGc-pU6DdPFw8po60ubI3w?pwd=r2m6) |

如果 Windows 内置的实时辅助字幕已经符合需求，请选择 Lite。需要本地语音识别、离线模型或更多识别设置时，再选择完整版。

## 快速开始

1. 下载并解压缩套件。
2. 完整版请运行 **`ARIA.bat`**；Lite 请运行 **`run_lite.bat`**。
3. 完整版选择识别模式、按需开启翻译后，点击 **Start**。

套件已内置 Python 运行环境，无需另外安装 Python。

## 识别模式

| 模式 | 引擎 | 适合场景 | 说明 |
|---|---|---|---|
| **精确模式** | Faster-Whisper | 预录视频、演讲和重视准确度的内容 | 建议使用 NVIDIA 显卡。 |
| **实时模式** | Sherpa-ONNX / Vosk | 对话与直播等需要快速更新的内容 | Sherpa-ONNX 支持中英文，Vosk 支持日文。 |
| **实时辅助字幕模式** | Windows 11 Live Captions | 日常播放、会议，以及没有 CUDA 的电脑 | 使用 Windows 内置功能，无需配置 NVIDIA 显卡或 CUDA。 |

完整版可以捕获 Windows 系统音频或麦克风音频。Lite 为了保持精简，仅提供实时辅助字幕模式。

## 翻译悬浮窗口

ARIA 可以使用 Google 翻译、Bing 翻译、有道翻译，或完整版内置的本地 NLLB 模型。原文与译文会分开显示，阅读时不会互相覆盖。

![ARIA 翻译字幕效果](README.assets/trans_effect.png)

在线翻译服务使用方便，但可能受到服务变动或请求频率限制。若在意离线使用与稳定性，建议使用本地 NLLB 模型。

## 语言支持

| 语言 | 精确模式 | 实时模式 | 实时辅助字幕模式 |
|---|:---:|:---:|:---:|
| 中文 | ✓ | ✓ | ✓ |
| 英文 | ✓ | ✓ | ✓ |
| 日文 | ✓ | ✓ | ✓ |
| 韩文 | ✓ | — | ✓ |
| 西班牙文、法文等 | ✓ | — | ✓ |

实时辅助字幕模式的可用语言由 Windows 功能决定；精确模式支持的语言最完整。

## 完整版内置模型

| 模型 | 用途 | 大约大小 | 语言 |
|---|---|---:|---|
| Whisper Large-v3 | 精确转写 | 3 GB | 多语言 |
| Sherpa-ONNX 双语模型 | 实时转写 | 500 MB | 中文、英文 |
| Vosk 日文模型 | 实时转写 | 1 GB | 日文 |
| NLLB | 本地翻译 | 1.2 GB | 多语言 |

## 设置与日志

设置会保留到下次启动。程序可以写入详细的运行日志，以及只保留字幕与翻译内容的简要日志；也能在设置窗口选择日志时区。原文与翻译悬浮窗口都可以独立移动和调整大小。

## 项目结构

```text
ARIA-v2/
├── python/          # 完整版内置的 Python 运行环境
├── src/             # 完整版源代码
├── models/          # 完整版离线模型
├── ARIA.bat         # 完整版启动程序
└── ARIA-v2-lite/
    ├── python/      # Lite 内置的 Python 运行环境
    ├── src/         # Lite 源代码
    └── run_lite.bat # Lite 启动程序
```

## 许可证

ARIA 采用 [GNU General Public License v3.0](LICENSE) 许可证。

## 致谢

- [Faster Whisper](https://github.com/SYSTRAN/faster-whisper)
- [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx)
- [Vosk](https://alphacephei.com/vosk/)
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch)

## 联系方式

- GitHub: [@sayksii](https://github.com/sayksii)
- Email: mark42967151@gmail.com
