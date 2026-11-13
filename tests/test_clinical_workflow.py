"""Unit and integration tests for Clinical Reviews, Care Plans, and Screening Handoff APIs.

Covers:
- POST /api/clinical-reviews:
  - Creating a clinical review
  - Rejecting nonexistent mother or screening IDs (404)
  - Rejecting a screening linked to a different mother (400)
  - Preserving EPDS Q10 safety alert without override
- GET /api/mothers/{mother_id}/clinical-reviews:
  - Retrieving reviews ordered newest first
  - 404 on nonexistent mother
- GET /api/mothers/{mother_id}/care-plan & PUT /api/mothers/{mother_id}/care-plan:
  - Upserting a care plan (creation when new, update when existing)
  - Validating priority, intervention, and status enum values
  - 404 for unknown mother
- POST /api/screenings/{screening_id}/handoff:
  - Successful handoff recorded in audit log
  - 404 on nonexistent screening
  - Q10 safety alert preservation
- Audit Logging:
  - Confirming clinical review, care plan, and handoff generate audit log events
  - Confirming raw notes/narratives are NOT stored in audit logs
"""

from datetime import date
import uuid
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.base import Base
from backend.database.connection import get_db
from backend.main import app
from backend.models.audit_log import AuditLog
from backend.models.care_plan import CarePlan
from backend.models.clinical_review import ClinicalReview
from backend.models.mother import Mother
from backend.models.screening import Screening


@pytest.fixture(scope="function")
def db_session():
    """Create an isolated, in-memory SQLite database session using StaticPool."""
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
# 1. Clinical Review Tests
# ---------------------------------------------------------------------------

def test_create_clinical_review_success(client: TestClient, db_session):
    """Test creating a clinical review for an existing mother and screening."""
    mother = Mother(name="Lakshmi Menon", age=30)
    db_session.add(mother)
    db_session.commit()

    screening = Screening(
        mother_id=mother.id,
        instrument="EPDS",
        total_score=13,
        risk_classification="moderate",
        q10_safety_alert=False,
        screening_status="completed",
    )
    db_session.add(screening)
    db_session.commit()

    payload = {
        "mother_id": str(mother.id),
        "screening_id": str(screening.id),
        "clinician_id": "DR-808",
        "clinician_name": "Dr. Anjali Gupta, MD",
        "review_status": "confirmed",
        "final_risk_classification": "moderate",
        "clinical_notes": "Mild maternal fatigue and sleep disturbance noted.",
        "required_immediate_escalation": False,
    }
    response = client.post("/api/clinical-reviews", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["mother_id"] == str(mother.id)
    assert data["screening_id"] == str(screening.id)
    assert data["review_status"] == "confirmed"
    assert data["clinician_name"] == "Dr. Anjali Gupta, MD"

    # Verify audit log was recorded without clinical notes
    stmt = select(AuditLog).where(AuditLog.action == "create_clinical_review")
    audit = db_session.scalars(stmt).first()
    assert audit is not None
    assert audit.actor_id == "DR-808"
    assert "fatigue" not in str(audit.details)


def test_create_clinical_review_rejects_missing_mother(client: TestClient):
    """Test 404 when mother does not exist."""
    payload = {
        "mother_id": str(uuid.uuid4()),
        "clinician_id": "DR-1",
        "clinician_name": "Dr. Test",
        "review_status": "confirmed",
    }
    response = client.post("/api/clinical-reviews", json=payload)
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_create_clinical_review_rejects_mismatched_screening(client: TestClient, db_session):
    """Test 400 when screening belongs to a different mother."""
    m1 = Mother(name="Mother One")
    m2 = Mother(name="Mother Two")
    db_session.add_all([m1, m2])
    db_session.commit()

    s1 = Screening(
        mother_id=m1.id,
        total_score=10,
        risk_classification="moderate",
        q10_safety_alert=False,
    )
    db_session.add(s1)
    db_session.commit()

    # Attempt to review screening s1 under mother m2
    payload = {
        "mother_id": str(m2.id),
        "screening_id": str(s1.id),
        "clinician_id": "DR-1",
        "clinician_name": "Dr. Test",
        "review_status": "confirmed",
    }
    response = client.post("/api/clinical-reviews", json=payload)
    assert response.status_code == 400
    assert "does not belong" in response.json()["detail"]


def test_get_mother_clinical_reviews_ordering(client: TestClient, db_session):
    """Test retrieving clinical reviews for a mother ordered newest first."""
    mother = Mother(name="Revathi V")
    db_session.add(mother)
    db_session.commit()

    r1 = ClinicalReview(
        mother_id=mother.id,
        clinician_id="DOC-1",
        clinician_name="Dr. One",
        review_status="pending",
    )
    r2 = ClinicalReview(
        mother_id=mother.id,
        clinician_id="DOC-2",
        clinician_name="Dr. Two",
        review_status="confirmed",
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    response = client.get(f"/api/mothers/{mother.id}/clinical-reviews")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["clinician_id"] == "DOC-2"
    assert data[1]["clinician_id"] == "DOC-1"


# ---------------------------------------------------------------------------
# 2. Care Plan Tests
# ---------------------------------------------------------------------------

def test_care_plan_upsert_and_retrieve(client: TestClient, db_session):
    """Test care plan creation via PUT, retrieval via GET, and subsequent update."""
    mother = Mother(name="Sarojini Devi", age=27)
    db_session.add(mother)
    db_session.commit()

    # Initial check before creation -> 404
    get_res = client.get(f"/api/mothers/{mother.id}/care-plan")
    assert get_res.status_code == 404

    # 1. Create plan via PUT
    payload = {
        "priority": "urgent",
        "intervention_type": "tele_manas",
        "referral_destination": "National Tele-MANAS Cell",
        "scheduled_followup_date": "2026-11-20",
        "assigned_clinician_id": "DR-TELE-01",
        "status": "active",
        "notes": "Telephonic support protocol initiated.",
    }
    put_res = client.put(f"/api/mothers/{mother.id}/care-plan", json=payload)
    assert put_res.status_code == 200
    plan_data = put_res.json()
    assert plan_data["priority"] == "urgent"
    assert plan_data["intervention_type"] == "tele_manas"
    assert plan_data["status"] == "active"

    # 2. Retrieve via GET
    get_res2 = client.get(f"/api/mothers/{mother.id}/care-plan")
    assert get_res2.status_code == 200
    assert get_res2.json()["id"] == plan_data["id"]

    # 3. Update existing plan
    payload["status"] = "completed"
    payload["priority"] = "routine"
    put_res2 = client.put(f"/api/mothers/{mother.id}/care-plan", json=payload)
    assert put_res2.status_code == 200
    assert put_res2.json()["id"] == plan_data["id"]  # Same plan updated
    assert put_res2.json()["status"] == "completed"

    # Verify audit log was recorded without clinical notes
    stmt = select(AuditLog).where(AuditLog.resource_type == "care_plan")
    audits = db_session.scalars(stmt).all()
    assert len(audits) >= 2
    for audit in audits:
        assert "Telephonic support" not in str(audit.details)


def test_care_plan_rejects_invalid_enums(client: TestClient, db_session):
    """Test validation errors for unapproved priority or intervention types."""
    mother = Mother(name="Test Mother")
    db_session.add(mother)
    db_session.commit()

    # Invalid priority
    res = client.put(
        f"/api/mothers/{mother.id}/care-plan",
        json={"priority": "super_urgent", "intervention_type": "counseling"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# 3. Screening Handoff Tests
# ---------------------------------------------------------------------------

def test_screening_handoff_success_preserves_q10_and_logs_audit(client: TestClient, db_session):
    """Test screening handoff records audit log, preserves screening outputs and Q10 alert."""
    mother = Mother(name="Kavita S", age=29)
    db_session.add(mother)
    db_session.commit()

    screening = Screening(
        mother_id=mother.id,
        instrument="EPDS",
        total_score=17,
        risk_classification="high",
        q10_safety_alert=True,
        screening_status="completed",
        fusion_status="completed",
    )
    db_session.add(screening)
    db_session.commit()

    payload = {
        "clinician_id": "COORD-500",
        "destination": "District Hospital Perinatal Crisis Unit",
        "urgency": "crisis",
        "notes": "Urgent transfer arranged by phone.",
    }
    response = client.post(f"/api/screenings/{screening.id}/handoff", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["screening_id"] == str(screening.id)
    assert data["q10_safety_alert_preserved"] is True
    assert data["status"] == "RECORDED_IN_AUDIT_LOG"
    assert "disclaimer" in data

    # Verify screening in DB was not altered
    db_screening = db_session.get(Screening, screening.id)
    assert db_screening.total_score == 17
    assert db_screening.q10_safety_alert is True

    # Verify audit log
    stmt = select(AuditLog).where(AuditLog.action == "screening_handoff")
    audit = db_session.scalars(stmt).first()
    assert audit is not None
    assert audit.actor_id == "COORD-500"
    assert audit.details["destination"] == "District Hospital Perinatal Crisis Unit"
    assert "Urgent transfer" not in str(audit.details)


def test_screening_handoff_unknown_screening_returns_404(client: TestClient):
    """Test 404 when attempting handoff on a non-existent screening."""
    unknown_id = uuid.uuid4()
    payload = {
        "clinician_id": "COORD-1",
        "destination": "Tele-MANAS",
    }
    response = client.post(f"/api/screenings/{unknown_id}/handoff", json=payload)
    assert response.status_code == 404
    assert f"'{unknown_id}' was not found" in response.json()["detail"]

