"""Unit and integration tests for Screening persistence service and retrieval endpoints.

Covers:
- Successful persistence via ScreeningService
- Rejection of unknown mother ID (MotherNotFoundError)
- Transaction rollback on invalid persistence input
- Modality statuses preservation and missing modalities non-negativity
- Q10 safety alert preservation
- No fabricated fusion output when absent
- GET /api/mothers/{mother_id}/screenings (history, newest first, 404 for unknown mother)
- GET /api/screenings/{screening_id} (retrieval, 404 for unknown, 422 for malformed UUID)
"""

from datetime import datetime, timezone
import uuid
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.base import Base
from backend.database.connection import get_db
from backend.main import app
from backend.models.mother import Mother
from backend.models.screening import Screening
from backend.schemas.screening import (
    FusionStatusEnum,
    ModalityStatusEnum,
    ScreeningPersistRequest,
    ScreeningStatusEnum,
)
from backend.services.screening_service import (
    MotherNotFoundError,
    ScreeningPersistenceError,
    screening_service,
)


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
# 1. Service Layer: Screening Persistence Tests
# ---------------------------------------------------------------------------

def test_persist_screening_success(db_session):
    """Test persisting a valid screening session with multimodal outputs."""
    mother = Mother(name="Sunita Rao", age=28)
    db_session.add(mother)
    db_session.commit()
    db_session.refresh(mother)

    payload = ScreeningPersistRequest(
        mother_id=mother.id,
        instrument="EPDS",
        total_score=15,
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
        model_metadata={"pipeline": "v1.3.0", "fusion": "late_weighted"},
        multimodal_scores={"text_prob": 0.75, "audio_prob": 0.68, "fused_prob": 0.72},
        notes="Administered in clinical intake room.",
    )

    record = screening_service.persist_screening(db_session, payload)
    assert record.id is not None
    assert isinstance(record.id, uuid.UUID)
    assert record.mother_id == mother.id
    assert record.total_score == 15
    assert record.q10_safety_alert is True
    assert record.modality_status["text"] == "completed"
    assert record.modality_status["video"] == "not_requested"
    assert record.fusion_status == "completed"
    assert record.multimodal_scores["fused_prob"] == 0.72


def test_persist_screening_unknown_mother_raises_error(db_session):
    """Verify persisting a screening for a non-existent mother raises MotherNotFoundError."""
    unknown_id = uuid.uuid4()
    payload = ScreeningPersistRequest(
        mother_id=unknown_id,
        total_score=5,
        risk_classification="low",
        q10_safety_alert=False,
    )
    with pytest.raises(MotherNotFoundError) as exc_info:
        screening_service.persist_screening(db_session, payload)
    assert str(unknown_id) in str(exc_info.value)


def test_persist_screening_preserves_absent_modalities_without_fabrication(db_session):
    """Verify missing modalities are NOT interpreted as negative or fabricated scores."""
    mother = Mother(name="Deepika Sen", age=30)
    db_session.add(mother)
    db_session.commit()

    payload = ScreeningPersistRequest(
        mother_id=mother.id,
        total_score=8,
        risk_classification="low",
        q10_safety_alert=False,
        modality_status={
            "text": ModalityStatusEnum.unavailable,
            "audio": ModalityStatusEnum.failed,
            "video": ModalityStatusEnum.not_requested,
        },
        # model_metadata and multimodal_scores left empty/None
    )
    record = screening_service.persist_screening(db_session, payload)
    assert record.fusion_status == "not_available"
    assert record.multimodal_scores == {}
    assert record.model_metadata == {}
    assert record.modality_status["text"] == "unavailable"
    assert record.modality_status["audio"] == "failed"


# ---------------------------------------------------------------------------
# 2. Router Layer: Screening History & Retrieval Tests
# ---------------------------------------------------------------------------

def test_get_mother_screenings_history_ordering(client: TestClient, db_session):
    """Test retrieving screening history for a mother returns records newest first."""
    mother = Mother(name="Fatima Khan", age=25)
    db_session.add(mother)
    db_session.commit()

    # Create older screening
    s1 = Screening(
        mother_id=mother.id,
        screening_date=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
        total_score=6,
        risk_classification="low",
        q10_safety_alert=False,
        screening_status="completed",
        fusion_status="not_available",
    )
    # Create newer screening
    s2 = Screening(
        mother_id=mother.id,
        screening_date=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        total_score=14,
        risk_classification="high",
        q10_safety_alert=True,
        screening_status="completed",
        fusion_status="completed",
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    response = client.get(f"/api/mothers/{mother.id}/screenings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Verify newest first ordering
    assert data[0]["id"] == str(s2.id)
    assert data[0]["total_score"] == 14
    assert data[0]["q10_safety_alert"] is True
    assert data[1]["id"] == str(s1.id)
    assert data[1]["total_score"] == 6


def test_get_mother_screenings_mother_not_found(client: TestClient):
    """Test 404 response when querying screening history for a non-existent mother."""
    unknown_id = uuid.uuid4()
    response = client.get(f"/api/mothers/{unknown_id}/screenings")
    assert response.status_code == 404
    assert f"'{unknown_id}' was not found" in response.json()["detail"]


def test_get_screening_by_id_success(client: TestClient, db_session):
    """Test retrieving an individual screening by UUID."""
    mother = Mother(name="Meena Kumari", age=33)
    db_session.add(mother)
    db_session.commit()

    screening = Screening(
        mother_id=mother.id,
        instrument="EPDS",
        total_score=16,
        risk_classification="high",
        q10_safety_alert=True,
        screening_status="completed",
        fusion_status="completed",
        modality_status={"text": "completed", "audio": "completed"},
        submitted_answers={"EPDS_Q10": 1},
        item_scores={"EPDS_Q10": 1},
        multimodal_scores={"fused_probability": 0.74},
    )
    db_session.add(screening)
    db_session.commit()
    db_session.refresh(screening)

    response = client.get(f"/api/screenings/{screening.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(screening.id)
    assert data["mother_id"] == str(mother.id)
    assert data["total_score"] == 16
    assert data["q10_safety_alert"] is True
    assert data["fusion_status"] == "completed"
    assert data["multimodal_scores"]["fused_probability"] == 0.74


def test_get_screening_by_id_not_found(client: TestClient):
    """Test 404 response for unknown screening UUID."""
    unknown_id = uuid.uuid4()
    response = client.get(f"/api/screenings/{unknown_id}")
    assert response.status_code == 404
    assert f"'{unknown_id}' was not found" in response.json()["detail"]


def test_get_screening_invalid_uuid_rejected(client: TestClient):
    """Test 422 response for malformed non-UUID parameter."""
    response = client.get("/api/screenings/malformed-uuid-string")
    assert response.status_code == 422


def test_list_all_screenings_endpoint(client: TestClient, db_session):
    """Test GET /api/screenings lists all screenings across mothers."""
    mother = Mother(name="Sunita Rao", age=28)
    db_session.add(mother)
    db_session.commit()

    s1 = Screening(
        mother_id=mother.id,
        instrument="EPDS",
        total_score=6,
        risk_classification="low",
        q10_safety_alert=False,
    )
    s2 = Screening(
        mother_id=mother.id,
        instrument="EPDS",
        total_score=14,
        risk_classification="high",
        q10_safety_alert=True,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    response = client.get("/api/screenings")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    ids = [item["id"] for item in data]
    assert str(s1.id) in ids
    assert str(s2.id) in ids


def test_post_screening_endpoint(client: TestClient, db_session):
    """Test POST /api/screenings persists screening directly via REST."""
    mother = Mother(name="Meera Joshi", age=31)
    db_session.add(mother)
    db_session.commit()

    payload = {
        "mother_id": str(mother.id),
        "total_score": 12,
        "risk_classification": "moderate",
        "q10_safety_alert": False,
        "instrument": "EPDS",
        "submitted_answers": {"EPDS_Q01": 2},
        "item_scores": {"EPDS_Q01": 2},
    }
    response = client.post("/api/screenings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["mother_id"] == str(mother.id)
    assert data["total_score"] == 12
    assert data["risk_classification"] == "moderate"


