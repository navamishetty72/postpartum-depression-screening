"""FastAPI Router for Screening Retrieval endpoints.

Exposes:
- GET /api/mothers/{mother_id}/screenings (screening history for a mother)
- GET /api/screenings/{screening_id} (retrieve individual screening by UUID)
"""

import logging
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.database.base import utc_now
from backend.database.connection import get_db
from backend.models.screening import Screening
from backend.schemas.handoff import ScreeningHandoffRequest, ScreeningHandoffResponse
from backend.schemas.screening import ScreeningPersistRequest, ScreeningResponse
from backend.services.audit_service import audit_service
from backend.services.screening_service import (
    MotherNotFoundError,
    ScreeningService,
    screening_service,
)


logger = logging.getLogger("ppd.routers.screenings")

router = APIRouter(tags=["Screenings"])


@router.post(
    "/api/screenings",
    response_model=ScreeningResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Persist a completed screening session and multimodal results",
)
def create_screening(
    payload: ScreeningPersistRequest,
    db: Session = Depends(get_db),
    service: ScreeningService = Depends(lambda: screening_service),
) -> ScreeningResponse:
    """Persist screening answers, EPDS score, risk tier, and multimodal predictions."""
    try:
        screening = service.persist_screening(db, payload)
        return ScreeningResponse.model_validate(screening)
    except MotherNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Failed to persist screening: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist screening session due to an internal server error.",
        ) from exc


@router.get(
    "/api/screenings",
    response_model=List[ScreeningResponse],
    status_code=status.HTTP_200_OK,
    summary="List all screenings across mothers",
)
def list_screenings(
    skip: int = Query(default=0, ge=0, description="Offset for pagination"),
    limit: int = Query(default=50, ge=1, le=200, description="Page limit"),
    db: Session = Depends(get_db),
    service: ScreeningService = Depends(lambda: screening_service),
) -> List[ScreeningResponse]:
    """Retrieve a paginated list of all screenings, ordered newest first."""
    screenings = service.list_screenings(db, skip=skip, limit=limit)
    return [ScreeningResponse.model_validate(s) for s in screenings]


@router.get(
    "/api/mothers/{mother_id}/screenings",
    response_model=List[ScreeningResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve screening history for a specific mother",
)
def get_mother_screenings(
    mother_id: uuid.UUID,
    db: Session = Depends(get_db),
    service: ScreeningService = Depends(lambda: screening_service),
) -> List[ScreeningResponse]:
    """Retrieve all screening records belonging to a mother, newest first."""
    screenings = service.get_screenings_by_mother_id(db, mother_id)
    if screenings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mother with ID '{mother_id}' was not found.",
        )
    return [ScreeningResponse.model_validate(s) for s in screenings]


@router.get(
    "/api/screenings/{screening_id}",
    response_model=ScreeningResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an individual screening by UUID",
)
def get_screening(
    screening_id: uuid.UUID,
    db: Session = Depends(get_db),
    service: ScreeningService = Depends(lambda: screening_service),
) -> ScreeningResponse:
    """Retrieve details and multimodal results of a single screening event."""
    screening = service.get_screening_by_id(db, screening_id)
    if not screening:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening with ID '{screening_id}' was not found.",
        )
    return ScreeningResponse.model_validate(screening)


@router.post(
    "/api/screenings/{screening_id}/handoff",
    response_model=ScreeningHandoffResponse,
    status_code=status.HTTP_200_OK,
    summary="Record clinical handoff event for a screening",
)
def handoff_screening(
    screening_id: uuid.UUID,
    payload: ScreeningHandoffRequest,
    request: Request,
    db: Session = Depends(get_db),
    service: ScreeningService = Depends(lambda: screening_service),
) -> ScreeningHandoffResponse:
    """Record clinical screening handoff in audit log while strictly preserving screening data.

    Guarantees:
    - Verifies the screening exists (404 if missing).
    - Preserves original screening scores, predictions, and EPDS Q10 safety alert.
    - Records an audit log event without storing raw clinical notes or patient narratives.
    - Makes no fraudulent claim of external emergency dispatch; returns RECORDED_IN_AUDIT_LOG.
    """
    screening = service.get_screening_by_id(db, screening_id)
    if not screening:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening with ID '{screening_id}' was not found.",
        )

    client_ip = request.client.host if request.client else None
    handoff_time = utc_now()

    # Record event in audit log (strictly sanitized, no patient narratives)
    audit_service.record_event(
        db=db,
        action="screening_handoff",
        resource_type="screening",
        resource_id=str(screening.id),
        actor_id=payload.clinician_id,
        actor_role="clinician",
        details={
            "mother_id": str(screening.mother_id),
            "destination": payload.destination,
            "urgency": payload.urgency,
            "q10_safety_alert": screening.q10_safety_alert,
            "risk_classification": screening.risk_classification,
        },
        client_ip=client_ip,
    )
    db.commit()

    return ScreeningHandoffResponse(
        screening_id=screening.id,
        mother_id=screening.mother_id,
        destination=payload.destination,
        urgency=payload.urgency,
        q10_safety_alert_preserved=screening.q10_safety_alert,
        handoff_recorded_at=handoff_time,
        status="RECORDED_IN_AUDIT_LOG",
    )


