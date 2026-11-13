"""Pydantic v2 schemas for the Acoustic Audio screening foundation.

Defines schemas for the seven acoustic summary features, acoustic feature validation,
and structured audio screening inference responses with strict provenance tracking,
explicit physiological literature bounds, and non-predictive safeguards.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from pipelines.synthetic_audio.config import (
    ACOUSTIC_FEATURE_BOUNDS,
    ACOUSTIC_FEATURE_NAMES,
    DATA_ORIGIN_TAG,
)

# -----------------------------------------------------------------------------
# Peer-Reviewed Clinical & Phonetic Literature Citations for Acoustic Bounds
# -----------------------------------------------------------------------------
ACOUSTIC_FEATURE_LITERATURE_SOURCES: Dict[str, Dict[str, str]] = {
    "f0_mean_hz": {
        "range": "[130.0, 310.0] Hz",
        "normative_prior": "215.0 Hz",
        "source": "Titze, I.R. (1994) Principles of Voice Production; Baken & Orlikoff (2000) Clinical Measurement of Speech and Voice (Adult female modal fundamental frequency).",
    },
    "f0_std_hz": {
        "range": "[8.0, 75.0] Hz",
        "normative_prior": "28.0 Hz",
        "source": "Aronson & Bless (2009) Clinical Voice Disorders; Baken & Orlikoff (2000). Reduced pitch variability characterizes depressive flat affect.",
    },
    "jitter_local_percent": {
        "range": "[0.20, 5.50] %",
        "normative_prior": "1.20 % (Normative threshold < 1.04%)",
        "source": "Horii, Y. (1979) Fundamental frequency perturbation observed in sustained phonation; Boersma & Weenink (2023) Praat manual voice report.",
    },
    "shimmer_local_percent": {
        "range": "[1.00, 16.00] %",
        "normative_prior": "4.50 % (Normative threshold < 3.81%)",
        "source": "Horii, Y. (1980) Vocal shimmer in sustained phonation; Boersma & Weenink (2023) Praat normative standards.",
    },
    "hnr_db": {
        "range": "[8.00, 30.00] dB",
        "normative_prior": "20.0 dB (Healthy voice typical > 20 dB)",
        "source": "Yumoto et al. (1982) Harmonics-to-noise ratio as an index of the degree of hoarseness; de Krom, G. (1993) JSHR.",
    },
    "speech_rate_syllables_per_sec": {
        "range": "[1.80, 6.20] syllables/sec",
        "normative_prior": "3.80 syl/s",
        "source": "de Jong & Wempe (2009) Praat syllable nucleus detector; Cummins et al. (2015) Review of depression and suicide risk assessment using speech.",
    },
    "pause_ratio": {
        "range": "[0.08, 0.65]",
        "normative_prior": "0.24",
        "source": "Mundt et al. (2007) Voice acoustic measures of depression severity; Low et al. (2020) Automated analysis of speech in depression and psychomotor slowing.",
    },
}


class AcousticFeatures(BaseModel):
    """Schema validating the seven canonical acoustic summary predictors.

    Enforces physiological plausibility bounds based on peer-reviewed clinical voice
    literature priors (Titze 1994, Baken & Orlikoff 2000, Mundt 2007, Cummins 2015).
    Disallows unknown extra features via extra='forbid' to prevent silent schema drift.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    f0_mean_hz: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["f0_mean_hz"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["f0_mean_hz"][1],
        description="Mean fundamental frequency in Hertz [130.0, 310.0] (Adult female modal register; Titze 1994)",
    )
    f0_std_hz: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["f0_std_hz"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["f0_std_hz"][1],
        description="Standard deviation of fundamental frequency in Hertz [8.0, 75.0] (Pitch variability; Baken 2000)",
    )
    jitter_local_percent: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["jitter_local_percent"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["jitter_local_percent"][1],
        description="Local cycle-to-cycle pitch perturbation percentage [0.20, 5.50] (Horii 1979, Praat standard)",
    )
    shimmer_local_percent: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["shimmer_local_percent"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["shimmer_local_percent"][1],
        description="Local cycle-to-cycle amplitude perturbation percentage [1.00, 16.00] (Horii 1980, Praat standard)",
    )
    hnr_db: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["hnr_db"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["hnr_db"][1],
        description="Harmonics-to-noise ratio in decibels [8.00, 30.00] (Acoustic glottal breathiness; Yumoto 1982)",
    )
    speech_rate_syllables_per_sec: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["speech_rate_syllables_per_sec"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["speech_rate_syllables_per_sec"][1],
        description="Speech rate in syllables per second [1.80, 6.20] (Psychomotor rate; de Jong 2009, Cummins 2015)",
    )
    pause_ratio: float = Field(
        ...,
        ge=ACOUSTIC_FEATURE_BOUNDS["pause_ratio"][0],
        le=ACOUSTIC_FEATURE_BOUNDS["pause_ratio"][1],
        description="Ratio of total pause duration to speaking duration [0.08, 0.65] (Psychomotor retardation; Mundt 2007)",
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

    mother_id: Optional[str] = Field(
        default=None,
        description="Participant or mother identifier associated with this screening request",
    )
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
    "ACOUSTIC_FEATURE_LITERATURE_SOURCES",
    "ACOUSTIC_FEATURE_NAMES",
    "AcousticFeatures",
    "AudioInferenceRequest",
    "AudioPredictionDetails",
    "AudioScreeningResponse",
]
