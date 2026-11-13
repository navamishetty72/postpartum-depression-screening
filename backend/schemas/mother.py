"""Pydantic schemas for Mother management entities and API contracts."""

from datetime import date, datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class MotherBase(BaseModel):
    """Base schema defining common attributes of a Mother entity."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Full legal or preferred name of the mother",
        examples=["Ananya Sharma"],
    )
    age: Optional[int] = Field(
        default=None,
        ge=10,
        le=120,
        description="Age in years",
        examples=[29],
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Primary phone or mobile contact number",
        examples=["+91-9876543210"],
    )
    email: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Primary email address",
        examples=["ananya.sharma@example.com"],
    )
    delivery_date: Optional[date] = Field(
        default=None,
        description="Date of delivery (most recent infant)",
        examples=["2026-10-01"],
    )
    pregnancy_type: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Pregnancy type (e.g. 'singleton', 'twins', 'cesarean')",
        examples=["singleton"],
    )
    medical_history: Optional[str] = Field(
        default=None,
        description="Clinical medical history and obstetrical background notes",
        examples=["Gestational hypertension managed with labetalol. Primigravida."],
    )
    notes: Optional[str] = Field(
        default=None,
        description="Administrative or observational notes",
        examples=["Referred from postpartum routine checkup clinic."],
    )


class MotherCreate(MotherBase):
    """Schema for registering a new Mother record."""
    pass


class MotherUpdate(BaseModel):
    """Schema for updating an existing Mother record. All fields are optional."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Full legal or preferred name of the mother",
    )
    age: Optional[int] = Field(
        default=None,
        ge=10,
        le=120,
        description="Age in years",
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Primary phone or mobile contact number",
    )
    email: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Primary email address",
    )
    delivery_date: Optional[date] = Field(
        default=None,
        description="Date of delivery (most recent infant)",
    )
    pregnancy_type: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Pregnancy type",
    )
    medical_history: Optional[str] = Field(
        default=None,
        description="Clinical medical history and obstetrical background notes",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Administrative or observational notes",
    )


class MotherResponse(MotherBase):
    """Schema returned for a Mother entity across API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID)",
        examples=["94c8d062-dc11-4a0f-8a0e-cd5e504f1098"],
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp of registration (UTC)",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp of last modification (UTC)",
    )

