"""
Abstract base class for pipeline lifecycle.

LiveCaptionsPipeline and StreamingPipeline share on_subtitle callback
assignment, _running state, and abstract start/stop interface.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from ..events import SubtitleEvent
from ..logger import debug


class BasePipeline(ABC):
    """Shared pipeline lifecycle for ASR / LiveCaptions pipelines."""

    def __init__(
        self,
        on_subtitle: Callable[[SubtitleEvent], None] | None = None,
    ):
        self.on_subtitle = on_subtitle or self._default_callback
        self._running = False

    @abstractmethod
    def start(self) -> None:
        """Start the pipeline."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the pipeline."""

    def _default_callback(self, event: SubtitleEvent) -> None:
        """Default subtitle callback when no on_subtitle is provided."""
        debug(f"[{event.language}] {event.text}")

    @property
    def is_running(self) -> bool:
        return self._running
