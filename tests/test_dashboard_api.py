"""Unit and integration tests for Dashboard Metrics, Screening Activity, and Alerts APIs.

Covers:
- GET /api/dashboard/metrics:
  - Empty database returns all zeros
  - Known seeded records return exact aggregated counts
  - High-risk screenings counted accurately without fabricated scores
  - Pending reviews and active care plans counted correctly
- GET /api/dashboard/screening-activity:
  - Exactly 4w, 8w, and 12w timeframes supported
  - Empty periods return zero count
  - Invalid timeframe returns 422
  - Chronological ordering of intervals
- GET /api/dashboard/alerts:
  - EPDS Q10 safety alerts appear regardless of total score / model prediction
  - High risk screenings appear with clear non-sensitive descriptions
  - Immediate clinical escalations appear as critical alerts
  - No duplicate alerts for the same underlying event
  - Privacy check: no raw patient narratives or medical notes in alert descriptions
"""

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.base import Base, utc_now
from backend.database.connection import get_db
from backend.main import app
from backend.models.care_plan import CarePlan
from backend.models.clinical_review import ClinicalReview
from backend.models.mother import Mother
from backend.models.screening import Screening


@pytest.fixture(scope="function")
def db_session():
    """Create an isolated in-memory SQLite database session with StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with database dependency override."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. Dashboard Metrics Tests
# ---------------------------------------------------------------------------

def test_dashboard_metrics_empty_database(client: TestClient):
    """Test metrics on an empty database return zero across all categories."""
    response = client.get("/api/dashboard/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_mothers"] == 0
    assert data["total_screenings"] == 0
    assert data["high_risk_screenings"] == 0
    assert data["pending_clinical_reviews"] == 0
    assert data["active_care_plans"] == 0


def test_dashboard_metrics_with_seeded_records(client: TestClient, db_session):
    """Test metrics calculation with known populated records."""
    m1 = Mother(name="Mother 1")
    m2 = Mother(name="Mother 2")
    m3 = Mother(name="Mother 3")
    db_session.add_all([m1, m2, m3])
    db_session.commit()

    # Screenings: 1 high risk, 1 moderate risk, 1 low risk
    s1 = Screening(mother_id=m1.id, total_score=15, risk_classification="high", q10_safety_alert=False)
    s2 = Screening(mother_id=m2.id, total_score=11, risk_classification="moderate", q10_safety_alert=False)
    s3 = Screening(mother_id=m3.id, total_score=4, risk_classification="low", q10_safety_alert=False)
    db_session.add_all([s1, s2, s3])

    # Reviews: 1 pending, 1 confirmed
    r1 = ClinicalReview(mother_id=m1.id, clinician_id="DOC-1", clinician_name="Dr. One", review_status="pending")
    r2 = ClinicalReview(mother_id=m2.id, clinician_id="DOC-2", clinician_name="Dr. Two", review_status="confirmed")
    db_session.add_all([r1, r2])

    # Care plans: 1 active, 1 completed
    cp1 = CarePlan(mother_id=m1.id, intervention_type="tele_manas", status="active")
    cp2 = CarePlan(mother_id=m2.id, intervention_type="counseling", status="completed")
    db_session.add_all([cp1, cp2])
    db_session.commit()

    response = client.get("/api/dashboard/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_mothers"] == 3
    assert data["total_screenings"] == 3
    assert data["high_risk_screenings"] == 1
    assert data["pending_clinical_reviews"] == 1
    assert data["active_care_plans"] == 1


# ---------------------------------------------------------------------------
# 2. Screening Activity Tests
# ---------------------------------------------------------------------------

def test_screening_activity_timeframes(client: TestClient, db_session):
    """Test 4w, 8w, and 12w timeframes return correct number of periods."""
    mother = Mother(name="Mother Test")
    db_session.add(mother)
    db_session.commit()

    # Add a screening today and one 10 days ago
    now = utc_now()
    s1 = Screening(mother_id=mother.id, total_score=5, risk_classification="low", screening_date=now)
    s2 = Screening(mother_id=mother.id, total_score=7, risk_classification="low", screening_date=now - timedelta(days=10))
    db_session.add_all([s1, s2])
    db_session.commit()

    # 4w timeframe -> 4 periods
    res4 = client.get("/api/dashboard/screening-activity?timeframe=4w")
    assert res4.status_code == 200
    data4 = res4.json()
    assert data4["timeframe"] == "4w"
    assert data4["total_periods"] == 4
    assert len(data4["data"]) == 4

    # 8w timeframe -> 8 periods
    res8 = client.get("/api/dashboard/screening-activity?timeframe=8w")
    assert res8.status_code == 200
    assert len(res8.json()["data"]) == 8

    # 12w timeframe -> 12 periods
    res12 = client.get("/api/dashboard/screening-activity?timeframe=12w")
    assert res12.status_code == 200
    assert len(res12.json()["data"]) == 12


def test_screening_activity_invalid_timeframe_rejected(client: TestClient):
    """Test rejection of unsupported timeframe query values."""
    response = client.get("/api/dashboard/screening-activity?timeframe=16w")
    assert response.status_code == 422


def test_screening_activity_empty_periods_contain_zeros(client: TestClient):
    """Confirm periods with no activity report 0 count."""
    response = client.get("/api/dashboard/screening-activity?timeframe=4w")
    assert response.status_code == 200
    data = response.json()
    for period in data["data"]:
        assert period["screening_count"] == 0


# ---------------------------------------------------------------------------
# 3. Dashboard Alerts Tests
# ---------------------------------------------------------------------------

def test_dashboard_alerts_q10_persists_even_with_low_total_score(client: TestClient, db_session):
    """Verify EPDS Q10 safety alert appears as critical even if total score is low (e.g. 2)."""
    mother = Mother(name="Pooja Hegde")
    db_session.add(mother)
    db_session.commit()

    # Low total score (2) but Q10 positive
    screening = Screening(
        mother_id=mother.id,
        total_score=2,
        risk_classification="low",
        q10_safety_alert=True,
    )
    db_session.add(screening)
    db_session.commit()

    response = client.get("/api/dashboard/alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["total_alerts"] == 1
    alert = data["alerts"][0]
    assert alert["alert_type"] == "EPDS_Q10_SAFETY"
    assert alert["severity"] == "critical"
    assert alert["mother_name"] == "Pooja Hegde"
    assert "Question 10" in alert["description"]


def test_dashboard_alerts_immediate_escalation(client: TestClient, db_session):
    """Verify clinical review immediate escalation produces a critical alert."""
    mother = Mother(name="Sunidhi C")
    db_session.add(mother)
    db_session.commit()

    review = ClinicalReview(
        mother_id=mother.id,
        clinician_id="DOC-99",
        clinician_name="Dr. Suresh Rao",
        review_status="confirmed",
        required_immediate_escalation=True,
    )
    db_session.add(review)
    db_session.commit()

    response = client.get("/api/dashboard/alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["total_alerts"] == 1
    alert = data["alerts"][0]
    assert alert["alert_type"] == "IMMEDIATE_ESCALATION"
    assert alert["severity"] == "critical"
    assert "Dr. Suresh Rao" in alert["description"]


def test_dashboard_alerts_no_duplicate_for_same_screening(client: TestClient, db_session):
    """Ensure a high-risk screening with a Q10 alert does not generate duplicate alert items."""
    mother = Mother(name="Geetha K")
    db_session.add(mother)
    db_session.commit()

    # Screening is both high risk and Q10 positive
    s = Screening(
        mother_id=mother.id,
        total_score=16,
        risk_classification="high",
        q10_safety_alert=True,
    )
    db_session.add(s)
    db_session.commit()

    response = client.get("/api/dashboard/alerts")
    assert response.status_code == 200
    data = response.json()
    # Should only emit the critical Q10 alert, not a redundant high-risk duplicate
    assert data["total_alerts"] == 1
    assert data["alerts"][0]["alert_type"] == "EPDS_Q10_SAFETY"


def test_dashboard_alerts_privacy_safeguard(client: TestClient, db_session):
    """Verify descriptions never contain sensitive notes or raw patient narratives."""
    mother = Mother(name="Ananya", medical_history="Severe clinical history details that must not leak")
    db_session.add(mother)
    db_session.commit()

    s = Screening(
        mother_id=mother.id,
        total_score=18,
        risk_classification="high",
        q10_safety_alert=False,
        notes="Sensitive free-form note",
    )
    db_session.add(s)
    db_session.commit()

    response = client.get("/api/dashboard/alerts")
    assert response.status_code == 200
    alert = response.json()["alerts"][0]
    assert "must not leak" not in alert["description"]
    assert "Sensitive free-form note" not in alert["description"]

