# AGENTS.md

## Project overview

ARIA is a Windows desktop application that captures system audio or microphone input and renders live transcription in a movable PyQt6 overlay. It has three recognition paths: Precise (Faster-Whisper), Realtime (Sherpa-ONNX/Vosk), and Windows 11 Live Captions. Translation is a separate layer and can be online or local. The repository targets Python 3.10+ and Windows. See `README.md` for user-facing behavior and `CHANGELOG.md` for release history.

## Repository layout

- `src/realtime_subtitles/audio/`: Windows audio capture, buffering, and VAD.
- `src/realtime_subtitles/transcription/`: ASR backends. Keep backend-specific code here.
- `src/realtime_subtitles/translation/`: translation providers and local NLLB support.
- `src/realtime_subtitles/ui/`: PyQt6 windows, overlays, settings, and tray UI.
- `src/realtime_subtitles/livecaptions/`: Windows Live Captions integration.
- `src/realtime_subtitles/model_manager/`: model discovery/download/configuration.
- `src/realtime_subtitles/pipeline.py`: pipeline orchestration and the existing Faster-Whisper pipeline.
- `src/realtime_subtitles/vosk_pipeline.py`: Vosk-specific realtime pipeline.
- `src/realtime_subtitles/settings_manager.py`: persistent settings.
- `src/realtime_subtitles/logger.py`: application logging and transcript logging.
- `models/`: local model data in packaged/full builds; do not commit large model artifacts unless explicitly requested.
- `pyproject.toml`: package metadata, dependencies, CLI entry point, and Ruff configuration.

## Development environment

Requirements:

- Windows 10/11 for meaningful integration testing.
- Python >= 3.10; match the repository's supported interpreter versions.
- Use a virtual environment for source development.
- The packaged Full build ships an embedded Python runtime; source development does not.

Install the project in editable mode with development dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the application from the source tree with:

```powershell
python -m realtime_subtitles.main
```

The package also exposes the `aria` console entry point.

## Validation commands

Before submitting a change, run the narrowest relevant checks first, then the full available suite when practical:

```powershell
python -m ruff check .
python -m pytest
```

For a packaging/import smoke test:

```powershell
python -m pip install -e .
python -c "import realtime_subtitles; print('import ok')"
```

If a test requires Windows audio devices, GUI interaction, CUDA, or installed models, document that limitation rather than pretending the test passed. Do not fabricate test results.

## Architecture rules

1. Preserve the separation between audio capture, ASR, translation, and UI.
2. Add a new ASR engine under `transcription/` or a dedicated pipeline module; do not embed model-specific inference inside UI classes.
3. Keep translation independent from ASR so one transcript can be sent to multiple translation providers.
4. Prefer callback/event interfaces for partial and final transcript updates. Realtime backends should not block the UI thread.
5. Avoid unbounded queues in realtime paths. If a producer can outrun inference, bound the queue and prefer dropping stale audio over accumulating latency.
6. Load/warm models before starting live capture when possible; avoid causing model initialization to build an audio backlog.
7. Preserve the existing settings/logging abstractions instead of introducing another global configuration mechanism.

## Realtime ASR guidance

ARIA's existing Sherpa-ONNX realtime backend is a true streaming recognizer with partial/final-oriented callbacks and uses ONNX models. Its current built-in Sherpa configuration is Chinese/English; Vosk is used for Japanese. Do not claim that the built-in Realtime mode supports arbitrary languages without adding and testing a model/backend.

For new realtime ASR work:

- Prefer genuinely streaming architectures (e.g. streaming Transducer/FastConformer-style models) over repeatedly decoding overlapping Whisper windows.
- Prefer ONNX Runtime-compatible models for Windows/AMD-friendly deployment when quality and latency are acceptable.
- Keep model selection/configuration data separate from inference logic.
- Do not assume an ASR model is streaming merely because it is called "realtime"; verify its inference API and state handling.
- Preserve 16 kHz mono PCM expectations unless a backend explicitly requires otherwise.
- Measure end-to-end latency, not just model inference time. Include capture, VAD/buffering, decoding, translation, and rendering.
- For live captions, correctness of finalization and avoiding duplicated text matter as much as raw token latency.

## Model and dependency policy

- Do not add a heavyweight ML dependency when an existing dependency can provide the required capability.
- Do not replace an existing backend wholesale unless the task requires it; prefer adding a backend behind the current abstraction.
- Do not commit API keys, credentials, tokens, cookies, or user-specific configuration.
- Do not commit downloaded model archives or generated runtime data.
- For model URLs, versions, checksums, licenses, and language support, verify the upstream source before changing them.
- Be explicit about CPU/GPU/DirectML/CUDA assumptions; do not silently introduce CUDA-only requirements into the realtime path.

## UI and UX rules

- Keep transcription/rendering work off the Qt UI thread.
- Preserve movable/resizable subtitle and translation overlays unless the task explicitly changes the interaction model.
- Avoid blocking network calls or model downloads from the UI thread.
- Keep source subtitles and translated subtitles logically separate so either can be disabled independently.
- Follow existing localization patterns under `i18n/`; do not hard-code user-facing strings when a translation key already exists.

## Windows-specific rules

- Treat WASAPI loopback and Windows Live Captions integrations as platform-specific code; isolate platform assumptions from core pipeline logic.
- Test both system-audio and microphone paths when touching `audio/`.
- Be careful with device enumeration, default-device changes, sample rates, and resource cleanup on stop/restart.
- Do not assume administrator privileges are available or required.

## Change discipline

- Read the target file and its direct callers before editing it.
- Match existing patterns and naming before introducing a new abstraction.
- Keep diffs focused; do not perform unrelated refactors or formatting sweeps.
- If behavior changes, add or update the smallest useful automated test. For hardware/GUI/model-dependent behavior, add a unit-testable seam where practical and document the remaining manual validation.
- Update `CHANGELOG.md` only for user-visible changes that belong in the project's release history; do not turn it into a development journal.
- Update README/docs when commands, supported languages, modes, or user-visible behavior change.
- Never claim a language/model/backend is supported until it has been verified in code and, where possible, exercised end-to-end.

## Realtime/translation correctness

When changing the live pipeline, explicitly reason about these states:

- partial transcript: mutable text shown while speech is continuing;
- committed transcript: stable text that should not be translated repeatedly;
- translation draft: replaceable translation for the current partial segment;
- translation commit: stable translation corresponding to committed source text.

Avoid sending every partial ASR update to a translation API. Prefer translating finalized or deliberately debounced segments, with bounded concurrency, so translation latency cannot grow without limit.

## Before finishing a task

1. Confirm the changed modules still import cleanly.
2. Run Ruff on changed Python files and relevant tests.
3. Run the full test suite when practical.
4. For realtime changes, perform a manual smoke test with a real Windows audio source when available.
5. Report exactly what was verified, what was not, and any hardware/model limitations.
