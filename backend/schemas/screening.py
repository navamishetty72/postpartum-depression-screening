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

