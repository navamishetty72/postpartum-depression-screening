"""FastAPI Router for Mother Management endpoints.

Exposes:
- POST /api/mothers
- GET /api/mothers
- GET /api/mothers/{mother_id}
- PUT /api/mothers/{mother_id}
"""

import logging
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.mother import MotherCreate, MotherResponse, MotherUpdate
from backend.services.mother_service import MotherService, mother_service

logger = logging.getLogger("ppd.routers.mothers")

router = APIRouter(prefix="/api/mothers", tags=["Mother Management"])


@router.post(
    "",
    response_model=MotherResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Mother",
)
def create_mother(
    payload: MotherCreate,
    db: Session = Depends(get_db),
    service: MotherService = Depends(lambda: mother_service),
) -> MotherResponse:
    """Register a new postpartum mother in the screening platform."""
    try:
        mother = service.create_mother(db, payload)
        return MotherResponse.model_validate(mother)
    except Exception as exc:
        logger.error("Failed to create mother: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register mother due to an internal server error.",
        ) from exc


@router.get(
    "",
    response_model=List[MotherResponse],
    status_code=status.HTTP_200_OK,
    summary="List registered Mothers",
)
def list_mothers(
    skip: int = Query(default=0, ge=0, description="Offset for pagination"),
    limit: int = Query(default=50, ge=1, le=200, description="Page limit"),
    db: Session = Depends(get_db),
    service: MotherService = Depends(lambda: mother_service),
) -> List[MotherResponse]:
    """Retrieve a paginated list of registered mothers."""
    mothers = service.list_mothers(db, skip=skip, limit=limit)
    return [MotherResponse.model_validate(m) for m in mothers]


@router.get(
    "/{mother_id}",
    response_model=MotherResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a Mother by UUID",
)
def get_mother(
    mother_id: uuid.UUID,
    db: Session = Depends(get_db),
    service: MotherService = Depends(lambda: mother_service),
) -> MotherResponse:
    """Retrieve details of a mother by UUID."""
    mother = service.get_mother_by_id(db, mother_id)
    if not mother:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mother with ID '{mother_id}' was not found.",
        )
    return MotherResponse.model_validate(mother)


@router.put(
    "/{mother_id}",
    response_model=MotherResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a Mother record",
)
def update_mother(
    mother_id: uuid.UUID,
    payload: MotherUpdate,
    db: Session = Depends(get_db),
    service: MotherService = Depends(lambda: mother_service),
) -> MotherResponse:
    """Update profile attributes of an existing mother."""
    updated = service.update_mother(db, mother_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mother with ID '{mother_id}' was not found.",
        )
    return MotherResponse.model_validate(updated)

