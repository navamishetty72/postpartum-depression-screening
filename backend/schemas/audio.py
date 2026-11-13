"""Pydantic v2 schemas for the Acoustic Audio screening foundation.

Defines schemas for the seven acoustic summary features, acoustic feature validation,
and structured audio screening inference responses with strict provenance tracking
and non-predictive safeguards.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from pipelines.synthetic_audio.config import (
    ACOUSTIC_FEATURE_BOUNDS,
    ACOUSTIC_FEATURE_NAMES,
    DATA_ORIGIN_TAG,
)


class AcousticFeatures(BaseModel):
    """Schema validating the seven canonical acoustic summary predictors.

    Enforces physiological plausibility bounds based on clinical voice literature priors.
    Disallows unknown extra features to prevent silent schema drift.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    f0_mean_hz: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["f0_mean_hz"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["f0_mean_hz"][1],
        description="Mean fundamental frequency in Hertz [130.0, 310.0]",
    )
    f0_std_hz: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["f0_std_hz"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["f0_std_hz"][1],
        description="Standard deviation of fundamental frequency in Hertz [8.0, 75.0]",
    )
    jitter_local_percent: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["jitter_local_percent"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["jitter_local_percent"][1],
        description="Local cycle-to-cycle pitch perturbation percentage [0.20, 5.50]",
    )
    shimmer_local_percent: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["shimmer_local_percent"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["shimmer_local_percent"][1],
        description="Local cycle-to-cycle amplitude perturbation percentage [1.00, 16.00]",
    )
    hnr_db: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["hnr_db"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["hnr_db"][1],
        description="Harmonics-to-noise ratio in decibels [8.00, 30.00]",
    )
    speech_rate_syllables_per_sec: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["speech_rate_syllables_per_sec"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["speech_rate_syllables_per_sec"][1],
        description="Speech rate measured in syllables per second [1.80, 6.20]",
    )
    pause_ratio: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["pause_ratio"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["pause_ratio"][1],
        description="Ratio of total silence/pause duration to total recording time [0.08, 0.65]",
    )


class AudioInferenceRequest(BaseModel):
    """Request payload for audio feature inference."""

    model_config = ConfigDict(extra="forbid")

    mother_id: Optional[str] = Field(
        default=None,
        description="Optional participant / mother identifier",
    )
    features: AcousticFeatures = Field(
        ...,
        description="The seven canonical acoustic summary predictors",
    )


class AudioPredictionDetails(BaseModel):
    """Reserved structure for validated audio model predictions."""

    model_config = ConfigDict(extra="ignore")

    predicted_risk_probability: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Reserved for calibrated PPD risk probability (None when uncalibrated/unavailable)",
    )
    predicted_class: Optional[int] = Field(
        default=None,
        ge=0,
        le=1,
        description="Reserved for binary screening classification (None when unavailable)",
    )
    risk_category: Optional[str] = Field(
        default=None,
        description="Categorical risk tier: 'HIGH_RISK', 'MODERATE_RISK', or 'LOW_RISK'",
    )


class AudioScreeningResponse(BaseModel):
    """Structured response schema for audio screening inference."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(
        default="unavailable",
        description="Execution status ('completed', 'unavailable', 'failed')",
    )
    is_predictive: bool = Field(
        default=False,
        description="Whether this modality output is clinically validated for predictive risk (strictly False for synthetic/experimental audio)",
    )
    data_origin: str = Field(
        default=DATA_ORIGIN_TAG,
        description="Provenance classification tag for the input acoustic domain",
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Audio model version string (None if model weights are not loaded)",
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Audio model identifier or architecture name",
    )
    prediction: Optional[AudioPredictionDetails] = Field(
        default=None,
        description="Prediction details (strictly None when weights are unavailable or non-predictive; never fabricated)",
    )
    acoustic_features: Optional[AcousticFeatures] = Field(
        default=None,
        description="Validated acoustic summary feature values",
    )
    message: Optional[str] = Field(
        default=None,
        description="Informative message regarding model availability and operational status",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error details if execution or validation failed",
    )
    disclaimer: str = Field(
        default="Research Prototype Benchmark Only — Synthetic/experimental acoustic fixtures are non-predictive and cannot validate clinical diagnostic efficacy.",
        description="Clinical safety and non-diagnostic research disclaimer",
    )


__all__ = [
    "ACOUSTIC_FEATURE_BOUNDS",
    "ACOUSTIC_FEATURE_NAMES",
    "AcousticFeatures",
    "AudioInferenceRequest",
    "AudioPredictionDetails",
    "AudioScreeningResponse",
]

