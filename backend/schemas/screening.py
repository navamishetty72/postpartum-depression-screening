"""Pydantic schemas for Screening persistence, individual retrieval, and historical listing."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ScreeningStatusEnum(str, Enum):
    """Agreed screening lifecycle status enum."""
    completed = "completed"
    partially_completed = "partially_completed"
    failed = "failed"


class ModalityStatusEnum(str, Enum):
    """Agreed individual modality execution status enum."""
    completed = "completed"
    unavailable = "unavailable"
    failed = "failed"
    not_requested = "not_requested"


class FusionStatusEnum(str, Enum):
    """Agreed multimodal fusion execution status enum."""
    completed = "completed"
    not_available = "not_available"
    insufficient_data = "insufficient_data"
    failed = "failed"


class ScreeningPersistRequest(BaseModel):
    """Payload provided to persist a screening session and Member 1 multimodal results.

    Member 1 calls this persistence interface after completing analysis.
    """

    model_config = ConfigDict(extra="forbid")

    mother_id: uuid.UUID = Field(
        ...,
        description="UUID of the enrolled Mother patient",
    )
    instrument: str = Field(
        default="EPDS",
        max_length=64,
        description="Instrument used (defaults to EPDS)",
    )
    total_score: int = Field(
        ...,
        ge=0,
        le=30,
        description="Total computed score from instrument (0-30 for EPDS)",
    )
    risk_classification: str = Field(
        ...,
        max_length=32,
        description="Risk tier assessed from instrument (e.g. 'low', 'moderate', 'high')",
    )
    q10_safety_alert: bool = Field(
        ...,
        description="Whether Question 10 (self-harm) safety alert was triggered. Must never be overridden.",
    )
    submitted_answers: Dict[str, Any] = Field(
        default_factory=dict,
        description="Map of question IDs to submitted user responses",
    )
    item_scores: Dict[str, int] = Field(
        default_factory=dict,
        description="Map of individual question IDs to numeric scores (0-3)",
    )
    screening_status: ScreeningStatusEnum = Field(
        default=ScreeningStatusEnum.completed,
        description="Overall screening execution status ('completed', 'partially_completed', 'failed')",
    )
    fusion_status: FusionStatusEnum = Field(
        default=FusionStatusEnum.not_available,
        description="Multimodal fusion status ('completed', 'not_available', 'insufficient_data', 'failed')",
    )
    modality_status: Dict[str, ModalityStatusEnum] = Field(
        default_factory=dict,
        description="Status map for each evaluated modality: {'text': 'completed', 'audio': 'unavailable', ...}",
    )
    model_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Member 1 model versions, feature extraction parameters, or execution metadata",
    )
    multimodal_scores: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured prediction outputs from Member 1 models and fusion",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Administrative or intake notes",
    )


class ScreeningResponse(BaseModel):
    """Structured response schema for individual screening retrieval and history."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique screening identifier (UUID)")
    mother_id: uuid.UUID = Field(..., description="Identifier of the enrolled Mother (UUID)")
    screening_date: datetime = Field(..., description="Date and time of screening administration (UTC)")
    instrument: str = Field(..., description="Screening instrument used (e.g. 'EPDS')")
    total_score: int = Field(..., description="Computed score from instrument (0-30)")
    risk_classification: str = Field(..., description="Assessed clinical risk tier")
    q10_safety_alert: bool = Field(..., description="True if self-harm safety alert was triggered")
    screening_status: str = Field(..., description="Screening lifecycle status")
    fusion_status: str = Field(..., description="Multimodal fusion status")
    modality_status: Dict[str, str] = Field(..., description="Per-modality execution status")
    submitted_answers: Dict[str, Any] = Field(..., description="Submitted answers mapping")
    item_scores: Dict[str, int] = Field(..., description="Item scores mapping")
    model_metadata: Dict[str, Any] = Field(..., description="Model metadata and pipeline info")
    multimodal_scores: Dict[str, Any] = Field(..., description="Structured multimodal prediction outputs")
    notes: Optional[str] = Field(default=None, description="Administrative or intake notes")
    created_at: datetime = Field(..., description="Record creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Record last modification timestamp (UTC)")


class ScreeningHistoryResponse(BaseModel):
    """Response container for a mother's screening history."""

    mother_id: uuid.UUID
    screenings: List[ScreeningResponse]
    total_count: int
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

