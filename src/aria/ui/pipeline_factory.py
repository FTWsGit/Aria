"""
Pipeline factory - creates StreamingPipeline or LiveCaptionsPipeline instances.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ..livecaptions import LiveCaptionsPipeline
from ..pipeline import StreamingPipeline
from ..translation.translation_layer import OpenAIConfig

if TYPE_CHECKING:
    from ..model_manager.manager import ModelManager
    from ..model_manager.registry import ModelRegistry
    from .app import PipelineSignals


class PipelineFactory:
    """Factory for creating pipeline instances based on mode."""

    @staticmethod
    def _resolve_model_id(
        settings: dict,
        registry: ModelRegistry,
        on_error: Callable[[str], None],
    ) -> str | None:
        """Resolve model_id from settings, falling back to first available model.

        Returns None when registry is empty (error is emitted via on_error).
        """
        model_id = settings.get("model_id")
        if model_id:
            try:
                registry.get(model_id)
                return model_id
            except KeyError:
                pass
        all_models = registry.list()
        if all_models:
            return all_models[0].id
        on_error("error_no_models_available")
        return None

    @staticmethod
    def create_streaming_pipeline(
        settings: dict,
        registry: ModelRegistry,
        model_manager: ModelManager,
        signals: PipelineSignals,
        on_error: Callable[[str], None],
    ) -> StreamingPipeline | None:
        """Create a StreamingPipeline for Sherpa-ONNX ASR.

        Returns None when no model is available (error already emitted via on_error).
        """
        openai_cfg = OpenAIConfig(
            endpoint=settings.get("openai_endpoint", "http://127.0.0.1:1234/v1"),
            api_key=settings.get("openai_api_key", ""),
            model_name=settings.get("openai_model_name", ""),
            temperature=settings.get("openai_temperature", 0.2),
            max_tokens=settings.get("openai_max_tokens", 1024),
            system_prompt=settings.get("openai_system_prompt", ""),
        )
        model_id = PipelineFactory._resolve_model_id(settings, registry, on_error)
        if model_id is None:
            return None
        return StreamingPipeline(
            model_id=model_id,
            registry=registry,
            model_manager=model_manager,
            on_subtitle=lambda e: signals.subtitle.emit(e),
            on_error=on_error,
            on_message=lambda m: signals.message.emit(m),
            enable_translation=settings.get("enable_translation", False),
            translation_engine=settings.get("translation_engine", "google"),
            target_language=settings.get("target_language", "zho_Hant"),
            audio_source=settings.get("audio_source", "system"),
            openai_config=openai_cfg,
        )

    @staticmethod
    def create_livecaptions_pipeline(
        settings: dict,
        signals: PipelineSignals,
    ) -> LiveCaptionsPipeline:
        """Create a LiveCaptionsPipeline for Windows 11 LiveCaptions."""
        openai_cfg = OpenAIConfig(
            endpoint=settings.get("openai_endpoint", "http://127.0.0.1:1234/v1"),
            api_key=settings.get("openai_api_key", ""),
            model_name=settings.get("openai_model_name", ""),
            temperature=settings.get("openai_temperature", 0.2),
            max_tokens=settings.get("openai_max_tokens", 1024),
            system_prompt=settings.get("openai_system_prompt", ""),
        )
        return LiveCaptionsPipeline(
            on_subtitle=lambda e: signals.subtitle.emit(e),
            on_message=lambda m: signals.message.emit(m),
            enable_translation=settings.get("enable_translation", False),
            translation_engine=settings.get("translation_engine", "google"),
            target_language=settings.get("target_language", "zho_Hant"),
            auto_hide_window=False,
            openai_config=openai_cfg,
        )
