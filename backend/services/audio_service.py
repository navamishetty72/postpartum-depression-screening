"""Service layer for Acoustic Audio screening inference and validation.

Manages audio model lifecycle, checks availability of trained checkpoints under models/audio_model/,
validates acoustic feature payloads against physiological bounds, and provides both
AudioScreeningResponse schemas (Phase 8C contract) and raw structured prediction dictionaries
for multimodal fusion orchestration.

SCIENTIFIC INTEGRITY & PROVENANCE NOTICE:
Current audio feature profiles and model artifacts are derived from clinically conditioned
synthetic acoustic simulations. They do NOT represent authentic patient voice recordings
and are strictly non-diagnostic research benchmarks. Audio models are strictly non-predictive
(is_predictive=False) and must remain excluded from predictive clinical late fusion.
"""

import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException
import joblib
import numpy as np
import pandas as pd

try:
    # pyrefly: ignore[missing-import]
    import torch
    HAS_TORCH = True
except ImportError:
    torch = None  # type: ignore
    HAS_TORCH = False

from backend.schemas.audio import (
    ACOUSTIC_FEATURE_BOUNDS,
    ACOUSTIC_FEATURE_LITERATURE_SOURCES,
    ACOUSTIC_FEATURE_NAMES,
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
DEFAULT_AUDIO_ARTIFACTS_DIR = DEFAULT_AUDIO_MODEL_DIR

EXPECTED_AUDIO_FEATURES: List[str] = [
    "f0_mean_hz",
    "f0_std_hz",
    "jitter_local_percent",
    "shimmer_local_percent",
    "hnr_db",
    "speech_rate_syllables_per_sec",
    "pause_ratio",
]


class AudioScreeningService:
    """Singleton service for audio acoustic screening inference, validation, and lifecycle management.

    Follows the architectural patterns of ClinicalScreeningService and TextNERService:
    - Thread-safe lazy or startup initialization.
    - Explicit is_loaded and is_available lifecycle readiness properties.
    - Safe handling of missing model checkpoints without crashing application startup.
    - Never trains models automatically during startup or inference.
    - Zero logging of sensitive patient biometric features or participant identifiers.
    """

    def __init__(
        self,
        model_dir: Optional[Union[str, Path]] = None,
        artifacts_dir: Optional[Union[str, Path]] = None,
        model_filename: str = "audio_model.pth",
        model_name: str = "random_forest",
    ) -> None:
        chosen_dir = model_dir or artifacts_dir or DEFAULT_AUDIO_MODEL_DIR
        self.model_dir: Path = Path(chosen_dir)
        self.artifacts_dir: Path = self.model_dir
        self.model_filename: str = model_filename
        self.model_name: str = model_name

        self._model: Any = None
        self._scaler: Optional[Any] = None
        self._rf_model: Optional[Any] = None
        self._model_version: Optional[str] = None
        self._is_available: bool = False
        self._load_error: Optional[str] = None
        self._startup_attempted: bool = False
        self._lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        """Whether a genuine trained audio model checkpoint or ML artifacts are loaded and ready."""
        return self._is_available and (self._model is not None or self._rf_model is not None)

    @property
    def is_available(self) -> bool:
        """Alias for is_loaded indicating modality readiness."""
        return self.is_loaded

    @property
    def model_dir_path(self) -> Path:
        """Configured path to audio model artifact directory."""
        return self.model_dir

    def startup(self) -> None:
        """Check for model weights and initialize audio pipeline if available.

        Never trains models automatically if checkpoints are missing.
        """
        with self._lock:
            self._startup_attempted = True
            model_path = self.model_dir / self.model_filename
            scaler_path = self.model_dir / "scaler.joblib"
            rf_path = self.model_dir / f"{self.model_name}.joblib"

            if not self.model_dir.exists():
                self._is_available = False
                self._load_error = f"Audio model directory does not exist: {self.model_dir}"
                logger.info(
                    "Audio screening model directory not found: %s. Service initialized in unavailable mode.",
                    self.model_dir,
                )
                return

            # 1. Check if PyTorch model checkpoint exists
            if self.model_filename and model_path.exists() and model_path.is_file():
                if not HAS_TORCH:
                    self._is_available = False
                    self._load_error = "Required dependency 'torch' is not installed."
                    logger.warning(
                        "Audio model checkpoint found at %s, but 'torch' is not installed.",
                        model_path,
                    )
                    return

                try:
                    state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
                    self._model = state_dict
                    self._is_available = True
                    self._model_version = "1.0.0"
                    self._load_error = None
                    logger.info("Audio screening model loaded successfully from %s", model_path)
                    return
                except Exception as exc:
                    self._model = None
                    self._is_available = False
                    self._load_error = f"Failed to load audio model: {exc}"
                    logger.warning("Error loading audio model checkpoint: %s", exc)
                    return

            # 2. Check if scikit-learn artifacts (scaler + model) exist
            if scaler_path.exists() and rf_path.exists():
                try:
                    self._scaler = joblib.load(scaler_path)
                    self._rf_model = joblib.load(rf_path)
                    self._is_available = True
                    self._model_version = f"audio_{self.model_name}_v1"
                    self._load_error = None
                    logger.info(
                        "Audio ML baseline (%s) loaded from %s",
                        self.model_name,
                        self.model_dir,
                    )
                    return
                except Exception as exc:
                    self._scaler = None
                    self._rf_model = None
                    self._is_available = False
                    self._load_error = f"Failed to load audio artifacts: {exc}"
                    logger.warning("Error loading audio ML baseline: %s", exc)
                    return

            # 3. Model files are missing
            self._is_available = False
            self._load_error = (
                f"Audio model weights missing under {self.model_dir} (neither {self.model_filename} "
                f"nor {scaler_path.name}/{rf_path.name} found)."
            )
            logger.info(
                "No audio models found under %s; initialized in unavailable mode.",
                self.model_dir,
            )

    def shutdown(self) -> None:
        """Release audio service resources on application shutdown."""
        with self._lock:
            if self._model is not None or self._rf_model is not None:
                logger.info("Shutting down audio screening service.")
            self._model = None
            self._scaler = None
            self._rf_model = None
            self._is_available = False
            self._startup_attempted = False
            self._load_error = None

    def predict(
        self,
        features: Union[AcousticFeatures, Dict[str, Any]],
        mother_id: Optional[str] = None,
        threshold: float = 0.5,
        as_response: bool = True,
    ) -> Union[AudioScreeningResponse, Dict[str, Any]]:
        """Execute audio screening inference or return explicit unavailable response.

        Never trains models automatically during inference.
        Never fabricates predictions when model artifacts are missing.
        Never logs participant identifiers or raw acoustic features.
        """
        if not self._startup_attempted:
            self.startup()

        # Validate input features against physiological bounds
        if isinstance(features, dict):
            validated_features = AcousticFeatures(**features)
        else:
            validated_features = features

        # When model weights or pipeline artifacts are missing or experimental
        if not self.is_loaded:
            if as_response:
                return AudioScreeningResponse(
                    mother_id=mother_id,
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
            raise HTTPException(
                status_code=503,
                detail=f"Audio screening inference model is unavailable: {self._load_error or 'No trained checkpoint deployed'}.",
            )

        # Execute inference if scikit-learn ML artifacts are loaded
        if self._scaler is not None and self._rf_model is not None:
            # Enforce exact feature ordering
            feature_row = [getattr(validated_features, f) for f in EXPECTED_AUDIO_FEATURES]
            df_features = pd.DataFrame([feature_row], columns=EXPECTED_AUDIO_FEATURES)

            try:
                scaled = self._scaler.transform(df_features)
                prob = float(self._rf_model.predict_proba(scaled)[0, 1])
            except Exception as exc:
                logger.error("Audio model inference execution failed: %s", type(exc).__name__, exc_info=False)
                raise HTTPException(
                    status_code=500,
                    detail="Acoustic feature inference failed due to an internal error.",
                ) from exc

            pred = int(prob >= threshold)
            if prob >= 0.70:
                category = "HIGH_RISK"
            elif prob >= 0.40:
                category = "MODERATE_RISK"
            else:
                category = "LOW_RISK"

            rounded_prob = round(prob, 4)
            pred_dict = {
                "predicted_risk_probability": rounded_prob,
                "predicted_class": pred,
                "risk_category": category,
                "decision_threshold": threshold,
                "model_utilized": self._model_version or f"audio_{self.model_name}_v1",
                "data_origin": DATA_ORIGIN_TAG,
                "provenance_notice": (
                    "Generated synthetic acoustic feature profiles from clinical conditioning. "
                    "Not authentic patient voice recordings."
                ),
                "clinical_disclaimer": (
                    "Research Prototype Benchmark Only — Synthetic simulation data. "
                    "Not clinically validated for medical diagnosis."
                ),
            }

            if as_response:
                return AudioScreeningResponse(
                    mother_id=mother_id,
                    status="completed",
                    is_predictive=False,  # strictly False for current synthetic experimental pipeline
                    data_origin=DATA_ORIGIN_TAG,
                    model_version=self._model_version,
                    model_name=self.model_name,
                    prediction=AudioPredictionDetails(
                        predicted_risk_probability=rounded_prob,
                        predicted_class=pred,
                        risk_category=category,
                        decision_threshold=threshold,
                    ),
                    acoustic_features=validated_features,
                    message="Audio feature profile processed under experimental non-predictive protocol.",
                )
            return pred_dict

        # Fallback for PyTorch or non-inferencing checkpoint
        if as_response:
            return AudioScreeningResponse(
                mother_id=mother_id,
                status="completed",
                is_predictive=False,
                data_origin=DATA_ORIGIN_TAG,
                model_version=self._model_version,
                model_name="PPDAudioCNN",
                prediction=None,
                acoustic_features=validated_features,
                message="Audio PyTorch checkpoint loaded under experimental non-predictive protocol.",
            )
        raise HTTPException(
            status_code=503,
            detail="Acoustic feature inference pipeline not configured for loaded model type.",
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
    "EXPECTED_AUDIO_FEATURES",
]
