"""FastAPI Router for Care Plan management endpoints.

Exposes:
- GET /api/mothers/{mother_id}/care-plan
- PUT /api/mothers/{mother_id}/care-plan
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.models.mother import Mother
from backend.schemas.care_plan import CarePlanResponse, CarePlanUpsertRequest
from backend.services.care_plan_service import (
    CarePlanService,
    CarePlanValidationError,
    care_plan_service,
)

logger = logging.getLogger("ppd.routers.care_plans")

router = APIRouter(tags=["Care Plans"])


@router.get(
    "/api/mothers/{mother_id}/care-plan",
    response_model=CarePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current care plan for a mother",
)
def get_care_plan(
    mother_id: uuid.UUID,
    db: Session = Depends(get_db),
    service: CarePlanService = Depends(lambda: care_plan_service),
) -> CarePlanResponse:
    """Retrieve the active or most recent care plan for a specific mother."""
    mother = db.get(Mother, mother_id)
    if not mother:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mother with ID '{mother_id}' was not found.",
        )

    plan = service.get_care_plan_by_mother_id(db, mother_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No care plan has been formulated for Mother '{mother_id}'.",
        )
    return CarePlanResponse.model_validate(plan)


@router.put(
    "/api/mothers/{mother_id}/care-plan",
    response_model=CarePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update care plan for a mother",
)
def upsert_care_plan(
    mother_id: uuid.UUID,
    payload: CarePlanUpsertRequest,
    request: Request,
    db: Session = Depends(get_db),
    service: CarePlanService = Depends(lambda: care_plan_service),
) -> CarePlanResponse:
    """Create or update a mother's care plan (upsert semantics).

    Contract Note:
    If a care plan does not yet exist for the mother, this endpoint creates one.
    If a plan already exists, it updates it. Returns 404 only if the Mother does not exist.
    """
    client_ip = request.client.host if request.client else None
    try:
        plan = service.upsert_care_plan(db, mother_id, payload, client_ip=client_ip)
        return CarePlanResponse.model_validate(plan)
    except CarePlanValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not exist" in str(exc) else status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Internal error during care plan upsert: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update care plan.",
        ) from exc

