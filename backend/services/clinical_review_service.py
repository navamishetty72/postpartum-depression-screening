"""Service layer for clinician-managed Clinical Reviews."""

import logging
from typing import List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.clinical_review import ClinicalReview
from backend.models.mother import Mother
from backend.models.screening import Screening
from backend.schemas.clinical_review import ClinicalReviewCreate
from backend.services.audit_service import audit_service

logger = logging.getLogger("ppd.services.clinical_review")


class ClinicalReviewError(Exception):
    """Base error for clinical review operations."""
    pass


class ReviewValidationError(ClinicalReviewError):
    """Raised when clinical review validation fails."""
    pass


class ClinicalReviewService:
    """Service providing business logic and validation for Clinical Reviews."""

    @staticmethod
    def create_review(
        db: Session,
        data: ClinicalReviewCreate,
        client_ip: Optional[str] = None,
    ) -> ClinicalReview:
        """Create a clinician-managed clinical review.

        Rules:
        - Mother must exist.
        - If screening_id is supplied, the screening must exist and must belong to the mother.
        - Clinician review does NOT erase or suppress an EPDS Q10 safety alert.
        - Records audit log event without storing raw clinical notes.
        """
        # 1. Verify mother exists
        mother = db.get(Mother, data.mother_id)
        if not mother:
            raise ReviewValidationError(f"Mother with ID '{data.mother_id}' does not exist.")

        # 2. Verify screening if supplied
        screening: Optional[Screening] = None
        if data.screening_id:
            screening = db.get(Screening, data.screening_id)
            if not screening:
                raise ReviewValidationError(f"Screening with ID '{data.screening_id}' does not exist.")
            if screening.mother_id != data.mother_id:
                raise ReviewValidationError(
                    f"Screening '{data.screening_id}' does not belong to Mother '{data.mother_id}'."
                )

        review = ClinicalReview(
            mother_id=data.mother_id,
            screening_id=data.screening_id,
            clinician_id=data.clinician_id,
            clinician_name=data.clinician_name,
            review_status=data.review_status.value,
            final_risk_classification=data.final_risk_classification,
            clinical_notes=data.clinical_notes,
            required_immediate_escalation=data.required_immediate_escalation,
        )

        try:
            db.add(review)
            db.flush()

            # Record audit event (sanitized, no raw clinical notes)
            audit_service.record_event(
                db=db,
                action="create_clinical_review",
                resource_type="clinical_review",
                resource_id=str(review.id),
                actor_id=data.clinician_id,
                actor_role="clinician",
                details={
                    "mother_id": str(data.mother_id),
                    "screening_id": str(data.screening_id) if data.screening_id else None,
                    "review_status": data.review_status.value,
                    "final_risk_classification": data.final_risk_classification,
                    "required_immediate_escalation": data.required_immediate_escalation,
                },
                client_ip=client_ip,
            )

            db.commit()
            db.refresh(review)
            logger.info("Created ClinicalReview [id=%s] by clinician [%s]", review.id, data.clinician_id)
            return review
        except Exception as exc:
            db.rollback()
            logger.error("Failed to persist ClinicalReview: %s", type(exc).__name__)
            raise ClinicalReviewError(f"Database error during review creation: {exc}") from exc

    @staticmethod
    def get_reviews_by_mother_id(
        db: Session,
        mother_id: uuid.UUID,
    ) -> Optional[List[ClinicalReview]]:
        """Retrieve all reviews for a mother, newest first. Returns None if mother not found."""
        mother = db.get(Mother, mother_id)
        if not mother:
            return None

        stmt = (
            select(ClinicalReview)
            .where(ClinicalReview.mother_id == mother_id)
            .order_by(desc(ClinicalReview.reviewed_at), desc(ClinicalReview.created_at))
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def list_reviews(
        db: Session,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ClinicalReview]:
        """Retrieve all clinical reviews across all mothers, newest first."""
        stmt = (
            select(ClinicalReview)
            .order_by(desc(ClinicalReview.reviewed_at), desc(ClinicalReview.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_review_by_id(
        db: Session,
        review_id: uuid.UUID,
    ) -> Optional[ClinicalReview]:
        """Retrieve an individual clinical review by UUID."""
        return db.get(ClinicalReview, review_id)


clinical_review_service = ClinicalReviewService()

