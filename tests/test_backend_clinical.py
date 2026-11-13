"""Backend API tests for Clinical Numerical ML screening service.

Verifies:
1. Successful model loading during application startup.
2. Successful clinical prediction via POST /api/clinical/predict.
3. Missing model artifact handling (HTTP 503).
4. Invalid / extra feature names rejection (HTTP 422).
5. Missing required features rejection (HTTP 422).
6. Supported missing values handling (None / null values correctly imputed).
7. Probability output format and range (0.0 <= p <= 1.0).
8. Risk category output correctness (HIGH_RISK, MODERATE_RISK, LOW_RISK).
9. Feature information endpoint GET /api/clinical/features.
10. Existing EPDS questionnaire endpoints remain functional.
11. Existing Text NER endpoint remains functional or returns expected status without regressions.
"""

from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.clinical_service import (
    ClinicalScreeningService,
    clinical_service,
    get_clinical_service,
)
from pipelines.clinical_numerical.config import (
    CATEGORICAL_FEATURES,
    EXCLUDED_COLUMNS,
    NUMERICAL_FEATURES,
    TOTAL_PREDICTOR_COUNT,
)


def _get_valid_clinical_features() -> Dict[str, Any]:
    """Return a complete dictionary of all 46 valid clinical survey features."""
    features: Dict[str, Any] = {
        # 2 Numerical
        "Age": 28.0,
        "Number of the latest pregnancy": 1.0,
        # 44 Categorical
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
    assert len(features) == TOTAL_PREDICTOR_COUNT == 46
    return features


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a TestClient with application lifespan active."""
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# 1. Successful model loading
# ---------------------------------------------------------------------------
def test_model_loading_at_startup(client: TestClient):
    """Verify that ClinicalNumericalPipeline is initialized and ready."""
    assert clinical_service.is_loaded is True
    assert clinical_service.model_name == "random_forest"
    assert clinical_service._pipeline is not None
    assert clinical_service._pipeline.is_ready is True


# ---------------------------------------------------------------------------
# 2. Successful clinical prediction
# ---------------------------------------------------------------------------
def test_successful_clinical_prediction(client: TestClient):
    """Verify POST /api/clinical/predict returns 200 with valid schema."""
    payload = {
        "mother_id": "test-mother-001",
        "features": _get_valid_clinical_features(),
    }
    response = client.post("/api/clinical/predict", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["mother_id"] == "test-mother-001"
    assert data["status"] == "completed"
    assert data["model_utilized"] == "random_forest"
    assert data["data_origin"] == "REAL_CLINICAL_SURVEY"
    assert "Research Prototype" in data["clinical_disclaimer"]

    prediction = data["prediction"]
    assert "predicted_risk_probability" in prediction
    assert "predicted_class" in prediction
    assert "risk_category" in prediction
    assert prediction["decision_threshold"] == 0.5


# ---------------------------------------------------------------------------
# 3. Missing model artifact (HTTP 503)
# ---------------------------------------------------------------------------
def test_missing_model_artifact_returns_503(client: TestClient):
    """Verify service returns HTTP 503 when the model pipeline cannot be loaded."""
    mock_unloaded_service = ClinicalScreeningService()
    mock_unloaded_service._pipeline = None
    mock_unloaded_service._load_error = "Mock missing artifact: models/clinical_numerical/random_forest.joblib not found"
    mock_unloaded_service._startup_attempted = True

    app.dependency_overrides[get_clinical_service] = lambda: mock_unloaded_service
    try:
        payload = {
            "mother_id": "test-mother-missing",
            "features": _get_valid_clinical_features(),
        }
        response = client.post("/api/clinical/predict", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "missing" in data["detail"].lower() or "unavailable" in data["detail"].lower()
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 4. Invalid feature names (HTTP 422)
# ---------------------------------------------------------------------------
def test_invalid_feature_names_rejected(client: TestClient):
    """Verify extra/unknown features and target column leakage are rejected with 422."""
    valid_features = _get_valid_clinical_features()

    # Case A: Unknown random field
    invalid_features = dict(valid_features)
    invalid_features["unknown_extra_feature"] = "invalid_value"
    response = client.post(
        "/api/clinical/predict",
        json={"mother_id": "test-mother-inv", "features": invalid_features},
    )
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("unknown_extra_feature" in str(err) for err in errors)

    # Case B: Excluded target column leakage (EPDS Score)
    leaked_features = dict(valid_features)
    leaked_features["EPDS Score"] = 18
    response = client.post(
        "/api/clinical/predict",
        json={"mother_id": "test-mother-leak", "features": leaked_features},
    )
    assert response.status_code == 422

    # Case C: Excluded raw target column leakage (EPDS_high_risk_screening_threshold)
    leaked_target = dict(valid_features)
    leaked_target["EPDS_high_risk_screening_threshold"] = 1
    response = client.post(
        "/api/clinical/predict",
        json={"mother_id": "test-mother-leak2", "features": leaked_target},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 5. Missing features (HTTP 422)
# ---------------------------------------------------------------------------
def test_missing_features_rejected(client: TestClient):
    """Verify omitting required features is rejected with 422 Unprocessable Entity."""
    # Only supply 2 out of 46 features
    incomplete_features = {
        "Age": 27.0,
        "Number of the latest pregnancy": 1.0,
    }
    response = client.post(
        "/api/clinical/predict",
        json={"mother_id": "test-mother-inc", "features": incomplete_features},
    )
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert len(errors) >= 44  # Missing 44 categorical features


# ---------------------------------------------------------------------------
# 6. Supported missing values (null / None imputed)
# ---------------------------------------------------------------------------
def test_supported_missing_values(client: TestClient):
    """Verify that null/None feature values are imputed by the preprocessor and yield 200."""
    features_with_nulls = _get_valid_clinical_features()
    # Set several numerical and categorical features to None
    features_with_nulls["Age"] = None
    features_with_nulls["Number of the latest pregnancy"] = None
    features_with_nulls["Residence"] = None
    features_with_nulls["Monthly income before latest pregnancy"] = None
    features_with_nulls["Addiction"] = None
    features_with_nulls["Relax/sleep when newborn is tended "] = None

    response = client.post(
        "/api/clinical/predict",
        json={"mother_id": "test-mother-nulls", "features": features_with_nulls},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "predicted_risk_probability" in data["prediction"]


# ---------------------------------------------------------------------------
# 7. Probability output format and range
# ---------------------------------------------------------------------------
def test_probability_output_range(client: TestClient):
    """Verify that predicted_risk_probability is a float within [0.0, 1.0]."""
    payload = {
        "mother_id": "test-mother-prob",
        "features": _get_valid_clinical_features(),
    }
    response = client.post("/api/clinical/predict", json=payload)
    assert response.status_code == 200
    prob = response.json()["prediction"]["predicted_risk_probability"]
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0


# ---------------------------------------------------------------------------
# 8. Risk category output validation
# ---------------------------------------------------------------------------
def test_risk_category_output(client: TestClient):
    """Verify risk_category is one of the standard clinical risk tiers."""
    payload = {
        "mother_id": "test-mother-cat",
        "features": _get_valid_clinical_features(),
    }
    response = client.post("/api/clinical/predict", json=payload)
    assert response.status_code == 200
    prediction = response.json()["prediction"]
    assert prediction["risk_category"] in {"HIGH_RISK", "MODERATE_RISK", "LOW_RISK"}
    assert prediction["predicted_class"] in {0, 1}


# ---------------------------------------------------------------------------
# 9. Feature information endpoint GET /api/clinical/features
# ---------------------------------------------------------------------------
def test_get_clinical_features_endpoint(client: TestClient):
    """Verify GET /api/clinical/features returns the authoritative 46 features."""
    response = client.get("/api/clinical/features")
    assert response.status_code == 200
    data = response.json()

    assert data["total_features"] == 46
    assert data["numerical_count"] == 2
    assert data["categorical_count"] == 44

    assert len(data["numerical_features"]) == 2
    assert "Age" in data["numerical_features"]
    assert "Number of the latest pregnancy" in data["numerical_features"]

    assert len(data["categorical_features"]) == 44
    assert "Residence" in data["categorical_features"]
    assert "Relax/sleep when newborn is tended " in data["categorical_features"]

    # Verify all 46 items in detailed feature list
    assert len(data["features"]) == 46
    for item in data["features"]:
        assert "name" in item
        assert item["feature_type"] in {"numerical", "categorical"}
        assert item["supports_missing_values"] is True

    # Verify prohibited features are listed
    assert len(data["prohibited_features"]) == len(EXCLUDED_COLUMNS)
    assert "EPDS Score" in data["prohibited_features"]
    assert "EPDS_high_risk_screening_threshold" in data["prohibited_features"]


# ---------------------------------------------------------------------------
# 10. Existing EPDS questionnaire endpoint still works
# ---------------------------------------------------------------------------
def test_existing_epds_endpoints_still_work(client: TestClient):
    """Verify GET and POST EPDS questionnaire endpoints are unaffected."""
    # GET /api/questionnaire/epds
    get_resp = client.get("/api/questionnaire/epds")
    assert get_resp.status_code == 200
    assert len(get_resp.json()["questions"]) == 10

    # POST /api/questionnaire/epds/submit
    submit_resp = client.post(
        "/api/questionnaire/epds/submit",
        json={
            "answers": [
                {"question_id": f"EPDS_Q{i:02d}", "selected_index": 0}
                for i in range(1, 11)
            ],
        },
    )
    assert submit_resp.status_code == 200
    assert "total_score" in submit_resp.json()


# ---------------------------------------------------------------------------
# 11. Existing Text NER endpoint still works or returns expected status
# ---------------------------------------------------------------------------
def test_existing_text_ner_endpoint_still_works(client: TestClient):
    """Verify POST /api/text-ner/extract is unaffected by clinical service addition."""
    response = client.post(
        "/api/text-ner/extract",
        json={"text": "Patient reports severe sadness and lack of sleep."},
    )
    # The Text NER endpoint may return 200 if its model is present, or 503 if not trained
    assert response.status_code in {200, 503}
    if response.status_code == 200:
        data = response.json()
        assert "entities" in data
        assert "text" in data

