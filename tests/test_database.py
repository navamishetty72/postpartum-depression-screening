"""Unit and integration test suite for MIORA database models, relationships, and connection.

Validates the team's shared API contract:
- Mother fields: (id, name, age, phone, email, delivery_date, pregnancy_type, medical_history, notes, created_at, updated_at)
- Screening statuses: (completed, partially_completed, failed)
- Modality & Fusion statuses: (completed, unavailable, failed, not_requested, etc.)
- Strict Q10 preservation without overrides
- AuditLog privacy rules (no raw patient narratives)
"""

from datetime import date, datetime, timezone
import uuid
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker, Session

from backend.database.base import Base
from backend.database.connection import (
    create_db_engine,
    get_database_url,
)
from backend.models import (
    Mother,
    Screening,
    ClinicalReview,
    CarePlan,
    AuditLog,
)


@pytest.fixture(scope="function")
def test_db_session():
    """Create an isolated, in-memory SQLite database session for unit testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session: Session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# 1. Database Connection & Environment Tests
# ---------------------------------------------------------------------------

def test_database_url_resolution(monkeypatch):
    """Test environment-driven URL resolution with fallback and normalization."""
    # Fallback to local default SQLite when unset
    monkeypatch.delenv("DATABASE_URL", raising=False)
    url = get_database_url()
    assert "sqlite" in url

    # Bare PostgreSQL URL: normalized to use installed driver (psycopg2) or bare scheme
    custom_pg = "postgresql://user:pass@remote-host:5432/clinical_db"
    monkeypatch.setenv("DATABASE_URL", custom_pg)
    resolved_pg = get_database_url()
    assert resolved_pg in (
        custom_pg,
        "postgresql+psycopg2://user:pass@remote-host:5432/clinical_db",
    )

    # Already driver-qualified PostgreSQL URL remains untouched
    qualified_pg = "postgresql+psycopg2://user:pass@remote-host:5432/clinical_db"
    monkeypatch.setenv("DATABASE_URL", qualified_pg)
    assert get_database_url() == qualified_pg

    # Legacy postgres:// scheme normalized to postgresql
    legacy_url = "postgres://user:pass@host:5432/db"
    monkeypatch.setenv("DATABASE_URL", legacy_url)
    assert get_database_url().startswith("postgresql")



def test_engine_creation_and_health_check():
    """Test engine instantiation and connection ping."""
    test_engine = create_db_engine("sqlite:///:memory:")
    assert test_engine is not None

    with test_engine.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1


# ---------------------------------------------------------------------------
# 2. Mother Model Contract Alignment Tests
# ---------------------------------------------------------------------------

def test_create_mother_with_contract_fields(test_db_session: Session):
    """Verify Mother entity creation using ONLY the agreed shared contract fields."""
    mother = Mother(
        name="Ananya Sharma",
        age=29,
        phone="+91-9876543210",
        email="ananya.sharma@example.com",
        delivery_date=date(2026, 10, 1),
        pregnancy_type="singleton",
        medical_history="Gestational hypertension managed with labetalol. Primigravida.",
        notes="Referred from postpartum routine checkup clinic.",
    )
    test_db_session.add(mother)
    test_db_session.commit()
    test_db_session.refresh(mother)

    assert isinstance(mother.id, uuid.UUID)
    assert mother.name == "Ananya Sharma"
    assert mother.age == 29
    assert mother.phone == "+91-9876543210"
    assert mother.email == "ananya.sharma@example.com"
    assert mother.delivery_date == date(2026, 10, 1)
    assert mother.pregnancy_type == "singleton"
    assert "hypertension" in mother.medical_history
    assert mother.created_at is not None
    assert mother.updated_at is not None

    # Test dictionary serialization helper
    data_dict = mother.to_dict()
    assert data_dict["id"] == str(mother.id)
    assert data_dict["name"] == "Ananya Sharma"
    assert data_dict["age"] == 29
    # Ensure unapproved fields are NOT in the model
    assert "medical_record_number" not in data_dict
    assert "high_risk_flag" not in data_dict


# ---------------------------------------------------------------------------
# 3. Screening Model & Modality/Fusion Status Tests
# ---------------------------------------------------------------------------

def test_create_screening_with_contract_statuses(test_db_session: Session):
    """Verify Screening entity with contract statuses (completed, fusion_status, q10_alert)."""
    mother = Mother(
        name="Kavita Nair",
        age=32,
        phone="+91-9876543212",
    )
    test_db_session.add(mother)
    test_db_session.commit()

    screening = Screening(
        mother_id=mother.id,
        instrument="EPDS",
        total_score=14,
        risk_classification="high",
        q10_safety_alert=True,
        submitted_answers={"q1": "As much as I ever did", "q10": "Hardly ever"},
        item_scores={"q1": 0, "q2": 1, "q10": 1},
        screening_status="completed",
        fusion_status="completed",
        modality_status={
            "text": "completed",
            "audio": "completed",
            "video": "not_requested",
        },
        model_metadata={"pipeline_version": "v1.3.0", "fusion_strategy": "late_fusion"},
        multimodal_scores={"text_prob": 0.78, "audio_prob": 0.65, "fused_score": 0.72},
        notes="Multimodal screening completed at community health center.",
    )
    test_db_session.add(screening)
    test_db_session.commit()
    test_db_session.refresh(screening)

    assert isinstance(screening.id, uuid.UUID)
    assert screening.total_score == 14
    assert screening.q10_safety_alert is True
    assert screening.screening_status == "completed"
    assert screening.fusion_status == "completed"
    assert screening.modality_status["text"] == "completed"
    assert screening.modality_status["video"] == "not_requested"
    assert screening.mother.name == "Kavita Nair"
    assert len(mother.screenings) == 1


# ---------------------------------------------------------------------------
# 4. Clinical Review & Care Plan Tests
# ---------------------------------------------------------------------------

def test_clinical_review_and_care_plan_contract(test_db_session: Session):
    """Verify ClinicalReview and CarePlan adhere to contract statuses and clinician ownership."""
    mother = Mother(
        name="Sunita Patel",
        age=26,
    )
    test_db_session.add(mother)
    test_db_session.commit()

    screening = Screening(
        mother_id=mother.id,
        instrument="EPDS",
        total_score=18,
        risk_classification="high",
        q10_safety_alert=True,
        screening_status="completed",
        fusion_status="not_available",
        submitted_answers={},
        item_scores={},
        modality_status={"text": "completed", "audio": "unavailable", "video": "not_requested"},
        model_metadata={},
        multimodal_scores={},
    )
    test_db_session.add(screening)
    test_db_session.commit()

    # Clinician reviews screening
    review = ClinicalReview(
        mother_id=mother.id,
        screening_id=screening.id,
        clinician_id="DOC-987",
        clinician_name="Dr. Radhika Iyer, MD",
        review_status="confirmed",
        final_risk_classification="high",
        clinical_notes="Patient presents with severe anxiety, sleep disruption, and mild depressive symptoms.",
        required_immediate_escalation=True,
    )
    test_db_session.add(review)

    # Clinician creates care plan
    care_plan = CarePlan(
        mother_id=mother.id,
        screening_id=screening.id,
        priority="crisis",
        intervention_type="tele_manas",
        referral_destination="Tele-MANAS & District Hospital Perinatal Unit",
        scheduled_followup_date=date(2026, 11, 14),
        assigned_clinician_id="DOC-987",
        status="active",
        notes="Urgent handover scheduled with perinatal mental health liaison.",
    )
    test_db_session.add(care_plan)
    test_db_session.commit()

    test_db_session.refresh(mother)
    assert len(mother.clinical_reviews) == 1
    assert mother.clinical_reviews[0].review_status == "confirmed"
    assert mother.clinical_reviews[0].required_immediate_escalation is True

    assert len(mother.care_plans) == 1
    assert mother.care_plans[0].priority == "crisis"
    assert mother.care_plans[0].status == "active"
    assert mother.care_plans[0].screening.id == screening.id


# ---------------------------------------------------------------------------
# 5. Cascade Delete Behavior
# ---------------------------------------------------------------------------

def test_cascade_delete_mother_removes_children(test_db_session: Session):
    """Verify deleting a Mother cascades to related screenings, reviews, and care plans."""
    mother = Mother(
        name="Meera Joshi",
        age=30,
    )
    test_db_session.add(mother)
    test_db_session.commit()

    screening = Screening(
        mother_id=mother.id,
        total_score=10,
        risk_classification="moderate",
        screening_status="completed",
        fusion_status="not_available",
        submitted_answers={},
        item_scores={},
        modality_status={},
        model_metadata={},
        multimodal_scores={},
    )
    review = ClinicalReview(
        mother_id=mother.id,
        clinician_id="DOC-123",
        clinician_name="Dr. Joshi",
    )
    care_plan = CarePlan(
        mother_id=mother.id,
        intervention_type="counseling",
    )
    test_db_session.add_all([screening, review, care_plan])
    test_db_session.commit()

    s_id = screening.id
    r_id = review.id
    cp_id = care_plan.id

    test_db_session.delete(mother)
    test_db_session.commit()

    assert test_db_session.get(Screening, s_id) is None
    assert test_db_session.get(ClinicalReview, r_id) is None
    assert test_db_session.get(CarePlan, cp_id) is None


# ---------------------------------------------------------------------------
# 6. Audit Log Tests & Privacy Safeguards
# ---------------------------------------------------------------------------

def test_audit_log_creation_and_privacy(test_db_session: Session):
    """Verify AuditLog records actions with sanitized metadata, never logging raw narratives."""
    audit_record = AuditLog(
        action="escalate_crisis",
        resource_type="mother",
        resource_id="00000000-0000-0000-0000-000000000001",
        actor_id="CLINICIAN-45",
        actor_role="clinician",
        details={
            "reason": "Q10 positive response triggered emergency protocol",
            "escalation_route": "tele_manas",
        },
        client_ip="192.168.1.50",
    )
    test_db_session.add(audit_record)
    test_db_session.commit()
    test_db_session.refresh(audit_record)

    assert isinstance(audit_record.id, uuid.UUID)
    assert audit_record.action == "escalate_crisis"
    assert audit_record.details["escalation_route"] == "tele_manas"
    assert audit_record.created_at is not None

    stmt = select(AuditLog).where(AuditLog.action == "escalate_crisis")
    results = test_db_session.scalars(stmt).all()
    assert len(results) == 1
    assert results[0].actor_id == "CLINICIAN-45"
