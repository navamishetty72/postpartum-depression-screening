"""Business service layer for Dashboard Metrics, Screening Activity, and Clinical Alerts."""

from datetime import date, datetime, timedelta, timezone
import logging
from typing import List
import uuid

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from backend.database.base import utc_now
from backend.models.care_plan import CarePlan
from backend.models.clinical_review import ClinicalReview
from backend.models.mother import Mother
from backend.models.screening import Screening
from backend.schemas.dashboard import (
    ActivityDataPoint,
    AlertItem,
    AlertSeverityEnum,
    DashboardAlertsResponse,
    DashboardMetricsResponse,
    DashboardTimeframeEnum,
    ScreeningActivityResponse,
)

logger = logging.getLogger("ppd.services.dashboard")


class DashboardService:
    """Service providing aggregated metrics, time-series activity, and urgent alerts."""

    @staticmethod
    def get_metrics(db: Session) -> DashboardMetricsResponse:
        """Calculate aggregated clinical metrics directly from database records."""
        # 1. Total registered mothers
        total_mothers = db.scalar(select(func.count(Mother.id))) or 0

        # 2. Total screenings recorded
        total_screenings = db.scalar(select(func.count(Screening.id))) or 0

        # 3. High-risk screenings (matches agreed risk classifications: 'high', 'severe', or uppercase equivalents)
        high_risk_condition = or_(
            func.lower(Screening.risk_classification) == "high",
            func.lower(Screening.risk_classification) == "severe",
        )
        high_risk_screenings = db.scalar(
            select(func.count(Screening.id)).where(high_risk_condition)
        ) or 0

        # 4. Pending clinical reviews
        pending_clinical_reviews = db.scalar(
            select(func.count(ClinicalReview.id)).where(
                func.lower(ClinicalReview.review_status) == "pending"
            )
        ) or 0

        # 5. Active care plans
        active_care_plans = db.scalar(
            select(func.count(CarePlan.id)).where(
                func.lower(CarePlan.status) == "active"
            )
        ) or 0

        return DashboardMetricsResponse(
            total_mothers=total_mothers,
            total_screenings=total_screenings,
            high_risk_screenings=high_risk_screenings,
            pending_clinical_reviews=pending_clinical_reviews,
            active_care_plans=active_care_plans,
        )

    @staticmethod
    def get_screening_activity(
        db: Session,
        timeframe: DashboardTimeframeEnum,
    ) -> ScreeningActivityResponse:
        """Aggregate screening activity over 4w, 8w, or 12w weekly intervals.

        Generates 7-day windows in chronological order, filling empty periods with 0.
        """
        weeks_map = {
            DashboardTimeframeEnum.four_weeks: 4,
            DashboardTimeframeEnum.eight_weeks: 8,
            DashboardTimeframeEnum.twelve_weeks: 12,
        }
        num_weeks = weeks_map[timeframe]

        now = utc_now()
        today = now.date()
        # Find Sunday/Monday start of current week, or measure backwards in exact 7-day blocks
        # We divide into num_weeks contiguous 7-day intervals:
        start_date = today - timedelta(days=num_weeks * 7)

        # Query all screenings within the timeframe
        stmt = (
            select(Screening.screening_date)
            .where(Screening.screening_date >= datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc))
        )
        dates = db.scalars(stmt).all()

        # Build contiguous intervals
        data_points: List[ActivityDataPoint] = []
        for w in range(num_weeks):
            period_start = start_date + timedelta(days=w * 7)
            period_end = period_start + timedelta(days=6)
            p_start_dt = datetime(period_start.year, period_start.month, period_start.day, 0, 0, 0, tzinfo=timezone.utc)
            p_end_dt = datetime(period_end.year, period_end.month, period_end.day, 23, 59, 59, tzinfo=timezone.utc)

            # Count screenings whose date falls in this window
            count = sum(1 for d in dates if d and (p_start_dt <= (d if d.tzinfo else d.replace(tzinfo=timezone.utc)) <= p_end_dt))
            data_points.append(
                ActivityDataPoint(
                    period_start=period_start,
                    period_end=period_end,
                    screening_count=count,
                )
            )

        return ScreeningActivityResponse(
            timeframe=timeframe,
            total_periods=len(data_points),
            data=data_points,
        )

    @staticmethod
    def get_alerts(db: Session) -> DashboardAlertsResponse:
        """Aggregate active clinical alerts across Q10 flags, high-risk screenings, and escalations.

        Privacy Rule:
        Descriptions must be concise and free of raw patient narratives, audio transcripts,
        or clinical impressions.
        """
        alerts: List[AlertItem] = []

        # 1. EPDS Q10 Safety Alerts (Critical severity)
        q10_stmt = (
            select(Screening, Mother)
            .join(Mother, Screening.mother_id == Mother.id)
            .where(Screening.q10_safety_alert.is_(True))
            .order_by(desc(Screening.screening_date))
        )
        q10_screenings = db.execute(q10_stmt).all()
        for screening, mother in q10_screenings:
            alerts.append(
                AlertItem(
                    alert_id=f"alert-q10-{screening.id}",
                    alert_type="EPDS_Q10_SAFETY",
                    severity=AlertSeverityEnum.critical,
                    mother_id=mother.id,
                    mother_name=mother.name,
                    screening_id=screening.id,
                    review_id=None,
                    timestamp=screening.screening_date,
                    description=f"EPDS Question 10 affirmative self-harm response recorded on {screening.screening_date.strftime('%Y-%m-%d')}.",
                )
            )

        # 2. High or Severe Risk Screenings WITHOUT Q10 (to prevent duplicate alerts for the same screening)
        high_risk_stmt = (
            select(Screening, Mother)
            .join(Mother, Screening.mother_id == Mother.id)
            .where(
                or_(
                    func.lower(Screening.risk_classification) == "high",
                    func.lower(Screening.risk_classification) == "severe",
                ),
                Screening.q10_safety_alert.is_(False),
            )
            .order_by(desc(Screening.screening_date))
        )
        hr_screenings = db.execute(high_risk_stmt).all()
        for screening, mother in hr_screenings:
            alerts.append(
                AlertItem(
                    alert_id=f"alert-hr-{screening.id}",
                    alert_type="HIGH_RISK_SCREENING",
                    severity=AlertSeverityEnum.high,
                    mother_id=mother.id,
                    mother_name=mother.name,
                    screening_id=screening.id,
                    review_id=None,
                    timestamp=screening.screening_date,
                    description=f"Screening assessed at {screening.risk_classification.upper()} risk with EPDS score {screening.total_score}.",
                )
            )

        # 3. Clinical Reviews Requiring Immediate Escalation
        escalation_stmt = (
            select(ClinicalReview, Mother)
            .join(Mother, ClinicalReview.mother_id == Mother.id)
            .where(ClinicalReview.required_immediate_escalation.is_(True))
            .order_by(desc(ClinicalReview.reviewed_at))
        )
        escalation_reviews = db.execute(escalation_stmt).all()
        for review, mother in escalation_reviews:
            alerts.append(
                AlertItem(
                    alert_id=f"alert-esc-{review.id}",
                    alert_type="IMMEDIATE_ESCALATION",
                    severity=AlertSeverityEnum.critical,
                    mother_id=mother.id,
                    mother_name=mother.name,
                    screening_id=review.screening_id,
                    review_id=review.id,
                    timestamp=review.reviewed_at,
                    description=f"Immediate clinical escalation designated by {review.clinician_name}.",
                )
            )

        # Sort all alerts newest first
        alerts.sort(key=lambda a: a.timestamp, reverse=True)

        return DashboardAlertsResponse(
            total_alerts=len(alerts),
            alerts=alerts,
        )


dashboard_service = DashboardService()

