"""Mother patient entity model representing postpartum mothers enrolled in screening."""

from datetime import date
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import Date, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.screening import Screening
    from backend.models.clinical_review import ClinicalReview
    from backend.models.care_plan import CarePlan


class Mother(Base, TimestampMixin):
    """Represents a postpartum mother registered in the MIORA clinical screening system.

    Aligned strictly with the team's shared API contract:
    - id (UUID)
    - name (str)
    - age (int, optional)
    - phone (str, optional)
    - email (str, optional)
    - delivery_date (date, optional)
    - pregnancy_type (str, optional)
    - medical_history (str, optional)
    - notes (str, optional)
    - created_at (datetime UTC)
    - updated_at (datetime UTC)
    """

    __tablename__ = "mothers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique primary key identifier (UUID)",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        doc="Full name of the mother",
    )
    age: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Age in years",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        index=True,
        nullable=True,
        doc="Primary phone / mobile contact number",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(128),
        index=True,
        nullable=True,
        doc="Primary email address",
    )
    delivery_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Date of delivery (most recent infant)",
    )
    pregnancy_type: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="Pregnancy type (e.g. 'singleton', 'twins', 'multiples', 'cesarean', 'vaginal')",
    )
    medical_history: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Clinical medical history and obstetrical background notes",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Administrative or observational notes",
    )

    # Relationships
    screenings: Mapped[List["Screening"]] = relationship(
        "Screening",
        back_populates="mother",
        cascade="all, delete-orphan",
        order_by="desc(Screening.created_at)",
    )
    clinical_reviews: Mapped[List["ClinicalReview"]] = relationship(
        "ClinicalReview",
        back_populates="mother",
        cascade="all, delete-orphan",
        order_by="desc(ClinicalReview.created_at)",
    )
    care_plans: Mapped[List["CarePlan"]] = relationship(
        "CarePlan",
        back_populates="mother",
        cascade="all, delete-orphan",
        order_by="desc(CarePlan.created_at)",
    )

    def __repr__(self) -> str:
        return f"<Mother(id={self.id}, name='{self.name}', phone='{self.phone}')>"
