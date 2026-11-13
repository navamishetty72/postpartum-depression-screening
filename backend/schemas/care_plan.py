"""Pydantic schemas for Care Plan entities and API requests/responses."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class CarePlanPriorityEnum(str, Enum):
    """Care plan priority tiers according to contract."""
    routine = "routine"
    urgent = "urgent"
    crisis = "crisis"


class InterventionTypeEnum(str, Enum):
    """Agreed intervention types."""
    counseling = "counseling"
    psychiatry = "psychiatry"
    obgyn_followup = "obgyn_followup"
    support_group = "support_group"
    tele_manas = "tele_manas"


class CarePlanStatusEnum(str, Enum):
    """Agreed care plan lifecycle statuses."""
    active = "active"
    completed = "completed"
    discontinued = "discontinued"


class CarePlanUpsertRequest(BaseModel):
    """Payload to create or update a mother's care plan."""

    model_config = ConfigDict(extra="forbid")

    screening_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional UUID of the screening triggering this plan",
    )
    priority: CarePlanPriorityEnum = Field(
        default=CarePlanPriorityEnum.routine,
        description="Priority tier: 'routine', 'urgent', 'crisis'",
    )
    intervention_type: InterventionTypeEnum = Field(
        ...,
        description="Intervention type: 'counseling', 'psychiatry', 'obgyn_followup', 'support_group', 'tele_manas'",
    )
    referral_destination: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Referral target clinic, hospital, helpline, or organization",
        examples=["Tele-MANAS & District Hospital Perinatal Unit"],
    )
    scheduled_followup_date: Optional[date] = Field(
        default=None,
        description="Scheduled clinical follow-up date (YYYY-MM-DD)",
        examples=["2026-11-20"],
    )
    assigned_clinician_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="ID of clinician managing this plan",
        examples=["DOC-101"],
    )
    status: CarePlanStatusEnum = Field(
        default=CarePlanStatusEnum.active,
        description="Care plan status: 'active', 'completed', 'discontinued'",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Plan objectives, patient instructions, or clinical notes",
    )


class CarePlanResponse(BaseModel):
    """Response schema representing a Care Plan entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique care plan identifier (UUID)")
    mother_id: uuid.UUID = Field(..., description="UUID of the mother")
    screening_id: Optional[uuid.UUID] = Field(default=None, description="UUID of the triggering screening")
    priority: str = Field(..., description="Priority ('routine', 'urgent', 'crisis')")
    intervention_type: str = Field(..., description="Intervention type")
    referral_destination: Optional[str] = Field(default=None, description="Referral destination")
    scheduled_followup_date: Optional[date] = Field(default=None, description="Scheduled follow-up date")
    assigned_clinician_id: Optional[str] = Field(default=None, description="Assigned clinician identifier")
    status: str = Field(..., description="Care plan status ('active', 'completed', 'discontinued')")
    notes: Optional[str] = Field(default=None, description="Clinical plan notes")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last modification timestamp (UTC)")

