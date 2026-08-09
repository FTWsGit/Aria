# ARIA v2

[中文說明 / Chinese version](README_ch.md)

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" alt="Windows">
  <img src="https://img.shields.io/badge/license-GPLv3-blue.svg" alt="GPLv3 License">
</p>

ARIA is a Windows desktop app for turning system audio into live subtitles. It can listen to audio from video players, browsers, games, and calls, then show the recognised text in a movable overlay. Translation can be shown in a separate overlay when needed.

![ARIA main window](README.assets/home_page.png)

## Downloads

| Build | Size | Includes | Requirements | Download |
|---|---:|---|---|---|
| **Lite** | ~600 MB | Windows Live Captions mode and translation overlay | Windows 11, version 22H2 or later | [Google Drive](https://drive.google.com/drive/folders/1rRQrj0IPX7rnQxA30WvmxhH-5c6fWZa8?usp=drive_link) · [Baidu](https://pan.baidu.com/s/1KkSlAv7X5yi90hTYuWZoPQ?pwd=j5ip) |
| **Full** | ~7.6 GB | Precise, Realtime, and Live Captions modes; offline models | Windows 10 or 11; NVIDIA GPU recommended for Precise mode | [Google Drive](https://drive.google.com/drive/folders/1rdxunARIa3-68VV4xAKlbzh_dv_wI130?usp=drive_link) · [Baidu](https://pan.baidu.com/s/1yGc-pU6DdPFw8po60ubI3w?pwd=r2m6) |

Choose Lite if Windows Live Captions covers your use case. Choose Full when you need local speech recognition, offline models, or more control over recognition settings.

## Getting started

1. Download and extract the package.
2. Start **`ARIA.bat`** in the Full package, or **`run_lite.bat`** in the Lite package.
3. Select a recognition mode in the Full package, configure translation if required, then select **Start**.

The package includes its own Python runtime, so a separate Python installation is not required.

## Recognition modes

| Mode | Engine | Good fit | Notes |
|---|---|---|---|
| **Precise** | Faster-Whisper | Recorded video, talks, and other accuracy-sensitive audio | Works best with an NVIDIA GPU. |
| **Realtime** | Sherpa-ONNX / Vosk | Conversations and streams where fast updates matter | Supports Chinese/English with Sherpa-ONNX and Japanese with Vosk. |
| **Live Captions** | Windows 11 Live Captions | Everyday playback, meetings, and systems without CUDA | Uses the Windows feature; no NVIDIA GPU or CUDA setup is needed. |

The Full package can capture Windows system audio or a microphone. Lite is intentionally limited to Live Captions mode.

## Translation overlay

ARIA can send recognised text to Google Translate, Bing Translator, Youdao, or the local NLLB model included with the Full package. The original captions stay in the source overlay while the translated text is shown separately.

![Example of ARIA's translation overlay](README.assets/trans_effect.png)

Online translation services are convenient, but they can be rate-limited or change without notice. Use the local NLLB model when offline operation and predictable availability are more important.

## Languages

| Language | Precise | Realtime | Live Captions |
|---|:---:|:---:|:---:|
| Chinese | ✓ | ✓ | ✓ |
| English | ✓ | ✓ | ✓ |
| Japanese | ✓ | ✓ | ✓ |
| Korean | ✓ | — | ✓ |
| Spanish, French, and more | ✓ | — | ✓ |

Live Captions language availability is determined by the Windows feature. Precise mode supports the broadest set of languages.

## Included models in the Full package

| Model | Purpose | Approx. size | Languages |
|---|---|---:|---|
| Whisper Large-v3 | Precise transcription | 3 GB | Multilingual |
| Sherpa-ONNX bilingual | Realtime transcription | 500 MB | Chinese, English |
| Vosk Japanese | Realtime transcription | 1 GB | Japanese |
| NLLB | Local translation | 1.2 GB | Multilingual |

## Logs and settings

Settings are saved between runs. The application can write a detailed session log and a smaller transcript-only log, and the log timezone can be selected from the settings window. The subtitle and translation overlays can be moved and resized independently.

## Project layout

```text
ARIA-v2/
├── python/          # Embedded Python runtime for the Full package
├── src/             # Full-package application source
├── models/          # Offline models for the Full package
├── ARIA.bat         # Full-package launcher
└── ARIA-v2-lite/
    ├── python/      # Embedded Python runtime for Lite
    ├── src/         # Lite application source
    └── run_lite.bat # Lite-package launcher
```

## License

ARIA is released under the [GNU General Public License v3.0](LICENSE).

## Acknowledgements

- [Faster Whisper](https://github.com/SYSTRAN/faster-whisper)
- [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx)
- [Vosk](https://alphacephei.com/vosk/)
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch)

## Contact

- GitHub: [@sayksii](https://github.com/sayksii)
- Email: mark42967151@gmail.com
