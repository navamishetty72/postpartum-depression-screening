"""Business service layer for Mother patient management and persistence."""

import logging
from typing import List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.mother import Mother
from backend.schemas.mother import MotherCreate, MotherUpdate

logger = logging.getLogger("ppd.services.mother")


class MotherService:
    """Service providing CRUD and lifecycle logic for Mother entities.

    PRIVACY REQUIREMENT:
    Do not log sensitive medical history, free text clinical notes, or personal contact info.
    Log only safe entity lifecycle events with record UUIDs.
    """

    @staticmethod
    def create_mother(db: Session, data: MotherCreate) -> Mother:
        """Create and persist a new Mother record in the database."""
        mother = Mother(
            name=data.name,
            age=data.age,
            phone=data.phone,
            email=data.email,
            delivery_date=data.delivery_date,
            pregnancy_type=data.pregnancy_type,
            medical_history=data.medical_history,
            notes=data.notes,
        )
        db.add(mother)
        db.commit()
        db.refresh(mother)
        logger.info("Created new Mother record [id=%s]", mother.id)
        return mother

    @staticmethod
    def get_mother_by_id(db: Session, mother_id: uuid.UUID) -> Optional[Mother]:
        """Retrieve a Mother by its unique UUID."""
        return db.get(Mother, mother_id)

    @staticmethod
    def list_mothers(
        db: Session,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Mother]:
        """List Mother records with pagination, ordered by creation date descending."""
        stmt = (
            select(Mother)
            .order_by(desc(Mother.created_at))
            .offset(max(0, skip))
            .limit(min(max(1, limit), 200))
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def update_mother(
        db: Session,
        mother_id: uuid.UUID,
        data: MotherUpdate,
    ) -> Optional[Mother]:
        """Update fields on an existing Mother record. Returns None if record does not exist."""
        mother = db.get(Mother, mother_id)
        if not mother:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(mother, field, value)

        db.commit()
        db.refresh(mother)
        logger.info("Updated Mother record [id=%s]", mother.id)
        return mother


mother_service = MotherService()

