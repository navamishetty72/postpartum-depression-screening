"""FastAPI Router for Clinical Review endpoints.

Exposes:
- POST /api/clinical-reviews
- GET /api/mothers/{mother_id}/clinical-reviews
"""

import logging
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.clinical_review import ClinicalReviewCreate, ClinicalReviewResponse
from backend.services.clinical_review_service import (
    ClinicalReviewService,
    ReviewValidationError,
    clinical_review_service,
)

logger = logging.getLogger("ppd.routers.clinical_reviews")

router = APIRouter(tags=["Clinical Reviews"])


@router.post(
    "/api/clinical-reviews",
    response_model=ClinicalReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a clinician-managed clinical review",
)
def create_clinical_review(
    payload: ClinicalReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    service: ClinicalReviewService = Depends(lambda: clinical_review_service),
) -> ClinicalReviewResponse:
    """Create and persist a new clinical review for a mother/screening."""
    client_ip = request.client.host if request.client else None
    try:
        review = service.create_review(db, payload, client_ip=client_ip)
        return ClinicalReviewResponse.model_validate(review)
    except ReviewValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not exist" in str(exc) else status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Internal error during review creation: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record clinical review.",
        ) from exc


@router.get(
    "/api/mothers/{mother_id}/clinical-reviews",
    response_model=List[ClinicalReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve clinical reviews for a mother",
)
def get_mother_clinical_reviews(
    mother_id: uuid.UUID,
    db: Session = Depends(get_db),
    service: ClinicalReviewService = Depends(lambda: clinical_review_service),
) -> List[ClinicalReviewResponse]:
    """Retrieve all clinical reviews conducted for a specific mother, newest first."""
    reviews = service.get_reviews_by_mother_id(db, mother_id)
    if reviews is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mother with ID '{mother_id}' was not found.",
        )
    return [ClinicalReviewResponse.model_validate(r) for r in reviews]


@router.get(
    "/api/clinical-reviews",
    response_model=List[ClinicalReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="List all clinical reviews across mothers",
)
def list_clinical_reviews(
    skip: int = Query(default=0, ge=0, description="Offset for pagination"),
    limit: int = Query(default=50, ge=1, le=200, description="Page limit"),
    db: Session = Depends(get_db),
    service: ClinicalReviewService = Depends(lambda: clinical_review_service),
) -> List[ClinicalReviewResponse]:
    """Retrieve all clinical reviews, ordered newest first."""
    reviews = service.list_reviews(db, skip=skip, limit=limit)
    return [ClinicalReviewResponse.model_validate(r) for r in reviews]


@router.get(
    "/api/clinical-reviews/{review_id}",
    response_model=ClinicalReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an individual clinical review by UUID",
)
def get_clinical_review(
    review_id: uuid.UUID,
    db: Session = Depends(get_db),
    service: ClinicalReviewService = Depends(lambda: clinical_review_service),
) -> ClinicalReviewResponse:
    """Retrieve details of a single clinical review event."""
    review = service.get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical review with ID '{review_id}' was not found.",
        )
    return ClinicalReviewResponse.model_validate(review)

