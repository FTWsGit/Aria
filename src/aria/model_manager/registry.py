"""
Model Registry - Scans models/ directory for YAML model configurations.

Reads model specs from yaml files, never triggers downloads.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ModelSpec:
    """A single model's configuration parsed from YAML."""

    id: str
    kind: str
    backend: str
    display_name: str
    language: str
    source: dict
    size_mb: int = 0
    params: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    def get_size_display(self) -> str:
        """Get human-readable size string."""
        if self.size_mb >= 1024:
            return f"{self.size_mb / 1024:.1f}GB"
        return f"{self.size_mb}MB"


class ModelRegistry:
    """Scans models/ for *.yaml files and builds a model spec index."""

    def __init__(self, models_dir: Path):
        self._specs: dict[str, ModelSpec] = {}
        if not models_dir.is_dir():
            return

        for f in sorted(models_dir.rglob("*.yaml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            spec = ModelSpec(
                id=data["id"],
                kind=data["kind"],
                backend=data["backend"],
                display_name=data.get("display_name", data["id"]),
                language=data.get("language", "unknown"),
                source=data.get("source", {}),
                size_mb=data.get("size_mb", 0),
                params=data.get("params", {}),
                raw=data,
            )
            self._specs[spec.id] = spec

    def list(self, kind: str | None = None) -> list[ModelSpec]:
        return [s for s in self._specs.values() if kind is None or s.kind == kind]

    def get(self, model_id: str) -> ModelSpec:
        if model_id not in self._specs:
            raise KeyError(f"Model '{model_id}' not found in registry")
        return self._specs[model_id]

    def __len__(self) -> int:
        return len(self._specs)
