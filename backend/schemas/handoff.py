"""Pydantic schemas for Screening Handoff requests and responses."""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ScreeningHandoffRequest(BaseModel):
    """Payload to initiate a clinical screening handoff."""

    model_config = ConfigDict(extra="forbid")

    clinician_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="ID of clinician or coordinator initiating the handoff",
        examples=["COORD-404"],
    )
    destination: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Designated clinical handoff destination (e.g. 'Perinatal Crisis Unit', 'Tele-MANAS')",
        examples=["Perinatal Crisis Unit"],
    )
    urgency: str = Field(
        default="routine",
        description="Handoff urgency tier ('routine', 'urgent', 'crisis')",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Handoff administrative or clinical routing instructions",
    )


class ScreeningHandoffResponse(BaseModel):
    """Response describing the recorded handoff event."""

    model_config = ConfigDict(from_attributes=True)

    screening_id: uuid.UUID
    mother_id: uuid.UUID
    destination: str
    urgency: str
    q10_safety_alert_preserved: bool
    handoff_recorded_at: datetime
    status: str = Field(
        default="RECORDED_IN_AUDIT_LOG",
        description="Status based strictly on what the system actually records.",
    )
    disclaimer: str = Field(
        default=(
            "Handoff event recorded in clinical audit log. No external emergency service "
            "or telephony dispatch was automatically invoked by this endpoint."
        )
    )

