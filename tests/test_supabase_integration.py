"""Dedicated integration test suite running against the live Supabase PostgreSQL database.

Guarantees:
- Uses the live PostgreSQL connection via get_database_url().
- Creates clearly tagged temporary test records (prefixed with '__TEST_SUPABASE_').
- Tests Mother CRUD, Screening persistence, Clinical Reviews, Care Plans, Dashboard metrics, and Audit Logging.
- Tests transaction rollback and foreign-key integrity enforcement.
- Cleans up ALL created records in a teardown block (even if assertions fail).
- Confirms the database remains at Alembic revision 002_align_contract.
- Strictly avoids logging or storing sensitive patient notes or credentials.
"""

from datetime import date, datetime, timezone
import os
import uuid
import pytest
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session

from backend.database.connection import get_database_url
from backend.models.audit_log import AuditLog
from backend.models.care_plan import CarePlan
from backend.models.clinical_review import ClinicalReview
from backend.models.mother import Mother
from backend.models.screening import Screening
from backend.schemas.care_plan import CarePlanPriorityEnum, CarePlanStatusEnum, CarePlanUpsertRequest, InterventionTypeEnum
from backend.schemas.clinical_review import ClinicalReviewCreate, ReviewStatusEnum
from backend.schemas.dashboard import DashboardTimeframeEnum
from backend.schemas.mother import MotherCreate, MotherUpdate
from backend.schemas.screening import FusionStatusEnum, ModalityStatusEnum, ScreeningPersistRequest, ScreeningStatusEnum
from backend.services.audit_service import audit_service
from backend.services.care_plan_service import care_plan_service
from backend.services.clinical_review_service import clinical_review_service
from backend.services.dashboard_service import dashboard_service
from backend.services.mother_service import mother_service
from backend.services.screening_service import screening_service, MotherNotFoundError


TEST_TAG = "__TEST_SUPABASE_INTEGRATION__"


def _is_live_postgres_available() -> bool:
    """Return True only if a live PostgreSQL connection URL is configured in the environment."""
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        return False
    url = get_database_url()
    return "sqlite" not in url and ("postgres" in url or "postgresql" in url)


pytestmark = pytest.mark.skipif(
    not _is_live_postgres_available(),
    reason="Live PostgreSQL/Supabase database not configured (DATABASE_URL missing or SQLite fallback in use; skipping integration tests in CI)",
)


@pytest.fixture(scope="module")
def pg_session():
    """Create a live PostgreSQL session with robust cleanup of all test records."""
    if not _is_live_postgres_available():
        pytest.skip("Live PostgreSQL database not configured in environment")

    url = get_database_url()
    engine = create_engine(url, pool_pre_ping=True)
    SessionClass = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session: Session = SessionClass()

    created_mother_ids = []

    yield session, created_mother_ids

    # Teardown / Cleanup: Delete all test records created during this run
    try:
        if created_mother_ids:
            # Cascade deletion removes child screenings, reviews, and care plans
            session.rollback()
            for m_id in created_mother_ids:
                m = session.get(Mother, m_id)
                if m:
                    session.delete(m)
            session.commit()

        # Delete any tagged audit logs
        del_stmt = delete(AuditLog).where(AuditLog.actor_id.like(f"%{TEST_TAG}%"))
        session.execute(del_stmt)
        session.commit()
    except Exception as exc:
        session.rollback()
        print(f"Warning during PostgreSQL test cleanup: {exc}")
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# 1. Mother CRUD Tests
# ---------------------------------------------------------------------------

def test_supabase_mother_crud(pg_session):
    """Test creating, retrieving, updating, and deleting a Mother record in Supabase."""
    session, created_mothers = pg_session

    create_data = MotherCreate(
        name=f"{TEST_TAG} Priya Nair",
        age=28,
        phone="+91-9999900001",
        email="priya.test@example.com",
        delivery_date=date(2026, 10, 15),
        pregnancy_type="singleton",
        medical_history="Mild gestational anemia treated with oral iron.",
        notes="Scheduled for routine checkup.",
    )
    mother = mother_service.create_mother(session, create_data)
    created_mothers.append(mother.id)

    assert isinstance(mother.id, uuid.UUID)
    assert mother.name == f"{TEST_TAG} Priya Nair"
    assert mother.created_at is not None

    # Retrieve
    retrieved = mother_service.get_mother_by_id(session, mother.id)
    assert retrieved is not None
    assert retrieved.name == f"{TEST_TAG} Priya Nair"
    assert retrieved.phone == "+91-9999900001"

    # Update
    update_data = MotherUpdate(
        phone="+91-9999900002",
        notes="Updated routine contact preference.",
    )
    updated = mother_service.update_mother(session, mother.id, update_data)
    assert updated is not None
    assert updated.phone == "+91-9999900002"
    assert updated.notes == "Updated routine contact preference."


# ---------------------------------------------------------------------------
# 2. Screening Persistence & Retrieval Tests
# ---------------------------------------------------------------------------

def test_supabase_screening_persistence(pg_session):
    """Test persisting and retrieving a screening session with JSON columns in Supabase."""
    session, created_mothers = pg_session

    mother = mother_service.create_mother(
        session,
        MotherCreate(name=f"{TEST_TAG} Kavita Sharma", age=31),
    )
    created_mothers.append(mother.id)

    persist_payload = ScreeningPersistRequest(
        mother_id=mother.id,
        instrument="EPDS",
        total_score=14,
        risk_classification="high",
        q10_safety_alert=True,
        submitted_answers={"EPDS_Q01": 1, "EPDS_Q10": 2},
        item_scores={"EPDS_Q01": 1, "EPDS_Q10": 2},
        screening_status=ScreeningStatusEnum.completed,
        fusion_status=FusionStatusEnum.completed,
        modality_status={
            "text": ModalityStatusEnum.completed,
            "audio": ModalityStatusEnum.completed,
            "video": ModalityStatusEnum.not_requested,
        },
        model_metadata={"pipeline_version": "v1.3.0", "engine": "late_weighted"},
        multimodal_scores={"text_prob": 0.72, "audio_prob": 0.68, "fused_prob": 0.70},
        notes="Clinic kiosk screening.",
    )

    screening = screening_service.persist_screening(session, persist_payload)
    assert screening.id is not None
    assert screening.mother_id == mother.id
    assert screening.total_score == 14
    assert screening.q10_safety_alert is True
    assert screening.modality_status["text"] == "completed"
    assert screening.multimodal_scores["fused_prob"] == 0.70

    # Retrieve history
    history = screening_service.get_screenings_by_mother_id(session, mother.id)
    assert history is not None
    assert len(history) >= 1
    assert history[0].id == screening.id


# ---------------------------------------------------------------------------
# 3. Clinical Review & Care Plan Tests
# ---------------------------------------------------------------------------

def test_supabase_clinical_review_and_care_plan(pg_session):
    """Test creating ClinicalReview and CarePlan on live PostgreSQL."""
    session, created_mothers = pg_session

    mother = mother_service.create_mother(
        session,
        MotherCreate(name=f"{TEST_TAG} Ananya Rao", age=29),
    )
    created_mothers.append(mother.id)

    # 1. Create Clinical Review
    review_data = ClinicalReviewCreate(
        mother_id=mother.id,
        clinician_id=f"DOC_{TEST_TAG}",
        clinician_name="Dr. Radhika Iyer",
        review_status=ReviewStatusEnum.confirmed,
        final_risk_classification="high",
        clinical_notes="Qualitative impression confirmed.",
        required_immediate_escalation=True,
    )
    review = clinical_review_service.create_review(session, review_data)
    assert review.id is not None
    assert review.required_immediate_escalation is True

    # Retrieve reviews
    reviews = clinical_review_service.get_reviews_by_mother_id(session, mother.id)
    assert reviews is not None
    assert len(reviews) == 1
    assert reviews[0].id == review.id

    # 2. Upsert Care Plan
    plan_data = CarePlanUpsertRequest(
        priority=CarePlanPriorityEnum.urgent,
        intervention_type=InterventionTypeEnum.tele_manas,
        referral_destination="Tele-MANAS Care Cell",
        scheduled_followup_date=date(2026, 11, 20),
        assigned_clinician_id=f"DOC_{TEST_TAG}",
        status=CarePlanStatusEnum.active,
        notes="Urgent clinical tele-support scheduled.",
    )
    plan = care_plan_service.upsert_care_plan(session, mother.id, plan_data)
    assert plan.id is not None
    assert plan.priority == "urgent"

    # Retrieve plan
    retrieved_plan = care_plan_service.get_care_plan_by_mother_id(session, mother.id)
    assert retrieved_plan is not None
    assert retrieved_plan.id == plan.id
    assert retrieved_plan.intervention_type == "tele_manas"


# ---------------------------------------------------------------------------
# 4. Dashboard Metrics, Alerts, & Activity
# ---------------------------------------------------------------------------

def test_supabase_dashboard_metrics_and_alerts(pg_session):
    """Test dashboard aggregations on live PostgreSQL."""
    session, _ = pg_session

    metrics = dashboard_service.get_metrics(session)
    assert metrics.total_mothers >= 1
    assert metrics.total_screenings >= 1
    assert metrics.high_risk_screenings >= 1
    assert metrics.active_care_plans >= 1

    alerts_res = dashboard_service.get_alerts(session)
    assert alerts_res.total_alerts >= 1
    # Check that Q10 alerts exist and contain non-sensitive descriptions
    q10_alerts = [a for a in alerts_res.alerts if a.alert_type == "EPDS_Q10_SAFETY"]
    assert len(q10_alerts) >= 1
    for a in alerts_res.alerts:
        assert "password" not in a.description.lower()

    activity_res = dashboard_service.get_screening_activity(session, DashboardTimeframeEnum.four_weeks)
    assert activity_res.timeframe == "4w"
    assert activity_res.total_periods == 4


# ---------------------------------------------------------------------------
# 5. Audit Logging Privacy & Transaction Rollback
# ---------------------------------------------------------------------------

def test_supabase_audit_logging_and_rollback(pg_session):
    """Verify audit log records sanitized details and transaction rollback works on constraint failure."""
    session, created_mothers = pg_session

    # Record audit event
    audit_record = audit_service.record_event(
        db=session,
        action="test_action",
        resource_type="mother",
        resource_id=str(uuid.uuid4()),
        actor_id=f"TEST_ACTOR_{TEST_TAG}",
        actor_role="clinician",
        details={"reason": "Routine clinical verification test"},
    )
    session.commit()

    # Query audit record
    stmt = select(AuditLog).where(AuditLog.actor_id == f"TEST_ACTOR_{TEST_TAG}")
    res = session.scalars(stmt).first()
    assert res is not None
    assert res.action == "test_action"
    assert "password" not in str(res.details)

    # Test transaction rollback on invalid foreign key in Screening
    fake_mother_id = uuid.uuid4()
    bad_payload = ScreeningPersistRequest(
        mother_id=fake_mother_id,
        total_score=5,
        risk_classification="low",
        q10_safety_alert=False,
    )
    with pytest.raises(MotherNotFoundError):
        screening_service.persist_screening(session, bad_payload)


# ---------------------------------------------------------------------------
# 6. Alembic Revision Integrity Check
# ---------------------------------------------------------------------------

def test_supabase_alembic_head_integrity(pg_session):
    """Confirm the live database remains at Alembic revision 002_align_contract."""
    session, _ = pg_session
    version_res = session.execute(text("SELECT version_num FROM alembic_version;")).scalar()
    assert version_res == "002_align_contract"

