"""SQLAlchemy Declarative Base for the MIORA Postpartum Depression Screening Platform."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base class with common representation and serialisation helpers."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert model column attributes to a serializable dictionary."""
        result: Dict[str, Any] = {}
        for column in self.__table__.columns:
            val = getattr(self, column.name)
            if isinstance(val, (datetime,)):
                result[column.name] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                result[column.name] = str(val)
            else:
                result[column.name] = val
        return result


class TimestampMixin:
    """Reusable mixin providing standard UTC audit timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="Timestamp when the entity was created (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        doc="Timestamp when the entity was last modified (UTC)",
    )

