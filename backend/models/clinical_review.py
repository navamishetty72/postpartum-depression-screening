"""Clinical Review entity model representing clinician evaluation, verification, and overrides."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin, utc_now

if TYPE_CHECKING:
    from backend.models.mother import Mother
    from backend.models.screening import Screening


class ClinicalReview(Base, TimestampMixin):
    """Represents a formal clinical review conducted by a clinician.

    Clinicians can review algorithmically flagged screenings, confirm or override
    risk classifications, document qualitative impressions, and trigger care pathways.
    """

    __tablename__ = "clinical_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique review identifier (UUID)",
    )
    mother_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("mothers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to the mother under review",
    )
    screening_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("screenings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional reference to a specific screening event being evaluated",
    )
    clinician_id: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        doc="Identifier of the clinician performing the review",
    )
    clinician_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Display name or credentialed title of reviewing clinician",
    )
    review_status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
        doc="Review status: 'pending', 'confirmed', 'overridden'",
    )
    final_risk_classification: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        doc="Clinician's final assessed risk category (may differ from algorithmic score)",
    )
    clinical_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed clinical assessment, observational notes, and justification",
    )
    required_immediate_escalation: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Flag set when immediate crisis escalation was ordered (e.g. Tele-MANAS)",
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="Timestamp of clinical review completion (UTC)",
    )

    # Relationships
    mother: Mapped["Mother"] = relationship(
        "Mother",
        back_populates="clinical_reviews",
    )
    screening: Mapped[Optional["Screening"]] = relationship(
        "Screening",
        back_populates="clinical_reviews",
    )

    __table_args__ = (
        Index("ix_clinical_reviews_clinician_date", "clinician_id", "reviewed_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ClinicalReview(id={self.id}, mother_id={self.mother_id}, "
            f"clinician='{self.clinician_name}', status='{self.review_status}')>"
        )
