"""Audit logging service for tracking compliance and clinical application events.

PRIVACY SAFEGUARD:
Never store raw patient narratives, audio transcripts, forum quotes, passwords,
API keys, or sensitive clinical notes in audit logs.
Store only structured entity IDs, actor details, action types, and sanitized reason strings.
"""

import logging
from typing import Any, Dict, Optional
import uuid

from sqlalchemy.orm import Session

from backend.models.audit_log import AuditLog

logger = logging.getLogger("ppd.services.audit")


class AuditService:
    """Service to record immutable clinical action and data access events."""

    @staticmethod
    def record_event(
        db: Session,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        actor_id: str,
        actor_role: str = "clinician",
        details: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
    ) -> AuditLog:
        """Create and commit an audit record."""
        sanitized_details = details or {}
        audit_record = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            actor_role=actor_role,
            details=sanitized_details,
            client_ip=client_ip,
        )
        db.add(audit_record)
        # Note: caller or request lifecycle commits the transaction
        logger.info(
            "Audit event recorded: action=%s, resource=%s:%s, actor=%s",
            action,
            resource_type,
            resource_id,
            actor_id,
        )
        return audit_record


audit_service = AuditService()

