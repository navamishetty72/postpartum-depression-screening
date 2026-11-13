"""FastAPI Router for Dashboard endpoints.

Exposes:
- GET /api/dashboard/metrics
- GET /api/dashboard/screening-activity?timeframe=4w
- GET /api/dashboard/alerts
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.dashboard import (
    DashboardAlertsResponse,
    DashboardMetricsResponse,
    DashboardTimeframeEnum,
    ScreeningActivityResponse,
)
from backend.services.dashboard_service import DashboardService, dashboard_service

logger = logging.getLogger("ppd.routers.dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get(
    "/metrics",
    response_model=DashboardMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve platform clinical summary metrics",
)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    service: DashboardService = Depends(lambda: dashboard_service),
) -> DashboardMetricsResponse:
    """Retrieve aggregate counts for registered mothers, total screenings, high risk screenings,

    pending clinical reviews, and active care plans.
    """
    try:
        return service.get_metrics(db)
    except Exception as exc:
        logger.error("Failed to compute dashboard metrics: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard metrics.",
        ) from exc


@router.get(
    "/screening-activity",
    response_model=ScreeningActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve weekly screening activity time-series",
)
def get_screening_activity(
    timeframe: DashboardTimeframeEnum = Query(
        default=DashboardTimeframeEnum.four_weeks,
        description="Timeframe window. Supported values: '4w', '8w', '12w'",
    ),
    db: Session = Depends(get_db),
    service: DashboardService = Depends(lambda: dashboard_service),
) -> ScreeningActivityResponse:
    """Retrieve chronological weekly screening counts over 4w, 8w, or 12w windows."""
    try:
        return service.get_screening_activity(db, timeframe=timeframe)
    except Exception as exc:
        logger.error("Failed to generate screening activity: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve screening activity.",
        ) from exc


@router.get(
    "/alerts",
    response_model=DashboardAlertsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve active urgent clinical alerts",
)
def get_dashboard_alerts(
    db: Session = Depends(get_db),
    service: DashboardService = Depends(lambda: dashboard_service),
) -> DashboardAlertsResponse:
    """Retrieve urgent alerts (EPDS Q10 safety triggers, high-risk screenings, immediate escalations).

    Ordered chronologically newest first with concise, privacy-safe descriptions.
    """
    try:
        return service.get_alerts(db)
    except Exception as exc:
        logger.error("Failed to retrieve dashboard alerts: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard alerts.",
        ) from exc

