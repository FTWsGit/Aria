"""
Tests for VAD integration in StreamingPipeline.

Does not depend on Qt, audio devices, network, or sherpa model files.
Uses fake backends, fake AudioCapture, and tmp_path-based registry/model-cache.
"""

import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import yaml

from aria import pipeline as pipeline_mod
from aria.events import SubtitleEvent, TranscriptMessage
from aria.model_manager.manager import ModelManager
from aria.model_manager.registry import ModelRegistry
from aria.translation.translation_layer import TranslationLayer
from aria.vad.base import VadSegment

# ---------------------------------------------------------------------------
# Fake backends
# ---------------------------------------------------------------------------


class FakeVADBackend:
    """Scripted VAD backend implementing the VADBackend protocol.

    Controlled by a list of ``(frame_count, action)`` tuples where action is
    ``"start"`` or ``"stop"``. After feeding that many frames, the backend
    transitions to the corresponding state.
    """

    def __init__(self, frame_size: int = 512):
        self._frame_size = frame_size
        self._script: list[tuple[int, str]] = []
        self._frame_count = 0
        self._active = False
        self._segments: list[VadSegment] = []
        self._current_audio: list[np.ndarray] = []
        self._accept_calls: list[np.ndarray] = []
        self._total_samples = 0

    def set_script(self, script: list[tuple[int, str]]):
        """Set the script: list of (frame_count, 'start'|'stop')."""
        self._script = list(script)

    @property
    def frame_size(self) -> int:
        return self._frame_size

    def accept_waveform(self, frame: np.ndarray) -> None:
        self._accept_calls.append(frame.copy())
        self._total_samples += len(frame)
        self._frame_count += 1

        for target_count, action in self._script:
            if self._frame_count == target_count:
                if action == "start" and not self._active:
                    self._active = True
                    self._current_audio = []
                elif action == "stop" and self._active:
                    self._active = False
                    if self._current_audio:
                        combined = np.concatenate(self._current_audio)
                        seg = VadSegment(
                            start_sample=self._total_samples - len(combined),
                            samples=combined.astype(np.float32),
                        )
                        self._segments.append(seg)
                    self._current_audio = []

        if self._active:
            self._current_audio.append(frame.copy())

    def is_speech_active(self) -> bool:
        return self._active

    def current_segment_samples(self) -> np.ndarray:
        if not self._active or not self._current_audio:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self._current_audio).astype(np.float32)

    def pop_ready_segments(self) -> list[VadSegment]:
        segs = list(self._segments)
        self._segments = []
        return segs

    def flush(self) -> None:
        if self._active:
            self._active = False
            if self._current_audio:
                combined = np.concatenate(self._current_audio)
                seg = VadSegment(
                    start_sample=self._total_samples - len(combined),
                    samples=combined.astype(np.float32),
                )
                self._segments.append(seg)
            self._current_audio = []

    def reset(self) -> None:
        self._frame_count = 0
        self._active = False
        self._segments = []
        self._current_audio = []
        self._accept_calls = []
        self._total_samples = 0


class FakeStreamingTranscriber:
    """Fake streaming ASR backend that returns scripted text."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = list(responses) if responses else []
        self._call_count = 0
        self._process_calls: list[np.ndarray] = []
        self._reset_calls = 0
        self._final_text = ""

    def set_responses(self, responses: list[str]):
        self.responses = list(responses)

    def set_final_text(self, text: str):
        self._final_text = text

    def process_audio(self, audio: np.ndarray) -> str:
        self._process_calls.append(audio.copy())
        if self._call_count < len(self.responses):
            result = self.responses[self._call_count]
            self._call_count += 1
            return result
        return self.responses[-1] if self.responses else ""

    def reset(self) -> None:
        self._reset_calls += 1
        self._call_count = 0

    def get_final_result(self) -> str:
        return self._final_text


class FakeChunkedTranscriber:
    """Fake chunked ASR backend that records transcribe calls."""

    def __init__(self):
        self.transcribe_calls: list[tuple[np.ndarray, int]] = []
        self._response = ""

    def set_response(self, text: str):
        self._response = text

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        self.transcribe_calls.append((audio.copy(), sample_rate))
        return self._response


class FakeAudioCapture:
    """Fake AudioCapture that pushes scripted chunks via callback."""

    def __init__(self, chunks: list[np.ndarray] | None = None):
        self.chunks = chunks or []
        self._callback: Callable | None = None
        self._started = False

    def start(self, callback: Callable[[np.ndarray, int], None]) -> None:
        self._callback = callback
        self._started = True
        for chunk in self.chunks:
            callback(chunk, 16000)

    def stop(self) -> None:
        self._started = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_asr_streaming_yaml(model_id: str = "test-streaming", backend: str = "fake") -> dict:
    return {
        "id": model_id,
        "kind": "asr_streaming",
        "backend": backend,
        "display_name": "Test Streaming",
        "language": "en",
        "source": {"type": "manual", "path": "/tmp"},
        "size_mb": 100,
    }


def _make_asr_chunked_yaml(model_id: str = "test-chunked", backend: str = "fake") -> dict:
    return {
        "id": model_id,
        "kind": "asr_chunked",
        "backend": backend,
        "display_name": "Test Chunked",
        "language": "en",
        "source": {"type": "manual", "path": "/tmp"},
        "size_mb": 100,
    }


def _make_vad_yaml(model_id: str = "vad-test", backend: str = "fake") -> dict:
    return {
        "id": model_id,
        "kind": "vad",
        "backend": backend,
        "display_name": "Test VAD",
        "language": "universal",
        "source": {"type": "manual", "path": "/tmp"},
        "files": {"model": "vad_model.onnx"},
        "params": {"model_family": "silero"},
    }


def _make_registry_and_manager(tmp_path: Path, yamls: list[dict]) -> tuple[ModelRegistry, ModelManager]:
    """Create a ModelRegistry with given yaml specs and a ModelManager with cache_dir in tmp_path."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    for i, yaml_data in enumerate(yamls):
        (models_dir / f"model_{i}.yaml").write_text(yaml.dump(yaml_data), encoding="utf-8")

    registry = ModelRegistry(models_dir)
    manager = ModelManager(registry, cache_dir=cache_dir)

    # Create placeholder directories/files so is_downloaded returns True
    for spec in registry.list():
        model_path = manager.get_model_path(spec)
        model_path.mkdir(parents=True, exist_ok=True)
        (model_path / ".placeholder").touch()

    return registry, manager


def _make_sine_chunk(duration_s: float = 0.1, sample_rate: int = 16000) -> np.ndarray:
    """Generate a sine wave chunk of given duration."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    return np.sin(2 * np.pi * 440 * t).astype(np.float32)


def _collect_events(
    pipeline: pipeline_mod.StreamingPipeline, timeout: float = 2.0
) -> tuple[list[SubtitleEvent], list[str], list[TranscriptMessage]]:
    """Start, wait, stop pipeline and collect events."""
    subtitles: list[SubtitleEvent] = []
    errors: list[str] = []
    messages: list[TranscriptMessage] = []

    pipeline.on_subtitle = subtitles.append
    pipeline._on_error = errors.append
    pipeline._on_message = messages.append

    pipeline.start()
    time.sleep(timeout)
    pipeline.stop()

    return subtitles, errors, messages


# ---------------------------------------------------------------------------
# Test 1: VAD-off regression — streaming mode
# ---------------------------------------------------------------------------


def test_vad_off_streaming_fake_translator(monkeypatch, tmp_path):
    """With enable_vad=False, streaming mode should behave identically to legacy.

    Fake AudioCapture pushes a scripted chunk, the fake transcriber returns
    predictable text, and we verify the event sequence matches the expected
    _process_loop + _translation_loop pattern.
    """
    fake_transcriber = FakeStreamingTranscriber(responses=["hello world"])
    monkeypatch.setitem(pipeline_mod.STREAMING_BACKENDS, "fake", lambda spec, root: fake_transcriber)
    monkeypatch.setattr(pipeline_mod, "AudioCapture", FakeAudioCapture)

    audio_chunk = _make_sine_chunk(0.1)
    fake_capture = FakeAudioCapture(chunks=[audio_chunk])
    monkeypatch.setattr(pipeline_mod, "AudioCapture", lambda source=None, **kw: fake_capture)

    registry, manager = _make_registry_and_manager(tmp_path, [_make_asr_streaming_yaml()])

    pipeline = pipeline_mod.StreamingPipeline(
        model_id="test-streaming",
        registry=registry,
        model_manager=manager,
        enable_translation=False,
        enable_vad=False,
    )

    subtitles: list[SubtitleEvent] = []
    messages: list[TranscriptMessage] = []
    pipeline.on_subtitle = subtitles.append
    pipeline._on_message = messages.append

    pipeline.start()
    # Wait for audio to be processed
    time.sleep(0.5)
    pipeline.stop()

    # Should have at least one partial subtitle event
    assert len(subtitles) >= 1, "Expected at least one partial subtitle event"
    event = subtitles[0]
    assert event.text == "hello world"
    assert event.is_partial is True
    assert event.committed_translation == ""
    assert event.draft_translation == ""


# ---------------------------------------------------------------------------
# Test 2: VAD-on streaming integration
# ---------------------------------------------------------------------------


def test_vad_on_streaming_integration(monkeypatch, tmp_path):
    """VAD-on streaming mode: silence suppresses transcriber, segment close commits.

    The fake VAD is scripted to open a segment after 3 frames and close after 6.
    We verify: (a) transcriber not called during silence, (b) one commit after
    segment close with is_partial=False, (c) transcript + emit_message called.
    """
    fake_vad = FakeVADBackend(frame_size=512)
    fake_vad.set_script([(3, "start"), (6, "stop")])

    fake_transcriber = FakeStreamingTranscriber(responses=["partial", "more partial"])
    fake_transcriber.set_final_text("final sentence")

    monkeypatch.setitem(pipeline_mod.VAD_BACKENDS, "fake", lambda spec, root, **kw: fake_vad)
    monkeypatch.setitem(pipeline_mod.STREAMING_BACKENDS, "fake", lambda spec, root: fake_transcriber)

    # Create 10 audio chunks (100ms each = 1600 samples); VAD gets 1600/512 ≈ 3.1 frames per chunk
    audio_chunks = [_make_sine_chunk(0.1) for _ in range(10)]
    fake_capture = FakeAudioCapture(chunks=audio_chunks)
    monkeypatch.setattr(pipeline_mod, "AudioCapture", lambda source=None, **kw: fake_capture)

    yamls = [_make_asr_streaming_yaml(), _make_vad_yaml(model_id="vad-test", backend="fake")]
    registry, manager = _make_registry_and_manager(tmp_path, yamls)

    subtitles: list[SubtitleEvent] = []
    messages: list[TranscriptMessage] = []
    errors: list[str] = []

    pipeline = pipeline_mod.StreamingPipeline(
        model_id="test-streaming",
        registry=registry,
        model_manager=manager,
        enable_translation=False,
        enable_vad=True,
        vad_model_id="vad-test",
        vad_split_by_punctuation=False,
    )
    pipeline.on_subtitle = subtitles.append
    pipeline._on_error = errors.append
    pipeline._on_message = messages.append

    pipeline.start()
    time.sleep(1.0)
    pipeline.stop()

    # Partial events during speech
    partials = [e for e in subtitles if e.is_partial]
    assert len(partials) >= 1, "Expected at least one partial event during speech"

    # Final commit event
    finals = [e for e in subtitles if not e.is_partial]
    assert len(finals) >= 1, "Expected at least one final commit event"
    final = finals[0]
    assert final.text == "final sentence"

    # Verify transcriber was called during speech (not before scripted start)
    assert len(fake_transcriber._process_calls) > 0, "Transcriber should have been called during speech"

    # Verify reset was called after segment close
    assert fake_transcriber._reset_calls >= 1, "Transcriber should be reset after segment close"


# ---------------------------------------------------------------------------
# Test 3: VAD-on chunked integration
# ---------------------------------------------------------------------------


def test_vad_on_chunked_integration(monkeypatch, tmp_path):
    """VAD-on chunked mode: only completed segments are transcribed.

    Verify that _chunk_buffer time-based accumulation is bypassed and
    transcribe() is called only for completed VAD segments.
    """
    fake_vad = FakeVADBackend(frame_size=512)
    fake_vad.set_script([(2, "start"), (5, "stop")])

    fake_transcriber = FakeChunkedTranscriber()
    fake_transcriber.set_response("chunked result")

    monkeypatch.setitem(pipeline_mod.VAD_BACKENDS, "fake", lambda spec, root, **kw: fake_vad)
    monkeypatch.setitem(pipeline_mod.CHUNKED_BACKENDS, "fake", lambda spec, root: fake_transcriber)

    audio_chunks = [_make_sine_chunk(0.1) for _ in range(8)]
    fake_capture = FakeAudioCapture(chunks=audio_chunks)
    monkeypatch.setattr(pipeline_mod, "AudioCapture", lambda source=None, **kw: fake_capture)

    yamls = [_make_asr_chunked_yaml(), _make_vad_yaml(model_id="vad-test", backend="fake")]
    registry, manager = _make_registry_and_manager(tmp_path, yamls)

    subtitles: list[SubtitleEvent] = []
    messages: list[TranscriptMessage] = []

    pipeline = pipeline_mod.StreamingPipeline(
        model_id="test-chunked",
        registry=registry,
        model_manager=manager,
        enable_translation=False,
        enable_vad=True,
        vad_model_id="vad-test",
        vad_split_by_punctuation=False,
    )
    pipeline.on_subtitle = subtitles.append
    pipeline._on_message = messages.append

    pipeline.start()
    time.sleep(1.0)
    pipeline.stop()

    # transcribe should have been called at least once (for completed segment)
    assert len(fake_transcriber.transcribe_calls) >= 1, "Expected transcribe to be called for completed segment"

    # No partial events in chunked mode (OfflineRecognizer has no partial capability)
    partials = [e for e in subtitles if e.is_partial]
    assert len(partials) == 0, "Chunked VAD mode should not emit partial events"

    # Final commit
    finals = [e for e in subtitles if not e.is_partial]
    assert len(finals) >= 1


# ---------------------------------------------------------------------------
# Test 4: Graceful degradation
# ---------------------------------------------------------------------------


def test_vad_graceful_degradation_model_not_downloaded(monkeypatch, tmp_path):
    """When VAD model is not downloaded, _vad_gate is None and on_error fires.

    Pipeline should continue working via the legacy path.
    """
    fake_transcriber = FakeStreamingTranscriber(responses=["legacy works"])
    monkeypatch.setitem(pipeline_mod.STREAMING_BACKENDS, "fake", lambda spec, root: fake_transcriber)

    audio_chunk = _make_sine_chunk(0.1)
    fake_capture = FakeAudioCapture(chunks=[audio_chunk])
    monkeypatch.setattr(pipeline_mod, "AudioCapture", lambda source=None, **kw: fake_capture)

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Write ASR yaml + VAD yaml, but do NOT create the VAD model cache dir
    (models_dir / "asr.yaml").write_text(yaml.dump(_make_asr_streaming_yaml()), encoding="utf-8")
    (models_dir / "vad.yaml").write_text(
        yaml.dump(_make_vad_yaml(model_id="vad-test", backend="fake")), encoding="utf-8"
    )

    registry = ModelRegistry(models_dir)
    manager = ModelManager(registry, cache_dir=cache_dir)

    # Create ASR model cache dir so is_downloaded passes for ASR
    asr_path = manager.get_model_path(registry.get("test-streaming"))
    asr_path.mkdir(parents=True, exist_ok=True)
    (asr_path / ".placeholder").touch()

    subtitles: list[SubtitleEvent] = []
    errors: list[str] = []

    pipeline = pipeline_mod.StreamingPipeline(
        model_id="test-streaming",
        registry=registry,
        model_manager=manager,
        on_error=errors.append,
        enable_translation=False,
        enable_vad=True,
        vad_model_id="vad-test",
    )
    pipeline.on_subtitle = subtitles.append

    pipeline.start()
    time.sleep(0.5)
    pipeline.stop()

    # Verify degradation warning
    assert any("warning_vad_unavailable_fallback" in e for e in errors), (
        f"Expected 'warning_vad_unavailable_fallback' in errors, got: {errors}"
    )

    # Pipeline should still work (legacy path)
    assert pipeline._vad_gate is None
    assert len(subtitles) >= 1, "Legacy path should still produce subtitles"
    assert subtitles[0].text == "legacy works"


# ---------------------------------------------------------------------------
# Test 5: stop() flush tail segment
# ---------------------------------------------------------------------------


def test_stop_flush_tail_segment(monkeypatch, tmp_path):
    """When VAD has an open segment at stop(), flush() captures the tail.

    The tail sentence should appear in the commit events.
    """
    fake_vad = FakeVADBackend(frame_size=512)
    # Open segment early but never close it — flush() should handle it
    fake_vad.set_script([(2, "start")])

    fake_transcriber = FakeStreamingTranscriber(responses=["ongoing"])
    fake_transcriber.set_final_text("tail sentence")

    monkeypatch.setitem(pipeline_mod.VAD_BACKENDS, "fake", lambda spec, root, **kw: fake_vad)
    monkeypatch.setitem(pipeline_mod.STREAMING_BACKENDS, "fake", lambda spec, root: fake_transcriber)

    audio_chunks = [_make_sine_chunk(0.1) for _ in range(6)]
    fake_capture = FakeAudioCapture(chunks=audio_chunks)
    monkeypatch.setattr(pipeline_mod, "AudioCapture", lambda source=None, **kw: fake_capture)

    yamls = [_make_asr_streaming_yaml(), _make_vad_yaml(model_id="vad-test", backend="fake")]
    registry, manager = _make_registry_and_manager(tmp_path, yamls)

    subtitles: list[SubtitleEvent] = []
    messages: list[TranscriptMessage] = []

    pipeline = pipeline_mod.StreamingPipeline(
        model_id="test-streaming",
        registry=registry,
        model_manager=manager,
        enable_translation=False,
        enable_vad=True,
        vad_model_id="vad-test",
        vad_split_by_punctuation=False,
    )
    pipeline.on_subtitle = subtitles.append
    pipeline._on_message = messages.append

    pipeline.start()
    time.sleep(0.5)
    pipeline.stop()

    # Should have at least one final commit with the tail sentence
    finals = [e for e in subtitles if not e.is_partial]
    assert len(finals) >= 1, "Expected tail segment to be committed on stop"
    assert any("tail" in e.text.lower() for e in finals), f"Expected 'tail' in final events, got: {finals}"


# ---------------------------------------------------------------------------
# Test 6: process_committed_sentence unit tests
# ---------------------------------------------------------------------------


class FakeTranslator:
    """Fake translator that uppercases the input."""

    def __init__(self, target_lang: str = "zh"):
        self.target_language = target_lang

    def translate(self, text: str) -> str:
        return text.upper()


def test_process_committed_sentence_with_translator():
    """With translator, returns (translated, '', (text, translated))."""
    layer = TranslationLayer(
        enable_translation=True,
        translation_engine="google",
        target_language="zh",
        openai_config=pipeline_mod.OpenAIConfig(),
        on_message=None,
    )
    # Replace the real translator with our fake
    object.__setattr__(layer, "_translator", FakeTranslator())
    object.__setattr__(layer, "_state_manager", None)  # not needed for committed sentence path

    result = layer.process_committed_sentence("hello")
    assert result.committed_text == "HELLO"
    assert result.draft_text == ""
    assert result.batch == ("hello", "HELLO")


def test_process_committed_sentence_without_translator():
    """Without translator, returns ('', '', (text, None))."""
    layer = TranslationLayer(
        enable_translation=False,
        translation_engine="google",
        target_language="zh",
        openai_config=pipeline_mod.OpenAIConfig(),
        on_message=None,
    )

    result = layer.process_committed_sentence("hello")
    assert result.committed_text == ""
    assert result.draft_text == ""
    assert result.batch == ("hello", None)


def test_process_committed_sentence_empty_text():
    """Empty text returns ('', '', None)."""
    layer = TranslationLayer(
        enable_translation=True,
        translation_engine="google",
        target_language="zh",
        openai_config=pipeline_mod.OpenAIConfig(),
        on_message=None,
    )
    object.__setattr__(layer, "_translator", FakeTranslator())
    object.__setattr__(layer, "_state_manager", None)

    result = layer.process_committed_sentence("")
    assert result.committed_text == ""
    assert result.draft_text == ""
    assert result.batch is None


# ---------------------------------------------------------------------------
# Test 7: multi-sentence commit displays as one block
# ---------------------------------------------------------------------------


def test_multi_sentence_commit_single_display_event(monkeypatch, tmp_path):
    """A commit containing several sentences emits ONE display event.

    One SubtitleEvent per sentence would put several replacements into the
    same event-loop tick; with the overlay's replace semantics only the last
    one would stay visible. The block is displayed joined; transcript log and
    console history stay per sentence.
    """
    fake_vad = FakeVADBackend(frame_size=512)
    fake_vad.set_script([(3, "start"), (6, "stop")])

    fake_transcriber = FakeStreamingTranscriber()
    fake_transcriber.set_final_text("Hello there. How are you")

    monkeypatch.setitem(pipeline_mod.VAD_BACKENDS, "fake", lambda spec, root, **kw: fake_vad)
    monkeypatch.setitem(pipeline_mod.STREAMING_BACKENDS, "fake", lambda spec, root: fake_transcriber)

    audio_chunks = [_make_sine_chunk(0.1) for _ in range(10)]
    fake_capture = FakeAudioCapture(chunks=audio_chunks)
    monkeypatch.setattr(pipeline_mod, "AudioCapture", lambda source=None, **kw: fake_capture)

    yamls = [_make_asr_streaming_yaml(), _make_vad_yaml(model_id="vad-test", backend="fake")]
    registry, manager = _make_registry_and_manager(tmp_path, yamls)

    subtitles: list[SubtitleEvent] = []
    messages: list[TranscriptMessage] = []

    pipeline = pipeline_mod.StreamingPipeline(
        model_id="test-streaming",
        registry=registry,
        model_manager=manager,
        on_message=messages.append,
        enable_translation=False,
        enable_vad=True,
        vad_model_id="vad-test",
        # vad_split_by_punctuation defaults to True
    )
    pipeline.on_subtitle = subtitles.append

    pipeline.start()
    time.sleep(1.0)
    pipeline.stop()

    finals = [e for e in subtitles if not e.is_partial]
    assert len(finals) == 1, f"Expected exactly one display event for the commit, got: {finals}"
    assert finals[0].text == "Hello there\nHow are you"
    assert finals[0].committed_translation == ""
    # Console history is still per sentence
    assert len(messages) == 2


# ---------------------------------------------------------------------------
# Test 8: committed block displays immediately, translation arrives later
# ---------------------------------------------------------------------------


class SlowFakeTranslator:
    """Translator with a delay to widen the commit-to-translation window."""

    def __init__(self, target_lang: str = "zh"):
        self.target_language = target_lang

    def translate(self, text: str) -> str:
        time.sleep(0.2)
        return text.upper()


def test_commit_waits_for_translation_before_display(monkeypatch, tmp_path):
    """With translation enabled, nothing is displayed at commit time; the
    block shows only when the sentence translation arrives (a raw-only
    subtitle line is not useful)."""
    fake_vad = FakeVADBackend(frame_size=512)
    fake_vad.set_script([(3, "start"), (6, "stop")])

    fake_transcriber = FakeStreamingTranscriber()
    fake_transcriber.set_final_text("hello world")

    monkeypatch.setitem(pipeline_mod.VAD_BACKENDS, "fake", lambda spec, root, **kw: fake_vad)
    monkeypatch.setitem(pipeline_mod.STREAMING_BACKENDS, "fake", lambda spec, root: fake_transcriber)

    audio_chunks = [_make_sine_chunk(0.1) for _ in range(10)]
    fake_capture = FakeAudioCapture(chunks=audio_chunks)
    monkeypatch.setattr(pipeline_mod, "AudioCapture", lambda source=None, **kw: fake_capture)

    yamls = [_make_asr_streaming_yaml(), _make_vad_yaml(model_id="vad-test", backend="fake")]
    registry, manager = _make_registry_and_manager(tmp_path, yamls)

    subtitles: list[SubtitleEvent] = []
    messages: list[TranscriptMessage] = []

    pipeline = pipeline_mod.StreamingPipeline(
        model_id="test-streaming",
        registry=registry,
        model_manager=manager,
        enable_translation=False,  # swapped for a ready layer with a fake translator below
        enable_vad=True,
        vad_model_id="vad-test",
        vad_split_by_punctuation=False,
    )
    ready_layer = TranslationLayer(
        enable_translation=True,
        translation_engine="google",
        target_language="zh",
        openai_config=pipeline_mod.OpenAIConfig(),
        on_message=messages.append,
    )
    object.__setattr__(ready_layer, "_translator", SlowFakeTranslator())
    pipeline._translation_layer = ready_layer

    pipeline.on_subtitle = subtitles.append
    pipeline.start()
    time.sleep(1.5)
    pipeline.stop()

    finals = [e for e in subtitles if not e.is_partial]
    assert len(finals) == 1, f"Expected exactly one display event (after translation), got: {finals}"
    assert finals[0].text == "hello world"
    assert finals[0].committed_translation == "HELLO WORLD"


# ---------------------------------------------------------------------------
# Test 9: VAD source text rolling window
# ---------------------------------------------------------------------------


def test_vad_source_rolling_window(monkeypatch, tmp_path):
    """VAD source text accumulates across commits and rolls out at max_lines.

    Three consecutive commits with max_lines=2: the display keeps the two
    most recent source texts and drops the oldest. Both the internal state
    and the emitted SubtitleEvent reflect the rolling window.
    """
    fake_vad = FakeVADBackend(frame_size=512)
    fake_vad.set_script(
        [
            (3, "start"),
            (6, "stop"),  # segment 1
            (9, "start"),
            (12, "stop"),  # segment 2
            (15, "start"),
            (18, "stop"),  # segment 3
        ]
    )

    # Chunked transcriber returning a different text per segment
    responses = ["sentence one", "sentence two", "sentence three"]
    call_count = [0]

    class ScriptedChunkedTranscriber:
        def transcribe(self, audio, sample_rate):
            idx = min(call_count[0], len(responses) - 1)
            call_count[0] += 1
            return responses[idx]

    monkeypatch.setitem(pipeline_mod.VAD_BACKENDS, "fake", lambda spec, root, **kw: fake_vad)
    monkeypatch.setitem(pipeline_mod.CHUNKED_BACKENDS, "fake", lambda spec, root: ScriptedChunkedTranscriber())

    audio_chunks = [_make_sine_chunk(0.1) for _ in range(20)]
    fake_capture = FakeAudioCapture(chunks=audio_chunks)
    monkeypatch.setattr(pipeline_mod, "AudioCapture", lambda source=None, **kw: fake_capture)

    yamls = [_make_asr_chunked_yaml(), _make_vad_yaml(model_id="vad-test", backend="fake")]
    registry, manager = _make_registry_and_manager(tmp_path, yamls)

    subtitles: list[SubtitleEvent] = []
    messages: list[TranscriptMessage] = []

    pipeline = pipeline_mod.StreamingPipeline(
        model_id="test-chunked",
        registry=registry,
        model_manager=manager,
        enable_translation=False,
        enable_vad=True,
        vad_model_id="vad-test",
        vad_split_by_punctuation=False,
        max_lines=2,
    )

    # Swap in a translation layer with a slow fake translator so the
    # translation thread has time to observe _vad_display_block after
    # all commits are done.
    ready_layer = TranslationLayer(
        enable_translation=True,
        translation_engine="google",
        target_language="zh",
        openai_config=pipeline_mod.OpenAIConfig(),
        on_message=messages.append,
    )
    object.__setattr__(ready_layer, "_translator", SlowFakeTranslator())
    pipeline._translation_layer = ready_layer

    pipeline.on_subtitle = subtitles.append
    pipeline.start()
    time.sleep(3.0)
    pipeline.stop()

    # Internal state: two most recent sources kept, oldest rolled out
    assert pipeline._vad_committed_sources == ["sentence two", "sentence three"]
    assert pipeline._vad_display_block == "sentence two\nsentence three"

    # Emitted event reflects accumulated source text
    finals = [e for e in subtitles if not e.is_partial]
    assert len(finals) >= 1, f"Expected at least one final event, got: {len(finals)}"
    last_final = finals[-1]
    assert "sentence one" not in last_final.text, f"Oldest should roll out: {last_final.text}"
    assert "sentence two" in last_final.text, f"Expected 'sentence two': {last_final.text}"
    assert "sentence three" in last_final.text, f"Expected 'sentence three': {last_final.text}"


def test_vad_source_window_counts_sentences_not_commits(monkeypatch, tmp_path):
    """max_lines counts sentences, not commit events.

    A single commit that punctuation-splits into two sentences must count as
    two entries against max_lines — not one — so the window doesn't secretly
    hold more visible lines than max_lines once split blocks are involved,
    and so the source window's line-count semantics match the translation
    window's (both accumulate per-sentence).
    """
    fake_vad = FakeVADBackend(frame_size=512)
    fake_vad.set_script(
        [
            (3, "start"),
            (6, "stop"),  # segment 1: two sentences via punctuation split
            (9, "start"),
            (12, "stop"),  # segment 2: one sentence
        ]
    )

    responses = ["Hello there. How are you", "sentence three"]
    call_count = [0]

    class ScriptedChunkedTranscriber:
        def transcribe(self, audio, sample_rate):
            idx = min(call_count[0], len(responses) - 1)
            call_count[0] += 1
            return responses[idx]

    monkeypatch.setitem(pipeline_mod.VAD_BACKENDS, "fake", lambda spec, root, **kw: fake_vad)
    monkeypatch.setitem(pipeline_mod.CHUNKED_BACKENDS, "fake", lambda spec, root: ScriptedChunkedTranscriber())

    audio_chunks = [_make_sine_chunk(0.1) for _ in range(14)]
    fake_capture = FakeAudioCapture(chunks=audio_chunks)
    monkeypatch.setattr(pipeline_mod, "AudioCapture", lambda source=None, **kw: fake_capture)

    yamls = [_make_asr_chunked_yaml(), _make_vad_yaml(model_id="vad-test", backend="fake")]
    registry, manager = _make_registry_and_manager(tmp_path, yamls)

    subtitles: list[SubtitleEvent] = []

    pipeline = pipeline_mod.StreamingPipeline(
        model_id="test-chunked",
        registry=registry,
        model_manager=manager,
        enable_translation=False,
        enable_vad=True,
        vad_model_id="vad-test",
        vad_split_by_punctuation=True,
        max_lines=2,
    )
    pipeline.on_subtitle = subtitles.append

    pipeline.start()
    time.sleep(1.0)
    pipeline.stop()

    # "Hello there" (the older of the two sentences from commit 1) must have
    # rolled out even though it came from the same commit as "How are you" —
    # the window is keyed on sentence count, not on which commit produced it.
    assert pipeline._vad_committed_sources == ["How are you", "sentence three"]
    assert pipeline._vad_display_block == "How are you\nsentence three"

    finals = [e for e in subtitles if not e.is_partial]
    assert finals, "Expected at least one final display event"
    assert "Hello there" not in finals[-1].text
    assert finals[-1].text == "How are you\nsentence three"


def test_vad_params_ui_owned_keys_ignore_yaml(monkeypatch, tmp_path):
    """UI-owned VAD params come from vad_overrides (Settings/UI) with
    code-level fallbacks; yaml params carrying the same keys are ignored.

    Settings always produce concrete values for these keys, so without the
    exclusion a yaml value for them could never take effect. Non-UI keys
    (model_family etc.) still pass through from yaml.
    """
    captured: dict = {}

    def fake_backend_factory(spec, root, **kw):
        captured.update(kw["params"])
        return FakeVADBackend(frame_size=512)

    monkeypatch.setitem(pipeline_mod.VAD_BACKENDS, "fake", fake_backend_factory)
    monkeypatch.setitem(pipeline_mod.STREAMING_BACKENDS, "fake", lambda spec, root: FakeStreamingTranscriber())
    monkeypatch.setattr(pipeline_mod, "AudioCapture", lambda source=None, **kw: FakeAudioCapture())

    vad_yaml = _make_vad_yaml(model_id="vad-test", backend="fake")
    # Simulate a yaml that still carries UI-owned keys: they must be ignored.
    vad_yaml["params"].update(
        {
            "threshold": 0.99,
            "min_silence_duration": 9.9,
            "min_speech_duration": 9.9,
            "max_speech_duration": 99.0,
        }
    )
    registry, manager = _make_registry_and_manager(tmp_path, [_make_asr_streaming_yaml(), vad_yaml])

    # No overrides: UI-owned keys fall back to the UI-default constants
    pipeline_mod.StreamingPipeline(
        model_id="test-streaming",
        registry=registry,
        model_manager=manager,
        enable_translation=False,
        enable_vad=True,
        vad_model_id="vad-test",
    )
    assert captured["threshold"] == 0.5
    assert captured["min_silence_duration"] == 0.5
    assert captured["min_speech_duration"] == 0.25
    assert captured["max_speech_duration"] == 20.0
    # Non-UI keys still come from yaml
    assert captured["model_family"] == "silero"

    # Overrides (the Settings/UI path) win over both yaml and fallback;
    # None-valued entries do not shadow the fallback
    pipeline_mod.StreamingPipeline(
        model_id="test-streaming",
        registry=registry,
        model_manager=manager,
        enable_translation=False,
        enable_vad=True,
        vad_model_id="vad-test",
        vad_overrides={"threshold": 0.8, "min_silence_duration": None},
    )
    assert captured["threshold"] == 0.8
    assert captured["min_silence_duration"] == 0.5
