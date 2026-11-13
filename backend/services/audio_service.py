"""Service layer for Audio (Acoustic) ML screening inference.

Manages audio model lifecycle, loads trained Audio Random Forest and StandardScaler artifacts,
and predicts postpartum depression screening risk from 7 acoustic vocal biomarker features.

SCIENTIFIC INTEGRITY NOTICE:
Outputs are experimental and derived from clinically-conditioned synthetic acoustic feature
simulations. They do NOT represent authentic voice recordings or real-world audio diagnosis.
"""

import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger("ppd.audio_screening")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_AUDIO_ARTIFACTS_DIR = PROJECT_ROOT / "models" / "audio_model"

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
    """Inference service for the acoustic audio screening modality."""

    def __init__(
        self,
        artifacts_dir: Optional[Path] = None,
        model_name: str = "random_forest",
    ) -> None:
        self.artifacts_dir: Path = Path(artifacts_dir) if artifacts_dir else DEFAULT_AUDIO_ARTIFACTS_DIR
        self.model_name: str = model_name
        self._scaler: Optional[Any] = None
        self._model: Optional[Any] = None
        self._lock = threading.Lock()
        self._is_loaded: bool = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded and self._scaler is not None and self._model is not None

    def startup(self) -> None:
        """Load audio scaler and classifier once at application startup."""
        with self._lock:
            if self.is_loaded:
                return

            scaler_path = self.artifacts_dir / "scaler.joblib"
            model_path = self.artifacts_dir / f"{self.model_name}.joblib"

            if not scaler_path.exists() or not model_path.exists():
                logger.warning(
                    "Audio model artifacts missing at %s; acoustic inference will be unavailable.",
                    self.artifacts_dir,
                )
                self._is_loaded = False
                return

            try:
                self._scaler = joblib.load(scaler_path)
                self._model = joblib.load(model_path)
                self._is_loaded = True
                logger.info(
                    "Audio screening service loaded successfully: model=%s from %s",
                    self.model_name,
                    self.artifacts_dir,
                )
            except Exception as exc:
                logger.error("Failed to load audio model artifacts: %s", exc, exc_info=True)
                self._is_loaded = False

    def predict(
        self,
        features: Dict[str, Any],
        threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Score acoustic vocal features for PPD risk.

        Args:
            features: Dictionary containing the 7 expected acoustic features.
            threshold: Decision threshold for high-risk binary classification.

        Returns:
            Structured prediction dictionary matching the screening modality contract.
        """
        if not self.is_loaded:
            self.startup()
            if not self.is_loaded:
                raise HTTPException(
                    status_code=503,
                    detail="Audio screening inference model is unavailable.",
                )

        # Validate 7 required features
        missing = [f for f in EXPECTED_AUDIO_FEATURES if f not in features]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Missing required audio features: {sorted(missing)}. Expected {EXPECTED_AUDIO_FEATURES}.",
            )

        try:
            values = [float(features[f]) for f in EXPECTED_AUDIO_FEATURES]
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Audio features must be numeric floating-point values: {exc}",
            )

        # Create DataFrame with exact column names to avoid sklearn feature-name warnings
        df_features = pd.DataFrame([values], columns=EXPECTED_AUDIO_FEATURES)

        try:
            scaled = self._scaler.transform(df_features)
            prob = float(self._model.predict_proba(scaled)[0, 1])
        except Exception as exc:
            logger.error("Audio model inference failed: %s", exc, exc_info=True)
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

        return {
            "predicted_risk_probability": round(prob, 4),
            "predicted_class": pred,
            "risk_category": category,
            "decision_threshold": threshold,
            "model_utilized": f"audio_{self.model_name}_v1",
            "data_origin": "CLINICALLY_CONDITIONED_SYNTHETIC",
            "provenance_notice": (
                "Generated synthetic acoustic feature profiles from clinical conditioning. "
                "Not authentic patient voice recordings."
            ),
            "clinical_disclaimer": (
                "Research Prototype Benchmark Only — Synthetic simulation data. "
                "Not clinically validated for medical diagnosis."
            ),
        }


# Global singleton instance
audio_service = AudioScreeningService()


def get_audio_service() -> AudioScreeningService:
    """FastAPI dependency provider for AudioScreeningService."""
    return audio_service
