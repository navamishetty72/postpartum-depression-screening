"""Pydantic schemas for Clinical Review entities and API requests/responses."""

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ReviewStatusEnum(str, Enum):
    """Clinical review status values according to agreed contract."""
    pending = "pending"
    confirmed = "confirmed"
    overridden = "overridden"


class ClinicalReviewCreate(BaseModel):
    """Request payload for creating a clinician-managed review."""

    model_config = ConfigDict(extra="forbid")

    mother_id: uuid.UUID = Field(..., description="UUID of the mother under review")
    screening_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional UUID of the specific screening evaluated",
    )
    clinician_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Clinician staff identifier",
        examples=["DOC-101"],
    )
    clinician_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Clinician full name and professional title",
        examples=["Dr. Radhika Iyer, MD"],
    )
    review_status: ReviewStatusEnum = Field(
        default=ReviewStatusEnum.confirmed,
        description="Review decision status: 'pending', 'confirmed', 'overridden'",
    )
    final_risk_classification: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Clinician's final assessed risk category (e.g. 'low', 'moderate', 'high')",
    )
    clinical_notes: Optional[str] = Field(
        default=None,
        description="Qualitative clinical impressions, behavioral observations, or rationale",
    )
    required_immediate_escalation: bool = Field(
        default=False,
        description="Whether immediate crisis escalation (e.g. Tele-MANAS, inpatient care) was ordered",
    )


class ClinicalReviewResponse(BaseModel):
    """Response schema for a Clinical Review record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique review identifier (UUID)")
    mother_id: uuid.UUID = Field(..., description="UUID of the mother")
    screening_id: Optional[uuid.UUID] = Field(default=None, description="UUID of the evaluated screening")
    clinician_id: str = Field(..., description="Clinician identifier")
    clinician_name: str = Field(..., description="Clinician name")
    review_status: str = Field(..., description="Review status ('pending', 'confirmed', 'overridden')")
    final_risk_classification: Optional[str] = Field(default=None, description="Clinician's final risk classification")
    clinical_notes: Optional[str] = Field(default=None, description="Clinical notes")
    required_immediate_escalation: bool = Field(..., description="Immediate escalation indicator")
    reviewed_at: datetime = Field(..., description="Timestamp of review completion (UTC)")
    created_at: datetime = Field(..., description="Record creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Record last modification timestamp (UTC)")

