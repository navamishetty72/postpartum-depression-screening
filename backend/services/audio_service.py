"""Service layer for Acoustic Audio screening inference.

Manages audio model lifecycle, checks availability of trained checkpoints under models/audio_model/,
validates acoustic feature payloads against physiological bounds, and enforces scientific
boundaries: synthetic/experimental audio features remain strictly non-predictive (is_predictive=False)
and never return fabricated risk probabilities.
"""

import logging
from pathlib import Path
import threading
from typing import Any, Dict, Optional, Union

from backend.schemas.audio import (
    AcousticFeatures,
    AudioPredictionDetails,
    AudioScreeningResponse,
)
from pipelines.synthetic_audio.config import (
    DATA_ORIGIN_TAG,
    PROJECT_ROOT,
)

logger = logging.getLogger("ppd.audio_service")

DEFAULT_AUDIO_MODEL_DIR = PROJECT_ROOT / "models" / "audio_model"


class AudioScreeningService:
    """Singleton service for audio acoustic screening inference and validation."""

    def __init__(
        self,
        model_dir: Optional[Union[str, Path]] = None,
        model_filename: str = "audio_model.pth",
    ) -> None:
        self.model_dir: Path = Path(model_dir) if model_dir else DEFAULT_AUDIO_MODEL_DIR
        self.model_filename: str = model_filename
        self._model: Any = None
        self._model_version: Optional[str] = None
        self._is_available: bool = False
        self._load_error: Optional[str] = None
        self._startup_attempted: bool = False
        self._lock = threading.Lock()

    @property
    def is_available(self) -> bool:
        """Whether a genuine trained audio model checkpoint is loaded and ready."""
        return self._is_available and self._model is not None

    @property
    def model_dir_path(self) -> Path:
        """Configured path to audio model artifact directory."""
        return self.model_dir

    def startup(self) -> None:
        """Check for model weights and initialize audio pipeline if available."""
        with self._lock:
            self._startup_attempted = True
            model_path = self.model_dir / self.model_filename

            if not self.model_dir.exists():
                self._is_available = False
                self._load_error = f"Audio model directory does not exist: {self.model_dir}"
                logger.info(
                    "Audio screening model directory not found: %s. Service initialized in unavailable mode.",
                    self.model_dir,
                )
                return

            if not model_path.exists():
                self._is_available = False
                self._load_error = f"Audio model weights missing: {model_path}"
                logger.info(
                    "Audio model checkpoint '%s' not found. Service initialized in unavailable mode.",
                    self.model_filename,
                )
                return

            try:
                # If weights exist in future, attempt load safely
                import torch
                state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
                self._model = state_dict
                self._is_available = True
                self._model_version = "1.0.0"
                self._load_error = None
                logger.info("Audio screening model loaded successfully from %s", model_path)
            except Exception as exc:
                self._model = None
                self._is_available = False
                self._load_error = f"Failed to load audio model: {exc}"
                logger.warning("Error loading audio model checkpoint: %s", exc)

    def shutdown(self) -> None:
        """Release audio service resources on application shutdown."""
        with self._lock:
            if self._model is not None:
                logger.info("Shutting down audio screening service.")
            self._model = None
            self._is_available = False
            self._startup_attempted = False
            self._load_error = None

    def predict(
        self,
        features: Union[AcousticFeatures, Dict[str, Any]],
        mother_id: Optional[str] = None,
    ) -> AudioScreeningResponse:
        """Execute audio screening inference or return explicit unavailable response."""
        if not self._startup_attempted:
            self.startup()

        # Validate input features
        if isinstance(features, dict):
            validated_features = AcousticFeatures(**features)
        else:
            validated_features = features

        # When model weights or pipeline artifacts are missing or experimental
        if not self.is_available:
            return AudioScreeningResponse(
                status="unavailable",
                is_predictive=False,
                data_origin=DATA_ORIGIN_TAG,
                model_version=None,
                model_name=None,
                prediction=None,
                acoustic_features=validated_features,
                message=(
                    f"Audio screening inference model is unavailable: {self._load_error or 'No trained checkpoint deployed'}. "
                    "Current audio feature profiles are synthetic benchmarks (non-predictive)."
                ),
                error=None,
                disclaimer=(
                    "Research Prototype Benchmark Only — Synthetic/experimental acoustic fixtures "
                    "are non-predictive and cannot validate clinical diagnostic efficacy."
                ),
            )

        # If a real model is loaded in future, preserve non-predictive flag for synthetic benchmarks
        return AudioScreeningResponse(
            status="completed",
            is_predictive=False,  # strictly False for current synthetic experimental pipeline
            data_origin=DATA_ORIGIN_TAG,
            model_version=self._model_version,
            model_name="PPDAudioCNN",
            prediction=None,  # Never generate dummy probability or fabricated prediction
            acoustic_features=validated_features,
            message="Audio feature profile processed under experimental non-predictive protocol.",
        )


# Global singleton instance and FastAPI dependency provider
audio_service = AudioScreeningService()


def get_audio_service() -> AudioScreeningService:
    """FastAPI dependency for accessing the AudioScreeningService singleton."""
    return audio_service


__all__ = [
    "AudioScreeningService",
    "audio_service",
    "get_audio_service",
]

