"""Audit Log entity model tracking clinical data modifications and regulatory audit trails."""

from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import DateTime, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base, utc_now


class AuditLog(Base):
    """Immutable audit log record capturing clinical actions, data accesses, and changes.

    CRITICAL PRIVACY RULE:
    Never store raw sensitive patient narratives, free text speech transcripts,
    or raw forum quotes in audit logs. Store only sanitized action metadata,
    resource identifiers, and system events.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique audit record identifier (UUID)",
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Action performed (e.g. 'create_mother', 'record_screening', 'update_care_plan', 'override_risk')",
    )
    resource_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Type of entity affected (e.g. 'mother', 'screening', 'clinical_review', 'care_plan')",
    )
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="Stringified UUID or identifier of affected entity",
    )
    actor_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Identifier of user, clinician, or system agent executing action",
    )
    actor_role: Mapped[str] = mapped_column(
        String(32),
        default="clinician",
        nullable=False,
        doc="Role of actor at event time ('clinician', 'admin', 'system')",
    )
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Sanitized metadata and event reason (strictly no raw patient narrative or PII)",
    )
    client_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="Client IP address (IPv4 or IPv6)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
        doc="Timestamp of action occurrence (UTC)",
    )

    __table_args__ = (
        Index("ix_audit_logs_actor_action", "actor_id", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', "
            f"resource='{self.resource_type}:{self.resource_id}', actor='{self.actor_id}')>"
        )
