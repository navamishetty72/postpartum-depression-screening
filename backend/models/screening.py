"""Screening entity model representing clinical screening sessions and multimodal scores."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin, utc_now

if TYPE_CHECKING:
    from backend.models.mother import Mother
    from backend.models.clinical_review import ClinicalReview
    from backend.models.care_plan import CarePlan


class Screening(Base, TimestampMixin):
    """Represents a postpartum depression screening event.

    Retains questionnaire scores (e.g. EPDS), multimodal evaluation status,
    Member 1 ML inference metadata, and Q10 self-harm safety alerts.

    Adheres strictly to the team's shared API contract:
    - screening_status: 'completed', 'partially_completed', 'failed'
    - modality_status: 'completed', 'unavailable', 'failed', 'not_requested'
    - fusion_status: 'completed', 'not_available', 'insufficient_data', 'failed'
    - epds_q10_alert: affirmative answer to self-harm question (never overridden)
    - no fabricated predictions or combined risk scores
    """

    __tablename__ = "screenings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique screening event identifier (UUID)",
    )
    mother_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("mothers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to the enrolled Mother",
    )
    screening_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
        doc="Date and time of screening administration (UTC)",
    )
    instrument: Mapped[str] = mapped_column(
        String(64),
        default="EPDS",
        nullable=False,
        doc="Screening instrument used (e.g. 'EPDS')",
    )
    total_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Total computed score from instrument (0-30 for EPDS)",
    )
    risk_classification: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Assessed clinical risk tier (e.g. 'low', 'moderate', 'high')",
    )
    q10_safety_alert: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        nullable=False,
        doc="Indicates affirmative answer to self-harm question (e.g. EPDS Q10 > 0). Never overridden.",
    )
    submitted_answers: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Map of question IDs to submitted user answers",
    )
    item_scores: Mapped[Dict[str, int]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Map of individual question scores (0-3)",
    )
    screening_status: Mapped[str] = mapped_column(
        String(32),
        default="completed",
        nullable=False,
        index=True,
        doc="Lifecycle status: 'completed', 'partially_completed', 'failed'",
    )
    fusion_status: Mapped[str] = mapped_column(
        String(32),
        default="not_available",
        nullable=False,
        index=True,
        doc="Multimodal fusion status: 'completed', 'not_available', 'insufficient_data', 'failed'",
    )
    modality_status: Mapped[Dict[str, str]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Per-modality status: {'text': 'completed', 'audio': 'unavailable', 'video': 'not_requested'}",
    )
    model_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Member 1 ML model versions, features, and pipeline execution metadata",
    )
    multimodal_scores: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Structured prediction outputs from individual modalities and multimodal fusion",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Optional administrative or intake notes",
    )

    # Relationships
    mother: Mapped["Mother"] = relationship(
        "Mother",
        back_populates="screenings",
    )
    clinical_reviews: Mapped[List["ClinicalReview"]] = relationship(
        "ClinicalReview",
        back_populates="screening",
        cascade="all, delete-orphan",
        order_by="desc(ClinicalReview.created_at)",
    )
    care_plans: Mapped[List["CarePlan"]] = relationship(
        "CarePlan",
        back_populates="screening",
    )

    __table_args__ = (
        Index("ix_screenings_mother_date", "mother_id", "screening_date"),
        Index("ix_screenings_risk_alert", "risk_classification", "q10_safety_alert"),
        Index("ix_screenings_statuses", "screening_status", "fusion_status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Screening(id={self.id}, mother_id={self.mother_id}, "
            f"score={self.total_score}, risk='{self.risk_classification}', status='{self.screening_status}')>"
        )
