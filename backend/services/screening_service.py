"""Screening persistence and retrieval service for MIORA clinical backend.

Member 1 owns multimodal analysis; Member 2 owns storing and retrieving its results.
This service provides a transactional persistence function that Member 1 can call
after `/api/screenings/analyze` completes.
"""

import logging
from typing import List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.mother import Mother
from backend.models.screening import Screening
from backend.schemas.screening import ScreeningPersistRequest

logger = logging.getLogger("ppd.services.screening")


class ScreeningPersistenceError(Exception):
    """Raised when screening persistence fails (e.g. invalid foreign key or transaction error)."""
    pass


class MotherNotFoundError(ScreeningPersistenceError):
    """Raised when the referenced mother does not exist."""
    pass


class ScreeningService:
    """Service providing transactional persistence and retrieval for screening records."""

    @staticmethod
    def persist_screening(
        db: Session,
        data: ScreeningPersistRequest,
    ) -> Screening:
        """Persist a completed screening session and multimodal prediction results.

        Guarantees:
        - Verifies that the referenced Mother exists; raises MotherNotFoundError if missing.
        - Persists screening_status, modality_status, and fusion_status strictly according to contract.
        - Stores model_metadata and multimodal_scores only when explicitly supplied.
        - Strictly preserves the EPDS Q10 safety alert.
        - Never fabricates or calculates combined risk scores. Missing modalities remain missing.
        - Executes within a database transaction; safely rolls back on any failure.
        """
        # 1. Verify mother existence
        mother = db.get(Mother, data.mother_id)
        if not mother:
            logger.warning("Screening persistence rejected: Mother [id=%s] not found", data.mother_id)
            raise MotherNotFoundError(f"Mother with ID '{data.mother_id}' does not exist.")

        # 2. Extract and format status dictionaries cleanly
        modality_status_dict = {
            mod: (val.value if hasattr(val, "value") else str(val))
            for mod, val in data.modality_status.items()
        }

        # Model metadata & multimodal scores: store only what Member 1 supplied, else empty dict
        stored_metadata = data.model_metadata if data.model_metadata is not None else {}
        stored_multimodal = data.multimodal_scores if data.multimodal_scores is not None else {}

        screening = Screening(
            mother_id=data.mother_id,
            instrument=data.instrument,
            total_score=data.total_score,
            risk_classification=data.risk_classification,
            q10_safety_alert=data.q10_safety_alert,
            submitted_answers=data.submitted_answers,
            item_scores=data.item_scores,
            screening_status=(
                data.screening_status.value
                if hasattr(data.screening_status, "value")
                else str(data.screening_status)
            ),
            fusion_status=(
                data.fusion_status.value
                if hasattr(data.fusion_status, "value")
                else str(data.fusion_status)
            ),
            modality_status=modality_status_dict,
            model_metadata=stored_metadata,
            multimodal_scores=stored_multimodal,
            notes=data.notes,
        )

        try:
            db.add(screening)
            db.commit()
            db.refresh(screening)
            logger.info(
                "Persisted screening [id=%s] for Mother [id=%s] with status=%s, q10_alert=%s",
                screening.id,
                screening.mother_id,
                screening.screening_status,
                screening.q10_safety_alert,
            )
            return screening
        except Exception as exc:
            db.rollback()
            logger.error(
                "Failed to persist screening for Mother [id=%s]: %s",
                data.mother_id,
                type(exc).__name__,
            )
            raise ScreeningPersistenceError(f"Database error during screening persistence: {exc}") from exc

    @staticmethod
    def get_screening_by_id(
        db: Session,
        screening_id: uuid.UUID,
    ) -> Optional[Screening]:
        """Retrieve an individual screening record by UUID."""
        return db.get(Screening, screening_id)

    @staticmethod
    def get_screenings_by_mother_id(
        db: Session,
        mother_id: uuid.UUID,
    ) -> Optional[List[Screening]]:
        """Retrieve all screenings for a specific mother, newest first.

        Returns None if the Mother does not exist.
        """
        mother = db.get(Mother, mother_id)
        if not mother:
            return None

        stmt = (
            select(Screening)
            .where(Screening.mother_id == mother_id)
            .order_by(desc(Screening.screening_date), desc(Screening.created_at))
        )
        return list(db.scalars(stmt).all())


screening_service = ScreeningService()

