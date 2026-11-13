"""Backend API tests for POST /api/screenings/analyze (Central Screening Orchestration).

Verifies:
1. Clinical-only screening workflow.
2. Text-only screening workflow with biomedical NER extraction.
3. Combined clinical and text multimodal screening.
4. Missing consent rejection (HTTP 400).
5. Invalid modalities rejection (HTTP 422).
6. Missing clinical features when clinical is requested (HTTP 422).
7. Invalid clinical features and target leakage rejection (HTTP 422).
8. Missing or empty text input when text is requested (HTTP 422).
9. Missing optional modalities handled cleanly.
10. Unimplemented audio and video modalities report status='unavailable'.
11. Individual modality failure preservation (partial completion).
12. All requested modalities failure reports status='failed'.
13. Mother existence validator interface validation.
14. Complete response contract schema verification.
15. Existing endpoints (clinical, EPDS, Text NER) remain operational without regressions.
"""

from datetime import datetime
import io
import json
from pathlib import Path
from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas.screening import ScreeningAnalysisResponse
from backend.services.clinical_service import ClinicalScreeningService, clinical_service
from backend.services.screening_service import (
    MotherValidator,
    ScreeningOrchestrationService,
    get_screening_service,
)
from backend.services.text_ner_service import TextNERService, text_ner_service
from pipelines.text_ner.features import (
    align_spans_to_bio,
    extract_document_features,
    tokenize_with_offsets,
)
from pipelines.text_ner.inference import TextNERPredictor
from pipelines.text_ner.models import TextNERModel
from pipelines.text_ner.parser import Document, EntitySpan


def _get_valid_clinical_features() -> Dict[str, Any]:
    """Return complete valid 46-feature survey dictionary."""
    return {
        "Age": 28.0,
        "Number of the latest pregnancy": 1.0,
        "Residence": "Urban",
        "Education Level": "Graduate",
        "Marital status": "Married",
        "Occupation before latest pregnancy": "Employed",
        "Monthly income before latest pregnancy": "30000-50000",
        "Occupation After Your Latest Childbirth": "Homemaker",
        "Current monthly income": "30000-50000",
        "Husband's education level": "Graduate",
        "Husband’s monthly income": "40000-60000",
        "Addiction": "No",
        "Total children": 1,
        "Disease before pregnancy": "None",
        "History of pregnancy loss": "No",
        "Family type": "Nuclear",
        "Number of household members": 3,
        "Relationship with the in-laws": "Good",
        "Relationship with husband": "Good",
        "Relationship with the newborn": "Good",
        "Relationship between father and newborn": "Good",
        "Feeling about motherhood": "Happy",
        "Recieved Support": "Yes",
        "Need for Support": "No",
        "Major changes or losses during pregnancy": "No",
        "Abuse": "No",
        "Trust and share feelings": "Yes",
        "Pregnancy length": "Full term",
        "Pregnancy plan": "Planned",
        "Regular checkups": "Yes",
        "Fear of pregnancy": "No",
        "Diseases during pregnancy": "None",
        "Age of newborn": "1-3 months",
        "Age of immediate older children": "None",
        "Mode of delivery": "Normal",
        "Gender of newborn": "Female",
        "Birth compliancy": "Normal",
        "Breastfeed": "Yes",
        "Newborn illness": "No",
        "Worry about newborn": "No",
        "Relax/sleep when newborn is tended ": "Yes",
        "Relax/sleep when the newborn is asleep": "Yes",
        "Angry after latest child birth": "No",
        "Feeling for regular activities": "Normal",
        "Depression before pregnancy (PHQ2)": "No",
        "Depression during pregnancy (PHQ2)": "No",
    }


def _create_fast_test_ner_service(tmp_path: Path) -> TextNERService:
    """Build a functional TextNERService using a tiny deterministic model."""
    samples = [
        ("Severe postpartum depression and anxiety symptoms daily.", ["postpartum depression", "anxiety"]),
        ("Doctor discussed therapy and support for mood changes.", ["therapy"]),
    ]
    X_dicts, y_tags = [], []
    for idx, (text, kws) in enumerate(samples):
        spans = [
            EntitySpan(
                id=f"T{idx}_{text.index(kw)}",
                label="MMLite",
                start=text.index(kw),
                end=text.index(kw) + len(kw),
                text=kw,
            )
            for kw in kws
        ]
        doc = Document(id=f"test_{idx}", group="Test", text=text, spans=spans)
        tokens = tokenize_with_offsets(doc.text)
        X_dicts.extend(extract_document_features(tokens))
        y_tags.extend(align_spans_to_bio(tokens, doc.spans))

    model = TextNERModel(classifier_type="sgd", loss="modified_huber", max_iter=100, random_state=42)
    model.fit(X_dicts, y_tags)
    ckpt = tmp_path / "tiny_ner.joblib"
    model.save(ckpt)
    predictor = TextNERPredictor(model_path=ckpt)
    return TextNERService(predictor=predictor)


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a TestClient with application lifespan active."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def active_text_ner_service(tmp_path: Path) -> TextNERService:
    """Provide a working TextNERService for tests requiring text entity extraction."""
    return _create_fast_test_ner_service(tmp_path)


# ---------------------------------------------------------------------------
# 1. Clinical-Only Screening
# ---------------------------------------------------------------------------
def test_clinical_only_screening(client: TestClient):
    """Verify screening analysis requesting only the clinical numerical modality."""
    payload = {
        "motherId": "M-101",
        "modalities": json.dumps({"clinical": True, "text": False, "audio": False, "video": False}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    response = client.post("/api/screenings/analyze", data=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["mother_id"] == "M-101"
    assert data["status"] == "completed"
    assert "screening_id" in data

    # Clinical modality is completed
    clinical = data["clinical"]
    assert clinical["status"] == "completed"
    assert clinical["model_version"] == "random_forest"
    assert "predicted_risk_probability" in clinical["prediction"]
    assert clinical["prediction"]["risk_category"] in {"HIGH_RISK", "MODERATE_RISK", "LOW_RISK"}

    # Other modalities are not_requested
    assert data["text"]["status"] == "not_requested"
    assert data["audio"]["status"] == "not_requested"
    assert data["video"]["status"] == "not_requested"
    assert data["fusion"]["status"] == "not_available"


# ---------------------------------------------------------------------------
# 2. Text-Only Screening
# ---------------------------------------------------------------------------
def test_text_only_screening_with_file_upload(
    client: TestClient,
    active_text_ner_service: TextNERService,
):
    """Verify screening analysis requesting only the biomedical text NER modality via file upload."""
    orchestrator = ScreeningOrchestrationService(
        clinical_svc=clinical_service,
        text_svc=active_text_ner_service,
    )
    app.dependency_overrides[get_screening_service] = lambda: orchestrator
    try:
        text_content = b"Patient exhibits marked postpartum depression and constant anxiety after delivery."
        files = {
            "files_text": ("narrative.txt", io.BytesIO(text_content), "text/plain"),
        }
        data = {
            "motherId": "M-102",
            "modalities": json.dumps(["text"]),
            "consentConfirmed": "true",
            "eligibilityConfirmed": "true",
        }
        response = client.post("/api/screenings/analyze", data=data, files=files)
        assert response.status_code == 200

        res = response.json()
        assert res["mother_id"] == "M-102"
        assert res["status"] == "completed"

        text_res = res["text"]
        assert text_res["status"] == "completed"
        assert text_res["processing_type"] == "biomedical_ner"
        assert isinstance(text_res["entities"], list)
        assert text_res["processed_character_count"] > 0

        # Clinical was not requested
        assert res["clinical"]["status"] == "not_requested"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 3. Clinical and Text Together
# ---------------------------------------------------------------------------
def test_clinical_and_text_together(
    client: TestClient,
    active_text_ner_service: TextNERService,
):
    """Verify multimodal analysis requesting both clinical numerical and text NER modalities."""
    orchestrator = ScreeningOrchestrationService(
        clinical_svc=clinical_service,
        text_svc=active_text_ner_service,
    )
    app.dependency_overrides[get_screening_service] = lambda: orchestrator
    try:
        data = {
            "motherId": "M-103",
            "modalities": json.dumps({"clinical": True, "text": True}),
            "consentConfirmed": "true",
            "eligibilityConfirmed": "true",
            "clinical_features": json.dumps(_get_valid_clinical_features()),
            "text_content": "Mother reported persistent postpartum depression symptoms during clinical intake.",
        }
        response = client.post("/api/screenings/analyze", data=data)
        assert response.status_code == 200

        res = response.json()
        assert res["status"] == "completed"
        assert res["clinical"]["status"] == "completed"
        assert res["text"]["status"] == "completed"
        assert res["audio"]["status"] == "not_requested"
        assert res["video"]["status"] == "not_requested"
        assert res["fusion"]["status"] == "not_available"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 4. Missing Consent Rejection
# ---------------------------------------------------------------------------
def test_missing_consent_rejected(client: TestClient):
    """Verify that omitting or setting consentConfirmed to false returns HTTP 400."""
    # Case A: consentConfirmed is false
    data = {
        "motherId": "M-104",
        "modalities": json.dumps({"clinical": True}),
        "consentConfirmed": "false",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    response = client.post("/api/screenings/analyze", data=data)
    assert response.status_code == 400
    assert "consent" in response.json()["detail"].lower()

    # Case B: consentConfirmed is omitted
    data_no_consent = {
        "motherId": "M-104",
        "modalities": json.dumps({"clinical": True}),
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    response2 = client.post("/api/screenings/analyze", data=data_no_consent)
    assert response2.status_code == 400


def test_unconfirmed_eligibility_rejected(client: TestClient):
    """Verify that omitting or setting eligibilityConfirmed to false returns HTTP 403."""
    # Case A: eligibilityConfirmed is explicitly false
    data_false = {
        "motherId": "M-104",
        "modalities": json.dumps({"clinical": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "false",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    resp1 = client.post("/api/screenings/analyze", data=data_false)
    assert resp1.status_code == 403
    assert "eligibility confirmation is required" in resp1.json()["detail"].lower()

    # Case B: eligibilityConfirmed is omitted/missing (cannot bypass the gate)
    data_missing = {
        "motherId": "M-104",
        "modalities": json.dumps({"clinical": True}),
        "consentConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    resp2 = client.post("/api/screenings/analyze", data=data_missing)
    assert resp2.status_code == 403
    assert "eligibility confirmation is required" in resp2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 5. Invalid Modalities Rejection
# ---------------------------------------------------------------------------
def test_invalid_modalities_rejected(client: TestClient):
    """Verify malformed modalities JSON or empty modalities selection returns HTTP 422."""
    # Case A: Malformed JSON string
    response = client.post(
        "/api/screenings/analyze",
        data={"motherId": "M-105", "consentConfirmed": "true", "eligibilityConfirmed": "true", "modalities": "not-valid-json"},
    )
    assert response.status_code == 422

    # Case B: All modalities false (no modality requested)
    response2 = client.post(
        "/api/screenings/analyze",
        data={
            "motherId": "M-105",
            "consentConfirmed": "true",
            "eligibilityConfirmed": "true",
            "modalities": json.dumps({"clinical": False, "text": False, "audio": False, "video": False}),
        },
    )
    assert response2.status_code == 422
    assert "at least one" in response2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. Missing Clinical Features
# ---------------------------------------------------------------------------
def test_missing_clinical_features_rejected(client: TestClient):
    """Verify that requesting clinical modality without clinical_features returns HTTP 422."""
    data = {
        "motherId": "M-106",
        "modalities": json.dumps({"clinical": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
    }
    response = client.post("/api/screenings/analyze", data=data)
    assert response.status_code == 422
    assert "clinical_features" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 7. Invalid Clinical Features & Target Leakage
# ---------------------------------------------------------------------------
def test_invalid_clinical_features_rejected(client: TestClient):
    """Verify incomplete feature dictionaries or target leakage columns return HTTP 422."""
    # Case A: Missing required features (only 2 provided)
    data_incomplete = {
        "motherId": "M-107",
        "modalities": json.dumps({"clinical": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps({"Age": 28.0, "Number of the latest pregnancy": 1.0}),
    }
    resp = client.post("/api/screenings/analyze", data=data_incomplete)
    assert resp.status_code == 422

    # Case B: Target column leakage (EPDS Score)
    leaked = _get_valid_clinical_features()
    leaked["EPDS Score"] = 14
    data_leaked = {
        "motherId": "M-107",
        "modalities": json.dumps({"clinical": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(leaked),
    }
    resp_leak = client.post("/api/screenings/analyze", data=data_leaked)
    assert resp_leak.status_code == 422


# ---------------------------------------------------------------------------
# 8. Invalid Text Input
# ---------------------------------------------------------------------------
def test_invalid_text_input_rejected(client: TestClient):
    """Verify requesting text modality without any text content returns HTTP 422."""
    data = {
        "motherId": "M-108",
        "modalities": json.dumps({"text": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
    }
    response = client.post("/api/screenings/analyze", data=data)
    assert response.status_code == 422
    assert "text narrative content" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 9. Missing Optional Modalities
# ---------------------------------------------------------------------------
def test_missing_optional_modalities_accepted(client: TestClient):
    """Verify omitting optional modalities (audio, video, text) processes without failure."""
    data = {
        "motherId": "M-109",
        "modalities": json.dumps(["clinical"]),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    response = client.post("/api/screenings/analyze", data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "completed"
    assert res["clinical"]["status"] == "completed"
    assert res["text"]["status"] == "not_requested"
    assert res["audio"]["status"] == "not_requested"
    assert res["video"]["status"] == "not_requested"


# ---------------------------------------------------------------------------
# 10. Unavailable Audio & Video Modalities
# ---------------------------------------------------------------------------
def test_unavailable_audio_and_video_modalities(client: TestClient):
    """Verify requesting audio or video correctly marks them unavailable and yields partially_completed."""
    data = {
        "motherId": "M-110",
        "modalities": json.dumps({"clinical": True, "audio": True, "video": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    response = client.post("/api/screenings/analyze", data=data)
    assert response.status_code == 200

    res = response.json()
    assert res["status"] == "partially_completed"
    assert res["clinical"]["status"] == "completed"
    assert res["audio"]["status"] == "unavailable"
    assert res["video"]["status"] == "unavailable"
    assert res["fusion"]["status"] == "not_available"


# ---------------------------------------------------------------------------
# 11. Individual Modality Failure Preservation
# ---------------------------------------------------------------------------
def test_individual_modality_failure_preserves_successful_results(client: TestClient):
    """Verify that when one requested modality fails, other modality outputs are preserved."""
    # Create mock text service that fails with an inference error
    class FailingTextService(TextNERService):
        def extract_entities(self, text: str):
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Mocked text model failure")

    mock_svc = ScreeningOrchestrationService(
        clinical_svc=clinical_service,
        text_svc=FailingTextService(),
    )
    app.dependency_overrides[get_screening_service] = lambda: mock_svc
    try:
        data = {
            "motherId": "M-111",
            "modalities": json.dumps({"clinical": True, "text": True}),
            "consentConfirmed": "true",
            "eligibilityConfirmed": "true",
            "clinical_features": json.dumps(_get_valid_clinical_features()),
            "text_content": "Patient narrative input",
        }
        response = client.post("/api/screenings/analyze", data=data)
        assert response.status_code == 200

        res = response.json()
        assert res["status"] == "partially_completed"
        # Clinical succeeded and is preserved
        assert res["clinical"]["status"] == "completed"
        assert res["clinical"]["prediction"] is not None
        # Text failed and is reported
        assert res["text"]["status"] == "failed"
        assert "Mocked text model failure" in res["text"]["error"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 12. All Requested Modalities Fail
# ---------------------------------------------------------------------------
def test_all_requested_modalities_fail_status(client: TestClient):
    """Verify that if all requested modalities fail or are unavailable, overall status is 'failed'."""
    data = {
        "motherId": "M-112",
        "modalities": json.dumps({"audio": True, "video": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
    }
    response = client.post("/api/screenings/analyze", data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "failed"
    assert res["audio"]["status"] == "unavailable"
    assert res["video"]["status"] == "unavailable"


# ---------------------------------------------------------------------------
# 13. Mother Existence Validator Interface
# ---------------------------------------------------------------------------
def test_mother_existence_validator(client: TestClient):
    """Verify that MotherValidator interface rejects unregistered mothers with HTTP 404."""
    class MockRegistryValidator(MotherValidator):
        def validate_mother_exists(self, mother_id: str) -> bool:
            return mother_id in {"KNOWN-M-01", "KNOWN-M-02"}

    custom_orchestrator = ScreeningOrchestrationService(
        clinical_svc=clinical_service,
        text_svc=text_ner_service,
        mother_val=MockRegistryValidator(),
    )
    app.dependency_overrides[get_screening_service] = lambda: custom_orchestrator
    try:
        data = {
            "motherId": "UNREGISTERED-M-99",
            "modalities": json.dumps(["clinical"]),
            "consentConfirmed": "true",
            "eligibilityConfirmed": "true",
            "clinical_features": json.dumps(_get_valid_clinical_features()),
        }
        response = client.post("/api/screenings/analyze", data=data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 14. Response Contract Schema Validation
# ---------------------------------------------------------------------------
def test_response_contract_schema(client: TestClient):
    """Verify that response validates strictly against ScreeningAnalysisResponse schema."""
    data = {
        "motherId": "M-114",
        "modalities": json.dumps({"clinical": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    response = client.post("/api/screenings/analyze", data=data)
    assert response.status_code == 200

    # Parse and validate with Pydantic model
    validated = ScreeningAnalysisResponse.model_validate(response.json())
    assert validated.mother_id == "M-114"
    assert validated.status == "completed"
    assert validated.clinical.status == "completed"
    assert validated.fusion.status == "not_available"
    # Ensure processed_at is valid ISO timestamp
    dt = datetime.fromisoformat(validated.processed_at)
    assert dt is not None


# ---------------------------------------------------------------------------
# 15. Regression Check on Existing Endpoints
# ---------------------------------------------------------------------------
def test_existing_endpoints_regression(client: TestClient):
    """Ensure clinical predict, feature info, EPDS, and Text NER endpoints remain unaffected."""
    # Clinical Predict
    resp_clin = client.post(
        "/api/clinical/predict",
        json={"mother_id": "M-REG", "features": _get_valid_clinical_features()},
    )
    assert resp_clin.status_code == 200

    # Clinical Features
    resp_feat = client.get("/api/clinical/features")
    assert resp_feat.status_code == 200
    assert resp_feat.json()["total_features"] == 46

    # EPDS Questionnaire GET
    resp_epds = client.get("/api/questionnaire/epds")
    assert resp_epds.status_code == 200

    # EPDS Questionnaire Submit
    resp_epds_sub = client.post(
        "/api/questionnaire/epds/submit",
        json={"answers": [{"question_id": f"EPDS_Q{i:02d}", "selected_index": 0} for i in range(1, 11)]},
    )
    assert resp_epds_sub.status_code == 200
    assert "total_score" in resp_epds_sub.json()

    # Text NER
    resp_ner = client.post(
        "/api/text-ner/extract",
        json={"text": "Patient reports insomnia and depression."},
    )
    assert resp_ner.status_code in {200, 503}

