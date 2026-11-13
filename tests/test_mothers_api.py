"""Unit and integration tests for Mother Management API endpoints.

Covers:
- POST /api/mothers (creation, validation)
- GET /api/mothers (listing, pagination)
- GET /api/mothers/{mother_id} (retrieval, 404 for unknown, 422 for malformed UUID)
- PUT /api/mothers/{mother_id} (partial updates)
- Privacy enforcement: confirming medical history / notes are not logged.
"""

from datetime import date
import logging
import uuid
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.database.connection import get_db
from backend.main import app
from backend.models.mother import Mother


@pytest.fixture(scope="function")
def db_session():
    """Create an isolated, in-memory SQLite database session for API tests.

    Uses StaticPool so all connections and threads share the single in-memory database.
    """
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
# 1. POST /api/mothers Tests
# ---------------------------------------------------------------------------

def test_create_mother_success(client: TestClient, caplog):
    """Test creating a mother with valid agreed contract fields."""
    payload = {
        "name": "Ananya Sharma",
        "age": 29,
        "phone": "+91-9876543210",
        "email": "ananya.sharma@example.com",
        "delivery_date": "2026-10-01",
        "pregnancy_type": "singleton",
        "medical_history": "Mild anemia during third trimester; resolved with oral iron.",
        "notes": "Prefers evening clinical follow-up calls.",
    }
    with caplog.at_level(logging.INFO):
        response = client.post("/api/mothers", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Ananya Sharma"
    assert data["age"] == 29
    assert data["phone"] == "+91-9876543210"
    assert data["email"] == "ananya.sharma@example.com"
    assert data["delivery_date"] == "2026-10-01"
    assert data["pregnancy_type"] == "singleton"
    assert data["medical_history"] == payload["medical_history"]
    assert data["notes"] == payload["notes"]
    assert "created_at" in data
    assert "updated_at" in data

    # Verify sensitive medical history is NEVER written to logger
    for record in caplog.records:
        assert "anemia" not in record.message
        assert "Prefers evening" not in record.message


def test_create_mother_minimal_required_fields(client: TestClient):
    """Confirm optional fields can be safely omitted."""
    payload = {
        "name": "Priya Nair",
    }
    response = client.post("/api/mothers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Priya Nair"
    assert data["age"] is None
    assert data["phone"] is None
    assert data["email"] is None
    assert data["delivery_date"] is None
    assert data["pregnancy_type"] is None
    assert data["medical_history"] is None
    assert data["notes"] is None


def test_create_mother_invalid_payload_rejected(client: TestClient):
    """Test input validation for missing required name or out-of-range age."""
    # Missing name
    res1 = client.post("/api/mothers", json={"age": 25})
    assert res1.status_code == 422

    # Empty string name
    res2 = client.post("/api/mothers", json={"name": ""})
    assert res2.status_code == 422

    # Invalid age (negative or extreme)
    res3 = client.post("/api/mothers", json={"name": "Test Mother", "age": -5})
    assert res3.status_code == 422

    res4 = client.post("/api/mothers", json={"name": "Test Mother", "age": 150})
    assert res4.status_code == 422


# ---------------------------------------------------------------------------
# 2. GET /api/mothers (Listing) Tests
# ---------------------------------------------------------------------------

def test_list_mothers_with_pagination(client: TestClient, db_session):
    """Test retrieving a paginated list of registered mothers."""
    # Seed 3 mothers
    for i in range(3):
        m = Mother(name=f"Mother {i}", age=25 + i)
        db_session.add(m)
    db_session.commit()

    response = client.get("/api/mothers?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Second page
    response_p2 = client.get("/api/mothers?skip=2&limit=2")
    assert response_p2.status_code == 200
    assert len(response_p2.json()) == 1


# ---------------------------------------------------------------------------
# 3. GET /api/mothers/{mother_id} Tests
# ---------------------------------------------------------------------------

def test_get_mother_by_id_success(client: TestClient, db_session):
    """Test retrieving an existing mother by UUID."""
    mother = Mother(
        name="Deepa Verma",
        age=31,
        phone="+91-9123456789",
    )
    db_session.add(mother)
    db_session.commit()
    db_session.refresh(mother)

    response = client.get(f"/api/mothers/{mother.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(mother.id)
    assert data["name"] == "Deepa Verma"
    assert data["age"] == 31


def test_get_mother_not_found(client: TestClient):
    """Test 404 response for unknown random UUID."""
    unknown_id = uuid.uuid4()
    response = client.get(f"/api/mothers/{unknown_id}")
    assert response.status_code == 404
    assert f"'{unknown_id}' was not found" in response.json()["detail"]


def test_get_mother_invalid_uuid_rejected(client: TestClient):
    """Test 422 unprocessable entity for invalid non-UUID path parameter."""
    response = client.get("/api/mothers/not-a-valid-uuid-string")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 4. PUT /api/mothers/{mother_id} Tests
# ---------------------------------------------------------------------------

def test_update_mother_partial_fields(client: TestClient, db_session, caplog):
    """Test updating existing mother fields without altering untouched fields."""
    mother = Mother(
        name="Sunita Joshi",
        age=27,
        phone="+91-9876500000",
        notes="Initial consultation notes",
    )
    db_session.add(mother)
    db_session.commit()
    db_session.refresh(mother)

    update_payload = {
        "phone": "+91-9999999999",
        "notes": "Updated contact instructions",
    }
    with caplog.at_level(logging.INFO):
        response = client.put(f"/api/mothers/{mother.id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(mother.id)
    assert data["name"] == "Sunita Joshi"  # Unchanged
    assert data["age"] == 27  # Unchanged
    assert data["phone"] == "+91-9999999999"  # Updated
    assert data["notes"] == "Updated contact instructions"  # Updated

    # Ensure notes are not written to logs
    for record in caplog.records:
        assert "Updated contact instructions" not in record.message


def test_update_mother_not_found(client: TestClient):
    """Test 404 response when attempting to update an unknown mother ID."""
    unknown_id = uuid.uuid4()
    response = client.put(f"/api/mothers/{unknown_id}", json={"name": "Ghost Name"})
    assert response.status_code == 404
    assert f"'{unknown_id}' was not found" in response.json()["detail"]

