"""Voice-activity-detection subsystem."""

from .base import VADBackend, VadFeedResult, VadSegment
from .gate import VadGate
from .sherpa_vad import SherpaOnnxVadBackend

__all__ = [
    "VADBackend",
    "VadFeedResult",
    "VadGate",
    "VadSegment",
    "SherpaOnnxVadBackend",
]
