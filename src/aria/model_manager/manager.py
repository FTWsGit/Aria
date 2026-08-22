"""
Model Manager - Handles model downloading and status checking.
"""

import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..i18n import t
from .registry import ModelRegistry, ModelSpec


class ModelType(Enum):
    """Types of models supported."""

    SHERPA = "sherpa"


class ModelStatus(Enum):
    """Download status of a model."""

    NOT_DOWNLOADED = "not_downloaded"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    ERROR = "error"


@dataclass
class ModelInfo:
    """Information about a model."""

    id: str
    name: str
    model_type: ModelType
    size_mb: int
    description: str
    # Download source
    hf_repo: str | None = None  # Hugging Face repo ID
    download_url: str | None = None  # Direct download URL
    # Local paths
    local_folder: str | None = None  # Folder name in models directory

    def get_size_display(self) -> str:
        """Get human-readable size string."""
        if self.size_mb >= 1024:
            return f"{self.size_mb / 1024:.1f}GB"
        return f"{self.size_mb}MB"


# Model list is now driven by ModelRegistry (scans models/ *.yaml files).
# This list is kept for backward compatibility with ModelInfo-based UI code.
# Use ModelRegistry.list() for new code.
SUPPORTED_MODELS: list[ModelInfo] = []


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

    def get_model_path(self, model: ModelInfo | ModelSpec) -> Path:
        """Get the local path for a model (supports both ModelInfo and ModelSpec)."""
        if isinstance(model, ModelSpec):
            if model.source.get("type") == "manual":
                return Path(model.source["path"])
            return self.cache_dir / model.id
        # Legacy ModelInfo path
        if model.local_folder:
            return self.models_dir / model.local_folder
        return self.models_dir / model.id

    def is_downloaded(self, model: ModelInfo | ModelSpec) -> bool:
        """Check if model files are fully downloaded."""
        model_path = self.get_model_path(model)
        if not model_path.exists():
            return False

        if isinstance(model, ModelSpec):
            files = model.source.get("files")
            if files:
                return all((model_path / f).exists() for f in files)
            return any(model_path.iterdir())

        # Legacy ModelInfo check
        return (model.hf_repo and (any(model_path.glob("*.bin")) or any(model_path.glob("*.safetensors")))) or (
            model.download_url and model_path.is_dir() and any(model_path.iterdir())
        )

    def get_status(self, model: ModelInfo | ModelSpec) -> ModelStatus:
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

    def get_progress(self, model: ModelInfo | ModelSpec) -> float:
        """Get download progress (0.0 to 1.0)."""
        return self._download_progress.get(model.id, 0.0)

    def download(
        self,
        model: ModelInfo | ModelSpec,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> None:
        """
        Start downloading a model in background.

        Args:
            model: Model to download (ModelInfo or ModelSpec)
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

    def _download_model(self, model: ModelInfo | ModelSpec) -> None:
        """Download a model (runs in background thread)."""
        try:
            callback = self._download_callbacks.get(model.id)

            if isinstance(model, ModelSpec):
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
            elif model.hf_repo:
                self._download_from_huggingface(model, callback)
            elif model.download_url:
                self._download_from_url(model, callback)

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

    def _download_from_huggingface(
        self,
        model: ModelInfo,
        callback: Callable[[str, float, str], None] | None,
    ) -> None:
        """Download model from Hugging Face Hub."""
        try:
            from huggingface_hub import HfApi, hf_hub_download
        except ImportError as err:
            raise RuntimeError(t("download_status_install_hf")) from err

        model_path = self.get_model_path(model)

        if callback:
            callback(model.id, 0.05, t("download_status_downloading").format(name=t(model.name)))

        api = HfApi()
        repo_info = api.repo_info(model.hf_repo, repo_type="model")
        files = list(repo_info.siblings or [])

        # Calculate total bytes (if available)
        total_bytes = 0
        for f in files:
            if getattr(f, "size", None):
                total_bytes += f.size

        def local_file_size(path: Path) -> int:
            try:
                return path.stat().st_size
            except Exception:
                return 0

        downloaded_bytes = 0
        downloaded_files = 0
        for f in files:
            local_path = model_path / f.rfilename
            if local_path.exists() and local_path.is_file():
                downloaded_files += 1
                downloaded_bytes += local_file_size(local_path)

        if callback:
            callback(model.id, 0.01, t("download_status_downloading").format(name=t(model.name)))

        last_reported = {"percent": -5}

        for f in files:
            hf_hub_download(
                repo_id=model.hf_repo,
                filename=f.rfilename,
                local_dir=str(model_path),
            )

            downloaded_files += 1
            if getattr(f, "size", None):
                downloaded_bytes += f.size
            else:
                downloaded_bytes += local_file_size(model_path / f.rfilename)

            if total_bytes > 0:
                progress = min(0.95, downloaded_bytes / total_bytes)
            else:
                progress = min(0.95, downloaded_files / max(1, len(files)))

            if callback:
                callback(model.id, progress, t("download_status_downloading").format(name=t(model.name)))

            percent = int(progress * 100)
            if percent - last_reported["percent"] >= 5:
                last_reported["percent"] = percent
                print(f"[ModelManager] {t(model.name)}: {percent}%")

        if callback:
            callback(model.id, 0.98, t("download_status_verifying"))
        print(f"[ModelManager] {t(model.name)}: 98% ({t('download_status_verifying')})")

    def _download_from_url(
        self,
        model: ModelInfo,
        callback: Callable[[str, float, str], None] | None,
    ) -> None:
        """Download model from direct URL."""
        import tarfile
        import tempfile
        import urllib.request
        import zipfile

        model_path = self.get_model_path(model)
        url = model.download_url

        if callback:
            callback(model.id, 0.05, t("download_status_downloading").format(name=t(model.name)))

        last_reported = {"percent": -5}

        with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_archive_suffix(url)) as tmp:
            tmp_path = tmp.name

            def report_progress(block_num, block_size, total_size):
                if total_size > 0:
                    progress = min(0.8, block_num * block_size / total_size * 0.8)
                    self._download_progress[model.id] = progress
                    if callback:
                        downloaded_mb = block_num * block_size / 1024 / 1024
                        total_mb = total_size / 1024 / 1024
                        callback(
                            model.id,
                            progress,
                            t("download_status_progress").format(
                                downloaded=f"{downloaded_mb:.0f}", total=f"{total_mb:.0f}"
                            ),
                        )
                    percent = int(progress * 100)
                    if percent - last_reported["percent"] >= 5:
                        last_reported["percent"] = percent
                        print(f"[ModelManager] {t(model.name)}: {percent}%")

            urllib.request.urlretrieve(url, tmp_path, report_progress)

        if callback:
            callback(model.id, 0.85, t("download_status_extracting"))
        print(f"[ModelManager] {t(model.name)}: 85% ({t('download_status_extracting')})")

        model_path.mkdir(parents=True, exist_ok=True)

        if url.endswith(".zip"):
            with zipfile.ZipFile(tmp_path, "r") as zf:
                zf.extractall(model_path.parent)
        elif url.endswith(".tar.bz2") or url.endswith(".tar.gz"):
            with tarfile.open(tmp_path, "r:*") as tf:
                tf.extractall(model_path.parent)

        os.unlink(tmp_path)

        # Notify completion
        if callback:
            callback(model.id, 1.0, t("download_status_complete"))
        print(f"[ModelManager] {t(model.name)}: 100% ({t('download_status_complete')})")

    @staticmethod
    def _get_archive_suffix(url: str) -> str:
        """Get archive suffix from URL."""
        if ".tar.bz2" in url:
            return ".tar.bz2"
        elif ".tar.gz" in url:
            return ".tar.gz"
        elif ".zip" in url:
            return ".zip"
        return ""

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
        import os
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

    def delete(self, model: ModelInfo) -> bool:
        """Delete a downloaded model."""
        import shutil

        model_path = self.get_model_path(model)
        if model_path.exists():
            try:
                shutil.rmtree(model_path)
                return True
            except Exception as e:
                print(f"[ModelManager] Delete error: {e}")
        return False

    def get_all_models(self) -> list[ModelInfo]:
        """Get list of all supported models (from registry)."""
        models = []
        for spec in self.registry.list():
            info = ModelInfo(
                id=spec.id,
                name=spec.display_name,
                model_type=ModelType.SHERPA,
                size_mb=0,
                description=spec.language,
                local_folder=spec.id,
            )
            models.append(info)
        return models

    def get_models_by_type(self, model_type: ModelType) -> list[ModelInfo]:
        """Get models of a specific type."""
        return [m for m in SUPPORTED_MODELS if m.model_type == model_type]
