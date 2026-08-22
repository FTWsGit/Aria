
import pytest
import yaml

from aria.model_manager.registry import ModelRegistry, ModelSpec


def test_registry_lists_models(tmp_path):
    """Registry should list models from yaml files."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    yaml_content = {
        "id": "test-model",
        "kind": "asr_streaming",
        "backend": "sherpa_onnx",
        "display_name": "Test Model",
        "language": "zh",
        "source": {"type": "manual", "path": "/tmp"},
        "size_mb": 100,
    }
    (models_dir / "test.yaml").write_text(yaml.dump(yaml_content), encoding="utf-8")

    registry = ModelRegistry(models_dir)
    models = registry.list()
    assert len(models) == 1
    assert models[0].id == "test-model"


def test_registry_get_raises_keyerror(tmp_path):
    """Registry.get() should raise KeyError for non-existent model."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    registry = ModelRegistry(models_dir)
    with pytest.raises(KeyError):
        registry.get("nonexistent")


def test_registry_len(tmp_path):
    """Registry __len__ should match number of yaml files."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    for i in range(3):
        yaml_content = {
            "id": f"model-{i}",
            "kind": "asr_streaming",
            "backend": "sherpa_onnx",
            "display_name": f"Model {i}",
            "language": "zh",
            "source": {},
        }
        (models_dir / f"model_{i}.yaml").write_text(yaml.dump(yaml_content), encoding="utf-8")
    registry = ModelRegistry(models_dir)
    assert len(registry) == 3


def test_registry_list_filter_by_kind(tmp_path):
    """Registry.list(kind=...) should filter by kind."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    for i in range(2):
        yaml_content = {
            "id": f"streaming-{i}",
            "kind": "asr_streaming",
            "backend": "sherpa_onnx",
            "display_name": f"S{i}",
            "language": "zh",
            "source": {},
        }
        (models_dir / f"s{i}.yaml").write_text(yaml.dump(yaml_content), encoding="utf-8")
    yaml_content = {
        "id": "chunked-1",
        "kind": "asr_chunked",
        "backend": "whisper_http",
        "display_name": "C1",
        "language": "en",
        "source": {},
    }
    (models_dir / "c1.yaml").write_text(yaml.dump(yaml_content), encoding="utf-8")

    registry = ModelRegistry(models_dir)
    streaming = registry.list(kind="asr_streaming")
    chunked = registry.list(kind="asr_chunked")
    assert len(streaming) == 2
    assert len(chunked) == 1


def test_spec_get_size_display():
    """ModelSpec.get_size_display() should format sizes correctly."""
    spec = ModelSpec(
        id="test",
        kind="asr_streaming",
        backend="sherpa_onnx",
        display_name="T",
        language="zh",
        source={},
        size_mb=500,
    )
    assert spec.get_size_display() == "500MB"
    spec.size_mb = 2048
    assert spec.get_size_display() == "2.0GB"
