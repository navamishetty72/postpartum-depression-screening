"""Phase 5 ML Backend Hardening & Member 2 Integration Verification Tests.

Validates:
1. Mother existence validation dependency override interface for Member 2 database integration.
2. Strict independence of EPDS Question 10 safety alert (cannot be overridden by ML probabilities).
3. Privacy preservation: raw narratives, audio bytes, and patient survey records are never logged.
4. Default fusion engine has no active strategy by default (no fabricated scores).
5. Configurable discordance threshold behavior and insufficient data contract.
6. Text NER confidence is strictly rejected as a PPD risk probability.
7. Missing/unavailable modalities are never treated as negative clinical findings.
8. Complete response persistence contract readiness for Member 2 database models.
9. Error sanitization (no stack traces or internal parameters leaked in responses).
"""

import io
import json
import logging
from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.ml.fusion_engine import (
    DiscordanceAnalyzer,
    FusionStatus,
    ModalityCandidate,
    MultimodalFusionEngine,
    WeightedAverageFusionStrategy,
    fusion_engine,
)
from backend.schemas.screening import ScreeningAnalysisResponse
from backend.services.screening_service import (
    MotherValidator,
    get_mother_validator,
)
from tests.test_backend_screening import _get_valid_clinical_features


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create TestClient with application lifespan active."""
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# 1. Member 2 Mother Validator Dependency Override Interface
# ---------------------------------------------------------------------------
def test_member2_mother_validator_dependency_override(client: TestClient):
    """Verify Member 2 can plug in their SQL database validator via get_mother_validator override."""
    class Member2SQLDatabaseMotherValidator(MotherValidator):
        def __init__(self, registered_ids):
            self.registered_ids = set(registered_ids)

        def validate_mother_exists(self, mother_id: str) -> bool:
            # Simulates Member 2's session.query(Mother).filter_by(id=mother_id).first() is not None
            return mother_id in self.registered_ids

    mock_db_validator = Member2SQLDatabaseMotherValidator(registered_ids=["M-REGISTERED-01", "M-REGISTERED-02"])

    # Member 2 connects via app.dependency_overrides
    app.dependency_overrides[get_mother_validator] = lambda: mock_db_validator
    try:
        # Case A: Unregistered mother returns HTTP 404
        payload_unregistered = {
            "motherId": "M-GHOST-99",
            "modalities": json.dumps({"clinical": True}),
            "consentConfirmed": "true",
            "clinical_features": json.dumps(_get_valid_clinical_features()),
        }
        resp_404 = client.post("/api/screenings/analyze", data=payload_unregistered)
        assert resp_404.status_code == 404
        assert "not found" in resp_404.json()["detail"].lower()

        # Case B: Registered mother returns HTTP 200
        payload_registered = {
            "motherId": "M-REGISTERED-01",
            "modalities": json.dumps({"clinical": True}),
            "consentConfirmed": "true",
            "eligibilityConfirmed": "true",
            "clinical_features": json.dumps(_get_valid_clinical_features()),
        }
        resp_200 = client.post("/api/screenings/analyze", data=payload_registered)
        assert resp_200.status_code == 200
        assert resp_200.json()["mother_id"] == "M-REGISTERED-01"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 2. Strict Independence of EPDS Question 10 Safety Escalation
# ---------------------------------------------------------------------------
def test_q10_safety_escalation_independence(client: TestClient):
    """Verify that a positive Question 10 response triggers an urgent safety alert that ML cannot override."""
    # Answers where Q1-Q9 are 0 points, but Q10 has thoughts of self-harm (score=1)
    answers = []
    for i in range(1, 10):
        qid = f"EPDS_Q{i:02d}"
        idx = 0 if qid in {"EPDS_Q01", "EPDS_Q02", "EPDS_Q04"} else 3
        answers.append({"question_id": qid, "selected_index": idx})
    # Q10 reverse scored: index 2 corresponds to score 1
    answers.append({"question_id": "EPDS_Q10", "selected_index": 2})

    response = client.post("/api/questionnaire/epds/submit", json={"answers": answers})
    assert response.status_code == 200
    res = response.json()

    # Total score is very low (score = 1)
    assert res["total_score"] == 1
    # BUT safety alert is strictly triggered
    assert res["safety_alert"]["triggered"] is True
    assert res["safety_alert"]["severity"] == "URGENT_SAFETY_ASSESSMENT"
    assert res["safety_alert"]["question_10_score"] == 1
    assert "never be overridden" in res["safety_alert"]["override_protection"].lower()
    assert len(res["safety_alert"]["escalation_protocol"]) > 0


# ---------------------------------------------------------------------------
# 3. Privacy Preservation: No PII Logging
# ---------------------------------------------------------------------------
def test_privacy_no_pii_logging(client: TestClient, caplog: pytest.LogCaptureFixture):
    """Verify application loggers do not leak raw text narratives, features, or patient answers."""
    caplog.set_level(logging.DEBUG)

    sensitive_narrative = "CONFIDENTIAL_PATIENT_NARRATIVE: I feel overwhelming despair every night alone."
    valid_features = _get_valid_clinical_features()

    payload = {
        "motherId": "M-PRIVACY-TEST",
        "modalities": json.dumps({"clinical": True, "text": True}),
        "consentConfirmed": "true",
        "clinical_features": json.dumps(valid_features),
        "text_content": sensitive_narrative,
    }
    client.post("/api/screenings/analyze", data=payload)

    # Check that neither the sensitive narrative nor raw feature JSON appears in logged messages
    logged_text = caplog.text
    assert sensitive_narrative not in logged_text
    assert "CONFIDENTIAL_PATIENT_NARRATIVE" not in logged_text
    # Verify exact feature values aren't dumped as raw dictionary strings
    assert "Occupation before latest pregnancy" not in logged_text or "Employed" not in logged_text


# ---------------------------------------------------------------------------
# 4. Default Fusion Engine Has No Active Strategy
# ---------------------------------------------------------------------------
def test_default_fusion_engine_has_no_active_strategy():
    """Verify that global fusion_engine has strategy=None by default, preventing unvalidated fusion."""
    assert fusion_engine.strategy is None
    # Evaluating returns status='not_available'
    clinical_mock = {
        "status": "completed",
        "prediction": {"predicted_risk_probability": 0.85},
    }
    res = fusion_engine.evaluate(clinical=clinical_mock)
    assert res.status == FusionStatus.NOT_AVAILABLE.value
    assert res.combined_score is None


# ---------------------------------------------------------------------------
# 5. Configurable Discordance Threshold & Insufficient Data Contract
# ---------------------------------------------------------------------------
def test_discordance_threshold_configurable_and_contract():
    """Verify DiscordanceAnalyzer threshold is configurable and documentation specifies research-only status."""
    analyzer_strict = DiscordanceAnalyzer(threshold=0.10)
    assert analyzer_strict.threshold == 0.10

    analyzer_permissive = DiscordanceAnalyzer(threshold=0.50)
    assert analyzer_permissive.threshold == 0.50

    # With only 1 candidate, returns exact contract
    single_cand = ModalityCandidate(modality="clinical", status="completed", probability=0.8, is_predictive=True)
    report = analyzer_strict.analyze([single_cand])
    assert report.discordance_detected is False
    assert report.comparison == []
    assert report.explanation == "Insufficient comparable modality predictions."


# ---------------------------------------------------------------------------
# 6. Text NER Confidence Strictly Not Treated as PPD Risk Probability
# ---------------------------------------------------------------------------
def test_text_ner_confidence_never_treated_as_ppd_probability():
    """Verify Text NER entity extraction confidence is strictly rejected as a PPD probability."""
    engine = MultimodalFusionEngine()
    text_payload = {
        "status": "completed",
        "processing_type": "biomedical_ner",
        "entities": [
            {"text": "depression", "label": "MMLite", "confidence": 0.9999},
        ],
        "total_entities_detected": 1,
    }
    candidate = engine.extract_candidate("text", text_payload)
    assert candidate.is_predictive is False
    assert candidate.probability is None


# ---------------------------------------------------------------------------
# 7. Missing Modalities Never Treated as Negative Findings
# ---------------------------------------------------------------------------
def test_missing_modalities_never_treated_as_negative_findings():
    """Verify missing, failed, or unavailable modalities are never defaulted to probability=0.0."""
    engine = MultimodalFusionEngine()

    cand_missing = engine.extract_candidate("audio", None)
    assert cand_missing.status == "not_requested"
    assert cand_missing.probability is None
    assert cand_missing.is_predictive is False

    cand_unavail = engine.extract_candidate("video", {"status": "unavailable"})
    assert cand_unavail.status == "unavailable"
    assert cand_unavail.probability is None
    assert cand_unavail.is_predictive is False


# ---------------------------------------------------------------------------
# 8. Response Contract Readiness for Member 2 Persistence
# ---------------------------------------------------------------------------
def test_response_fields_contract_for_member2_persistence(client: TestClient):
    """Verify that response returned by POST /api/screenings/analyze contains all expected fields."""
    payload = {
        "motherId": "M-PERSIST-TEST",
        "modalities": json.dumps(["clinical"]),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    response = client.post("/api/screenings/analyze", data=payload)
    assert response.status_code == 200

    data = response.json()
    # Fields needed by Member 2 for relational SQL persistence:
    assert "screening_id" in data
    assert "mother_id" in data
    assert data["status"] in {"completed", "partially_completed", "failed"}
    assert "clinical" in data
    assert "text" in data
    assert "audio" in data
    assert "video" in data
    assert "fusion" in data
    assert "processed_at" in data

    # Validate against strict Pydantic model
    validated = ScreeningAnalysisResponse.model_validate(data)
    assert validated.mother_id == "M-PERSIST-TEST"


# ---------------------------------------------------------------------------
# 9. Error Sanitization (No Model Internals Leaked)
# ---------------------------------------------------------------------------
def test_error_handling_sanitization(client: TestClient):
    """Verify that malformed requests return standard HTTP error details without leaking internal tracebacks."""
    # Bad modalities parameter
    response = client.post(
        "/api/screenings/analyze",
        data={"motherId": "M-ERR", "consentConfirmed": "true", "modalities": "{"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # Ensure raw Python stack traces are not exposed
    assert "Traceback (most recent call last)" not in str(data)
    assert "File \"" not in str(data)


# ---------------------------------------------------------------------------
# 10. Eligibility Gate Contract & Dependency Override
# ---------------------------------------------------------------------------
def test_eligibility_gate_contract_and_dependency_override(client: TestClient):
    """Verify strict self-declared eligibility gate contract, precedence over 422, and override capability."""
    from backend.services.screening_service import EligibilityValidator, get_eligibility_validator

    valid_payload = {
        "motherId": "M-ELIG-TEST-01",
        "modalities": json.dumps({"clinical": True}),
        "consentConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }

    # Case A: Missing eligibility returns HTTP 403
    resp_missing = client.post("/api/screenings/analyze", data=valid_payload)
    assert resp_missing.status_code == 403
    assert "eligibility confirmation is required" in resp_missing.json()["detail"].lower()

    # Case B: False eligibility returns HTTP 403
    payload_false = {**valid_payload, "eligibilityConfirmed": "false"}
    resp_false = client.post("/api/screenings/analyze", data=payload_false)
    assert resp_false.status_code == 403
    assert "eligibility confirmation is required" in resp_false.json()["detail"].lower()

    # Case C: True eligibility returns HTTP 200
    payload_true = {**valid_payload, "eligibilityConfirmed": "true"}
    resp_true = client.post("/api/screenings/analyze", data=payload_true)
    assert resp_true.status_code == 200
    assert resp_true.json()["status"] == "completed"

    # Case D: Malformed request syntax returns HTTP 422 even if eligibility is missing
    resp_syntax_err = client.post(
        "/api/screenings/analyze",
        data={"motherId": "M-SYNTAX", "consentConfirmed": "true", "modalities": "{"},
    )
    assert resp_syntax_err.status_code == 422

    # Case E: EligibilityValidator dependency override
    class MockPermissiveEligibilityValidator(EligibilityValidator):
        def validate_eligibility(self, eligibility_confirmed):
            return True

    app.dependency_overrides[get_eligibility_validator] = lambda: MockPermissiveEligibilityValidator()
    try:
        # Request without eligibilityConfirmed now succeeds through the custom override
        resp_override = client.post("/api/screenings/analyze", data=valid_payload)
        assert resp_override.status_code == 200
    finally:
        app.dependency_overrides.clear()

