"""
Model Manager - Handles model downloading and status checking.
"""

import os
import threading
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from ..i18n import t
from .registry import ModelRegistry, ModelSpec


class ModelStatus(Enum):
    """Download status of a model."""

    NOT_DOWNLOADED = "not_downloaded"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    ERROR = "error"


class ModelManager:
    """Manages model downloading and status."""

    def __init__(self, registry: ModelRegistry, models_dir: Path | None = None, cache_dir: Path | None = None):
        """
        Initialize the model manager.

        Args:
            registry: ModelRegistry instance for model specs
            models_dir: Directory containing yaml configs (default: project_root/models/)
            cache_dir: Directory for downloaded model weights (default: project_root/models_cache/)
        """
        self.registry = registry
        self.models_dir = models_dir or self._get_default_models_dir()
        self.cache_dir = cache_dir or self._get_default_cache_dir()
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Download state
        self._download_progress: dict[str, float] = {}
        self._download_threads: dict[str, threading.Thread] = {}
        self._download_callbacks: dict[str, Callable[[str, float, str], None]] = {}

    @staticmethod
    def _get_default_models_dir() -> Path:
        """Get the default models directory (project directory)."""
        # Use project directory for portability
        # Find the project root by looking for src directory
        current = Path(__file__).resolve()
        # Go up from model_manager/manager.py -> model_manager -> aria -> src -> project_root
        project_root = current.parent.parent.parent.parent
        return project_root / "models"

    @staticmethod
    def _get_default_cache_dir() -> Path:
        """Get the default cache directory for downloaded model weights."""
        current = Path(__file__).resolve()
        project_root = current.parent.parent.parent.parent
        return project_root / "models_cache"

    def get_model_path(self, model: ModelSpec) -> Path:
        """Get the local path for a model."""
        if model.source.get("type") == "manual":
            return Path(model.source["path"])
        return self.cache_dir / model.id

    def is_downloaded(self, model: ModelSpec) -> bool:
        """Check if model files are fully downloaded."""
        model_path = self.get_model_path(model)
        if not model_path.exists():
            return False

        files = model.source.get("files")
        if files:
            return all((model_path / f).exists() for f in files)
        return any(model_path.iterdir())

    def get_status(self, model: ModelSpec) -> ModelStatus:
        """Check if a model is downloaded."""
        model_id = model.id

        # Check if downloading
        if model_id in self._download_threads:
            thread = self._download_threads[model_id]
            if thread.is_alive():
                return ModelStatus.DOWNLOADING

        # Check if downloaded
        if self.is_downloaded(model):
            return ModelStatus.DOWNLOADED

        return ModelStatus.NOT_DOWNLOADED

    def get_progress(self, model: ModelSpec) -> float:
        """Get download progress (0.0 to 1.0)."""
        return self._download_progress.get(model.id, 0.0)

    def download(
        self,
        model: ModelSpec,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> None:
        """
        Start downloading a model in background.

        Args:
            model: Model to download
            progress_callback: Callback(model_id, progress, status_text)
        """
        if self.get_status(model) == ModelStatus.DOWNLOADING:
            return

        if progress_callback:
            self._download_callbacks[model.id] = progress_callback

        thread = threading.Thread(
            target=self._download_model,
            args=(model,),
            daemon=True,
        )
        self._download_threads[model.id] = thread
        self._download_progress[model.id] = 0.0
        thread.start()

    def _download_model(self, model: ModelSpec) -> None:
        """Download a model (runs in background thread)."""
        try:
            callback = self._download_callbacks.get(model.id)

            source_type = model.source.get("type", "")
            if source_type == "huggingface":
                self._download_hf_spec(model, callback)
            elif source_type == "modelscope":
                self._download_modelscope(model, callback)
            elif source_type in ("url_zip", "url_tar"):
                self._download_url_spec(model, callback)
            elif source_type == "manual":
                # Manual type: no download needed, just verify path exists
                if not Path(model.source["path"]).exists():
                    raise FileNotFoundError(f"Manual model path not found: {model.source['path']}")
                self._download_progress[model.id] = 1.0
                if callback:
                    callback(model.id, 1.0, t("download_status_complete"))
                return
            else:
                raise ValueError(f"Unknown source type: {source_type}")

            self._download_progress[model.id] = 1.0
            if callback:
                callback(model.id, 1.0, t("download_status_complete"))
        except Exception as e:
            from ..logger import error as log_error

            log_error(f"Download error: {e}")
            if callback:
                callback(model.id, -1, t("download_status_error").format(error=str(e)))
        finally:
            if model.id in self._download_threads:
                del self._download_threads[model.id]

    def _download_hf_spec(
        self,
        model: ModelSpec,
        callback: Callable[[str, float, str], None] | None,
    ) -> None:
        """Download model from HuggingFace Hub using ModelSpec."""
        try:
            from huggingface_hub import snapshot_download
        except ImportError as err:
            raise RuntimeError(t("download_status_install_hf")) from err

        repo = model.source["repo"]
        local_dir = self.cache_dir / model.id
        files = model.source.get("files")

        if callback:
            callback(model.id, 0.05, t("download_status_downloading").format(name=model.display_name))

        if callback:
            callback(model.id, 0.06, t("download_status_waiting"))

        kwargs = {"local_dir": str(local_dir), "local_dir_use_symlinks": False}
        if files:
            kwargs["allow_patterns"] = files

        snapshot_download(repo_id=repo, **kwargs)

        if callback:
            callback(model.id, 0.98, t("download_status_verifying"))

    def _download_modelscope(
        self,
        model: ModelSpec,
        callback: Callable[[str, float, str], None] | None,
    ) -> None:
        """Download model from ModelScope using ModelSpec."""
        try:
            from modelscope import snapshot_download
        except ImportError as err:
            raise RuntimeError("modelscope is not installed. Run: pip install modelscope") from err

        repo = model.source["repo"]
        local_dir = self.cache_dir / model.id
        files = model.source.get("files")

        if callback:
            callback(model.id, 0.05, t("download_status_downloading").format(name=model.display_name))

        if callback:
            callback(model.id, 0.06, t("download_status_waiting"))

        kwargs = {"local_dir": str(local_dir)}
        if files:
            kwargs["allow_file_pattern"] = files

        snapshot_download(repo, **kwargs)

        if callback:
            callback(model.id, 0.98, t("download_status_verifying"))

    def _download_url_spec(
        self,
        model: ModelSpec,
        callback: Callable[[str, float, str], None] | None,
    ) -> None:
        """Download model from direct URL using ModelSpec."""
        import tarfile
        import tempfile
        import urllib.request
        import zipfile

        url = model.source["url"]
        extract = model.source.get("extract", True)
        local_dir = self.cache_dir / model.id

        if callback:
            callback(model.id, 0.05, t("download_status_downloading").format(name=model.display_name))

        suffix = ""
        if ".tar.bz2" in url:
            suffix = ".tar.bz2"
        elif ".tar.gz" in url:
            suffix = ".tar.gz"
        elif ".zip" in url:
            suffix = ".zip"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            urllib.request.urlretrieve(url, tmp_path)

        if callback:
            callback(model.id, 0.85, t("download_status_extracting"))

        if extract:
            local_dir.mkdir(parents=True, exist_ok=True)
            if url.endswith(".zip"):
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    zf.extractall(str(local_dir))
            elif url.endswith((".tar.bz2", ".tar.gz")):
                with tarfile.open(tmp_path, "r:*") as tf:
                    tf.extractall(str(local_dir))
        else:
            local_dir.mkdir(parents=True, exist_ok=True)
            import shutil

            shutil.move(tmp_path, local_dir / os.path.basename(url))

        os.unlink(tmp_path)

    def delete(self, model: ModelSpec) -> bool:
        """Delete a downloaded model."""
        import shutil

        model_path = self.get_model_path(model)
        if model_path.exists():
            try:
                shutil.rmtree(model_path)
                return True
            except Exception as e:
                from ..logger import error as log_error

                log_error(f"Delete error: {e}")
        return False
