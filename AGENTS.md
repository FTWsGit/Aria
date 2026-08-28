# AGENTS.md

## Project Overview

ARIA is a Windows desktop app that captures system audio or microphone input and renders transcription text in real time in a movable PyQt6 overlay window. There are currently two recognition paths: Sherpa-ONNX streaming recognition and the Windows 11 built-in captions. Translation is a separate layer, supporting both online and local. The project requires Python 3.10+ and only supports Windows.

## Development Environment

Requirements:

- Windows 10/11.
- Python >= 3.10.
- Use uv to manage the virtual environment and dependencies.

Run the app:

```powershell
uv run aria
```

## Verification Commands

Always use uv. Before committing, run the most relevant checks first, then the full suite:

```powershell
uv run ruff format
uv run ruff check --fix
uv run pytest
```

Packaging/import test:

```powershell
uv run python -c "import aria; print('import ok')"
```

If a test requires Windows audio devices, GUI interaction, CUDA, or an installed model, note the limitation — do not fake test results.


## Comment/Documentation Discipline

- Comments/docs state only **what was it and why**. Do not write "how it was figured out, what pitfalls were hit historically, why another approach was not used". Feasible vs infeasible comparisons, pitfall history, and rejected alternatives belong in git log / issue trackers, not in comments
- Never mention or reference any external document in comments — no `see xxx.mdc for details` or `see the xxx domain docs`
- A rule that can be stated in one sentence **should not be expanded into a paragraph of argument**. The argument is explained to the user verbally, not written into the file; an AI reading the corresponding code/types will understand why on its own — the comment does not need to explain it first
- Do not add explanatory comments to existing code

- Docs state only "what the project is" — not the user's requirements, not outlook, not the discussion process, not alternative approaches, not the content of other documents
- The `description` skeleton hint states only **what it is and when to read it**. No writing-theory, no "what it is not".

## Architecture Rules

- Keep audio capture, ASR, translation, and UI separated.

## UI and UX Rules

- Keep transcription/rendering work off the Qt UI thread.
- Keep the subtitle and translation overlay windows movable/resizable, unless the task explicitly changes the interaction model.
- Avoid blocking network calls or model downloads on the UI thread.
- Keep the source-subtitle and translated-subtitle logic separate so either can be disabled independently.
- Follow the localization pattern under `i18n/`; do not hardcode user-visible strings when a translation key exists.

## Windows-Specific Rules

- Treat WASAPI loopback and the Windows built-in captions integration as platform-specific code; isolate platform assumptions from core pipeline logic.
- When modifying `audio/`, test both the system-audio and microphone paths.
- Be careful with device enumeration, default-device changes, sample rates, and resource cleanup on stop/restart.
- Do not assume that admin privileges are required or have been granted.

## Working Rules(IMPORTANT!)
- Use Chinese to talk with user
- Never work with project when user did not ask for it
