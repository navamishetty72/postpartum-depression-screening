"""Pydantic schemas for Dashboard Metrics, Screening Activity, and Alerts."""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class DashboardTimeframeEnum(str, Enum):
    """Supported screening activity timeframes."""
    four_weeks = "4w"
    eight_weeks = "8w"
    twelve_weeks = "12w"


class DashboardMetricsResponse(BaseModel):
    """Aggregated clinical metrics across the platform."""

    total_mothers: int = Field(..., description="Total count of enrolled mothers")
    total_screenings: int = Field(..., description="Total count of completed screenings")
    high_risk_screenings: int = Field(
        ...,
        description="Count of screenings with high or severe risk classification",
    )
    pending_clinical_reviews: int = Field(
        ...,
        description="Count of clinical reviews awaiting clinician evaluation",
    )
    active_care_plans: int = Field(
        ...,
        description="Count of active intervention care plans",
    )


class ActivityDataPoint(BaseModel):
    """Single period time-series screening count."""

    period_start: date = Field(..., description="Start date of the interval (UTC)")
    period_end: date = Field(..., description="End date of the interval (UTC)")
    screening_count: int = Field(..., description="Total screenings conducted in this window")


class ScreeningActivityResponse(BaseModel):
    """Time-series activity aggregation."""

    timeframe: DashboardTimeframeEnum
    total_periods: int
    data: List[ActivityDataPoint]


class AlertSeverityEnum(str, Enum):
    """Alert severity tier."""
    critical = "critical"
    high = "high"
    warning = "warning"
    info = "info"


class AlertItem(BaseModel):
    """Structured clinical alert."""

    alert_id: str = Field(..., description="Stable or composite alert identifier")
    alert_type: str = Field(
        ...,
        description="Category of alert: 'EPDS_Q10_SAFETY', 'HIGH_RISK_SCREENING', 'IMMEDIATE_ESCALATION'",
    )
    severity: AlertSeverityEnum
    mother_id: uuid.UUID = Field(..., description="UUID of the mother")
    mother_name: str = Field(..., description="Name of the mother")
    screening_id: Optional[uuid.UUID] = Field(default=None, description="Associated screening UUID, if applicable")
    review_id: Optional[uuid.UUID] = Field(default=None, description="Associated clinical review UUID, if applicable")
    timestamp: datetime = Field(..., description="Timestamp of the trigger event (UTC)")
    description: str = Field(
        ...,
        description="Concise, non-sensitive description. Never contains raw patient narratives or clinical notes.",
    )


class DashboardAlertsResponse(BaseModel):
    """Container for active clinical alerts."""

    total_alerts: int
    alerts: List[AlertItem]

