"""Service layer for clinician-managed Care Plans."""

import logging
from typing import Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.care_plan import CarePlan
from backend.models.mother import Mother
from backend.models.screening import Screening
from backend.schemas.care_plan import CarePlanUpsertRequest
from backend.services.audit_service import audit_service

logger = logging.getLogger("ppd.services.care_plan")


class CarePlanError(Exception):
    """Base error for care plan operations."""
    pass


class CarePlanValidationError(CarePlanError):
    """Raised when care plan validation fails."""
    pass


class CarePlanService:
    """Service providing business logic and persistence for Care Plans."""

    @staticmethod
    def get_care_plan_by_mother_id(
        db: Session,
        mother_id: uuid.UUID,
    ) -> Optional[CarePlan]:
        """Retrieve the most recent care plan for a mother."""
        stmt = (
            select(CarePlan)
            .where(CarePlan.mother_id == mother_id)
            .order_by(desc(CarePlan.created_at))
        )
        return db.scalars(stmt).first()

    @staticmethod
    def upsert_care_plan(
        db: Session,
        mother_id: uuid.UUID,
        data: CarePlanUpsertRequest,
        client_ip: Optional[str] = None,
    ) -> CarePlan:
        """Create or update a care plan for a mother.

        If a care plan already exists, updates its fields. If not, creates a new one.
        Validates:
        - Mother must exist (raises CarePlanValidationError).
        - If screening_id is provided, must exist and belong to the mother.
        - Records an audit log event without storing raw clinical notes.
        """
        # 1. Verify mother exists
        mother = db.get(Mother, mother_id)
        if not mother:
            raise CarePlanValidationError(f"Mother with ID '{mother_id}' does not exist.")

        # 2. Verify screening if supplied
        if data.screening_id:
            screening = db.get(Screening, data.screening_id)
            if not screening:
                raise CarePlanValidationError(f"Screening with ID '{data.screening_id}' does not exist.")
            if screening.mother_id != mother_id:
                raise CarePlanValidationError(
                    f"Screening '{data.screening_id}' does not belong to Mother '{mother_id}'."
                )

        existing_plan = CarePlanService.get_care_plan_by_mother_id(db, mother_id)
        action_name = "update_care_plan" if existing_plan else "create_care_plan"

        try:
            if existing_plan:
                # Update existing plan
                existing_plan.screening_id = data.screening_id
                existing_plan.priority = data.priority.value
                existing_plan.intervention_type = data.intervention_type.value
                existing_plan.referral_destination = data.referral_destination
                existing_plan.scheduled_followup_date = data.scheduled_followup_date
                existing_plan.assigned_clinician_id = data.assigned_clinician_id
                existing_plan.status = data.status.value
                existing_plan.notes = data.notes
                plan = existing_plan
            else:
                # Create new plan
                plan = CarePlan(
                    mother_id=mother_id,
                    screening_id=data.screening_id,
                    priority=data.priority.value,
                    intervention_type=data.intervention_type.value,
                    referral_destination=data.referral_destination,
                    scheduled_followup_date=data.scheduled_followup_date,
                    assigned_clinician_id=data.assigned_clinician_id,
                    status=data.status.value,
                    notes=data.notes,
                )
                db.add(plan)

            db.flush()

            # Record audit event (sanitized, no clinical notes)
            audit_service.record_event(
                db=db,
                action=action_name,
                resource_type="care_plan",
                resource_id=str(plan.id),
                actor_id=data.assigned_clinician_id or "clinician",
                actor_role="clinician",
                details={
                    "mother_id": str(mother_id),
                    "priority": data.priority.value,
                    "intervention_type": data.intervention_type.value,
                    "status": data.status.value,
                    "referral_destination": data.referral_destination,
                },
                client_ip=client_ip,
            )

            db.commit()
            db.refresh(plan)
            logger.info("CarePlan [%s] successfully processed for Mother [%s]", plan.id, mother_id)
            return plan
        except Exception as exc:
            db.rollback()
            logger.error("Failed to upsert CarePlan: %s", type(exc).__name__)
            raise CarePlanError(f"Database error during care plan operation: {exc}") from exc


care_plan_service = CarePlanService()

