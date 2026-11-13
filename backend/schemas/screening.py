"""Pydantic v2 schemas for the Central Multimodal Screening Analysis API.

Defines request/response contracts for POST /api/screenings/analyze, supporting
multimodal dispatch (clinical, text, audio, video) and partial completion states
without fabricating predictions or diagnostic scores.
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

ModalityStatus = Literal["completed", "unavailable", "failed", "not_requested"]
OverallScreeningStatus = Literal["completed", "partially_completed", "failed"]


class ModalitiesSelection(BaseModel):
    """Normalized modality flags indicating which screening signals were requested."""

    model_config = ConfigDict(extra="ignore")

    clinical: bool = False
    text: bool = False
    audio: bool = False
    video: bool = False

    @classmethod
    def from_raw(cls, raw: Union[str, Dict[str, Any], List[str]]) -> "ModalitiesSelection":
        """Parse raw modalities from JSON string, dictionary, or list of strings."""
        import json

        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                raise ValueError("Modalities string cannot be empty.")
            try:
                parsed = json.loads(raw)
            except Exception as exc:
                raise ValueError(f"Invalid modalities JSON format: {exc}") from exc
        else:
            parsed = raw

        if isinstance(parsed, list):
            # Format: ["clinical", "text"] or ["text", "voice", "video"]
            items = {str(item).strip().lower() for item in parsed}
            return cls(
                clinical="clinical" in items,
                text="text" in items,
                audio="audio" in items or "voice" in items,
                video="video" in items,
            )
        elif isinstance(parsed, dict):
            # Format: {"clinical": true, "text": true, "audio": false, "video": false}
            # Or {"voice": true}
            return cls(
                clinical=bool(parsed.get("clinical", False)),
                text=bool(parsed.get("text", False)),
                audio=bool(parsed.get("audio", parsed.get("voice", False))),
                video=bool(parsed.get("video", False)),
            )
        else:
            raise ValueError(f"Unsupported modalities format: expected object or list, got {type(parsed).__name__}")


class ClinicalModalityResult(BaseModel):
    """Inference results produced by the ClinicalScreeningService (Random Forest)."""

    model_config = ConfigDict(extra="ignore")

    status: ModalityStatus = Field(
        ...,
        description="'completed', 'unavailable', 'failed', or 'not_requested'",
    )
    prediction: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured prediction containing risk probability, predicted class, and risk tier",
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Underlying baseline model utilized (e.g. 'random_forest')",
    )
    error: Optional[str] = Field(
        default=None,
        description="Diagnostic error description if execution failed",
    )


class TextModalityResult(BaseModel):
    """Extraction results produced by the TextNERService (Biomedical MMLite spans)."""

    model_config = ConfigDict(extra="ignore")

    status: ModalityStatus = Field(
        ...,
        description="'completed', 'unavailable', 'failed', or 'not_requested'",
    )
    processing_type: Optional[str] = Field(
        default="biomedical_ner",
        description="Type of NLP extraction executed",
    )
    entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of detected biomedical entity spans",
    )
    total_entities_detected: Optional[int] = Field(
        default=None,
        description="Count of identified biomedical entity spans",
    )
    processed_character_count: Optional[int] = Field(
        default=None,
        description="Total character count processed by the model",
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Text NER model release version",
    )
    error: Optional[str] = Field(
        default=None,
        description="Diagnostic error description if extraction failed",
    )


class AudioModalityResult(BaseModel):
    """Status placeholder for acoustic audio screening inference."""

    model_config = ConfigDict(extra="ignore")

    status: ModalityStatus = Field(
        default="unavailable",
        description="'unavailable' until unimodal acoustic inference model is deployed",
    )
    prediction: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Reserved for acoustic inference predictions",
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Acoustic model version string",
    )
    message: Optional[str] = Field(
        default=None,
        description="Informative message regarding modality availability",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error description if an attempt failed",
    )


class VideoModalityResult(BaseModel):
    """Status placeholder for visual dynamics/facial action unit screening inference."""

    model_config = ConfigDict(extra="ignore")

    status: ModalityStatus = Field(
        default="unavailable",
        description="'unavailable' until visual dynamics inference model is deployed",
    )
    prediction: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Reserved for visual dynamics predictions",
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Visual dynamics model version string",
    )
    message: Optional[str] = Field(
        default=None,
        description="Informative message regarding modality availability",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error description if an attempt failed",
    )


class FusionModalityResult(BaseModel):
    """Status placeholder for multimodal late fusion combiner."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(
        default="not_available",
        description="'not_available' pending multimodal fusion model deployment",
    )
    combined_score: Optional[float] = Field(
        default=None,
        description="Calibrated multimodal risk probability",
    )
    risk_category: Optional[str] = Field(
        default=None,
        description="Multimodal composite risk tier",
    )
    epds_equivalent: Optional[int] = Field(
        default=None,
        description="Estimated equivalent EPDS score",
    )
    modality_contributions: Dict[str, float] = Field(
        default_factory=dict,
        description="Relative weight/attribution of each modality to composite score",
    )
    discordance_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Cross-modal divergence metrics",
    )
    research_benchmarks: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Empirical multimodal benchmark metrics comparing single-modality and fusion architectures",
    )


class ScreeningAnalysisResponse(BaseModel):
    """Structured response returned by POST /api/screenings/analyze."""

    model_config = ConfigDict(extra="ignore")

    screening_id: str = Field(..., description="Unique screening session identifier (UUID)")
    mother_id: str = Field(..., description="Registered participant / patient identifier")
    status: OverallScreeningStatus = Field(
        ...,
        description="'completed', 'partially_completed', or 'failed'",
    )
    clinical: ClinicalModalityResult
    text: TextModalityResult
    audio: AudioModalityResult
    video: VideoModalityResult
    fusion: FusionModalityResult
    processed_at: str = Field(..., description="ISO-8601 UTC timestamp of screening completion")

