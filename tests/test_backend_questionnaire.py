"""Backend API integration tests for the EPDS questionnaire endpoints.

Validates GET /api/questionnaire/epds and POST /api/questionnaire/epds/submit,
including Item 10 safety escalation and override protection.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root_health_check():
    """Verify health endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["is_diagnostic"] is False


def test_get_epds_questionnaire_endpoint():
    """Verify GET /api/questionnaire/epds loads the 10-item question bank."""
    response = client.get("/api/questionnaire/epds")
    assert response.status_code == 200
    data = response.json()

    # Verify instrument metadata
    assert data["instrument"]["name"] == "Edinburgh Postnatal Depression Scale"
    assert data["instrument"]["abbreviation"] == "EPDS"
    assert data["instrument"]["question_count"] == 10
    assert data["instrument"]["maximum_score"] == 30
    assert data["instrument"]["is_diagnostic"] is False

    # Verify 10 questions and 4 options each
    questions = data["questions"]
    assert len(questions) == 10
    for i, q in enumerate(questions, start=1):
        assert q["id"] == f"EPDS_Q{i:02d}"
        assert len(q["response_options"]) == 4
        assert "source" in q and q["source"]["url"].startswith("http")

    # Item 10 check
    assert questions[9]["id"] == "EPDS_Q10"
    assert questions[9]["safety_critical"] is True


def test_submit_epds_all_zero_score_low_risk():
    """Submitting answers corresponding to 0 points should yield total_score=0 and no safety alert."""
    # Q1, Q2, Q4 direct scored: index 0 gives score 0
    # Q3, Q5-Q10 reverse scored: index 3 gives score 0
    answers = []
    for i in range(1, 11):
        qid = f"EPDS_Q{i:02d}"
        if qid in {"EPDS_Q01", "EPDS_Q02", "EPDS_Q04"}:
            idx = 0
        else:
            idx = 3
        answers.append({"question_id": qid, "selected_index": idx})

    response = client.post("/api/questionnaire/epds/submit", json={"answers": answers})
    assert response.status_code == 200
    res = response.json()

    assert res["total_score"] == 0
    assert res["maximum_score"] == 30
    assert res["classification"] == "Low likelihood of depressive illness"
    assert res["is_diagnostic"] is False
    assert res["safety_alert"]["triggered"] is False
    assert res["safety_alert"]["severity"] == "NONE"
    assert len(res["item_scores"]) == 10
    assert all(item["score"] == 0 for item in res["item_scores"])


def test_submit_epds_all_three_score_maximum_risk():
    """Submitting answers corresponding to 3 points should yield total_score=30 and safety alert."""
    # Q1, Q2, Q4 direct scored: index 3 gives score 3
    # Q3, Q5-Q10 reverse scored: index 0 gives score 3
    answers = []
    for i in range(1, 11):
        qid = f"EPDS_Q{i:02d}"
        if qid in {"EPDS_Q01", "EPDS_Q02", "EPDS_Q04"}:
            idx = 3
        else:
            idx = 0
        answers.append({"question_id": qid, "selected_index": idx})

    response = client.post("/api/questionnaire/epds/submit", json={"answers": answers})
    assert response.status_code == 200
    res = response.json()

    assert res["total_score"] == 30
    assert res["classification"] == "Probable depression"
    assert res["safety_alert"]["triggered"] is True
    assert res["safety_alert"]["question_10_score"] == 3
    assert res["safety_alert"]["severity"] == "URGENT_SAFETY_ASSESSMENT"
    assert len(res["safety_alert"]["escalation_protocol"]) > 0


def test_submit_epds_question_10_safety_override_with_low_total_score():
    """CRITICAL: Positive Q10 triggers urgent safety alert even when total score is low (e.g. 1)."""
    # Answer 0 for Q1-Q9, but score 1 for Q10 ("Hardly ever", index 2)
    answers = []
    for i in range(1, 10):
        qid = f"EPDS_Q{i:02d}"
        idx = 0 if qid in {"EPDS_Q01", "EPDS_Q02", "EPDS_Q04"} else 3
        answers.append({"question_id": qid, "selected_index": idx})

    # Q10 with index 2 ("Hardly ever" -> score 1)
    answers.append({"question_id": "EPDS_Q10", "selected_index": 2})

    response = client.post("/api/questionnaire/epds/submit", json={"answers": answers})
    assert response.status_code == 200
    res = response.json()

    # Total score is 1 (in the low risk range)
    assert res["total_score"] == 1
    assert res["classification"] == "Low likelihood of depressive illness"

    # BUT safety alert MUST BE TRIGGERED independently
    assert res["safety_alert"]["triggered"] is True
    assert res["safety_alert"]["question_10_score"] == 1
    assert res["safety_alert"]["severity"] == "URGENT_SAFETY_ASSESSMENT"
    assert "SAFETY ALERT" in res["safety_alert"]["message"]
    assert "NEVER be overridden" in res["safety_alert"]["override_protection"]


def test_submit_epds_missing_question_returns_422():
    """Incomplete questionnaire (9 items) must be rejected with HTTP 422."""
    answers = [{"question_id": f"EPDS_Q{i:02d}", "selected_index": 0} for i in range(1, 10)]
    response = client.post("/api/questionnaire/epds/submit", json={"answers": answers})
    assert response.status_code == 422


def test_submit_epds_invalid_index_returns_422():
    """Selected option index out of [0, 3] range must be rejected with HTTP 422."""
    answers = [{"question_id": f"EPDS_Q{i:02d}", "selected_index": 0} for i in range(1, 11)]
    answers[0]["selected_index"] = 4  # Invalid index (options are 0, 1, 2, 3)
    response = client.post("/api/questionnaire/epds/submit", json={"answers": answers})
    assert response.status_code == 422
    assert any("selected_index" in str(err) for err in response.json()["detail"])
