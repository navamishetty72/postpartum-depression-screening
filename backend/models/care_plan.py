"""Care Plan entity model representing post-screening intervention and follow-up management."""

from datetime import date
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import Date, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.mother import Mother
    from backend.models.screening import Screening


class CarePlan(Base, TimestampMixin):
    """Represents a clinician-managed intervention, referral, or monitoring care plan for a mother."""

    __tablename__ = "care_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique care plan identifier (UUID)",
    )
    mother_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("mothers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to the enrolled Mother",
    )
    screening_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("screenings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional reference to the screening that triggered this plan",
    )
    priority: Mapped[str] = mapped_column(
        String(32),
        default="routine",
        nullable=False,
        index=True,
        doc="Plan priority tier: 'routine', 'urgent', 'crisis'",
    )
    intervention_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Intervention category: 'counseling', 'psychiatry', 'obgyn_followup', 'support_group', 'tele_manas'",
    )
    referral_destination: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        doc="Target hospital, clinic, helpline, or community mental health organization",
    )
    scheduled_followup_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        index=True,
        doc="Target date for next check-in or clinical follow-up appointment",
    )
    assigned_clinician_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="ID of clinician responsible for coordinating or executing this plan",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
        index=True,
        doc="Care plan lifecycle status: 'active', 'completed', 'discontinued'",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed plan goals, patient instructions, or clinical notes",
    )

    # Relationships
    mother: Mapped["Mother"] = relationship(
        "Mother",
        back_populates="care_plans",
    )
    screening: Mapped[Optional["Screening"]] = relationship(
        "Screening",
        back_populates="care_plans",
    )

    __table_args__ = (
        Index("ix_care_plans_priority_status", "priority", "status"),
        Index("ix_care_plans_followup_status", "scheduled_followup_date", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<CarePlan(id={self.id}, mother_id={self.mother_id}, "
            f"type='{self.intervention_type}', priority='{self.priority}', status='{self.status}')>"
        )
