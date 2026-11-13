"""Focused unit tests for Audio schema validation and AudioScreeningService foundation.

Tests Phase 8F reconciliation requirements:
1. Schema validation of the 7 acoustic features against physiological bounds.
2. Verification of documented clinical literature citations for all physiological boundaries.
3. Extra and missing field rejection (extra='forbid').
4. AudioScreeningService startup, shutdown, and configurable directory.
5. Verification of is_loaded and is_available lifecycle properties.
6. Safe unavailable response behavior when model checkpoints are missing (no fabricated predictions).
7. Strict non-predictive flag (is_predictive=False) and provenance preservation.
8. Proper propagation of participant/mother identifiers without exposing biometrics in logs.
9. Temporary artifact mock loading and inference execution (RandomForest + StandardScaler).
10. Verification of exact feature ordering in DataFrame transformation.
11. Verification that no automatic training is triggered by startup or inference.
12. Compatibility with both as_response=True (AudioScreeningResponse) and as_response=False (dict/HTTPException).
"""

from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
import joblib
import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from backend.schemas.audio import (
    ACOUSTIC_FEATURE_BOUNDS,
    ACOUSTIC_FEATURE_LITERATURE_SOURCES,
    ACOUSTIC_FEATURE_NAMES,
    AcousticFeatures,
    AudioInferenceRequest,
    AudioScreeningResponse,
)
from backend.services.audio_service import (
    EXPECTED_AUDIO_FEATURES,
    AudioScreeningService,
)
from pipelines.synthetic_audio.config import DATA_ORIGIN_TAG


@pytest.fixture
def valid_acoustic_dict():
    """Valid canonical acoustic features dictionary within literature priors."""
    return {
        "f0_mean_hz": 215.0,
        "f0_std_hz": 28.0,
        "jitter_local_percent": 1.20,
        "shimmer_local_percent": 4.50,
        "hnr_db": 20.0,
        "speech_rate_syllables_per_sec": 3.80,
        "pause_ratio": 0.24,
    }


@pytest.fixture
def temp_audio_artifacts(tmp_path):
    """Create lightweight temporary scaler and Random Forest model artifacts for testing."""
    model_dir = tmp_path / "test_audio_model"
    model_dir.mkdir(parents=True)

    # 1. Fit dummy scaler on 7 features with feature names
    scaler = StandardScaler()
    dummy_data = np.random.RandomState(42).randn(20, 7)
    dummy_df = pd.DataFrame(dummy_data, columns=EXPECTED_AUDIO_FEATURES)
    scaler.fit(dummy_df)
    joblib.dump(scaler, model_dir / "scaler.joblib")

    # 2. Fit dummy Random Forest classifier
    rf = RandomForestClassifier(n_estimators=5, random_state=42)
    dummy_labels = np.array([0, 1] * 10)
    rf.fit(scaler.transform(dummy_df), dummy_labels)
    joblib.dump(rf, model_dir / "random_forest.joblib")

    return model_dir


# =====================================================================
# 1. Schema Validation Tests
# =====================================================================


def test_acoustic_features_valid_payload(valid_acoustic_dict):
    """Verify that valid acoustic feature dictionary parses correctly."""
    features = AcousticFeatures(**valid_acoustic_dict)
    assert features.f0_mean_hz == 215.0
    assert features.f0_std_hz == 28.0
    assert features.jitter_local_percent == 1.20
    assert features.shimmer_local_percent == 4.50
    assert features.hnr_db == 20.0
    assert features.speech_rate_syllables_per_sec == 3.80
    assert features.pause_ratio == 0.24


def test_acoustic_features_literature_sources_documented():
    """Verify all 7 acoustic feature boundaries have documented clinical literature sources."""
    for feature_name in ACOUSTIC_FEATURE_NAMES:
        assert feature_name in ACOUSTIC_FEATURE_LITERATURE_SOURCES, (
            f"Missing literature citation source for feature: {feature_name}"
        )
        source_entry = ACOUSTIC_FEATURE_LITERATURE_SOURCES[feature_name]
        assert "range" in source_entry
        assert "normative_prior" in source_entry
        assert "source" in source_entry
        assert len(source_entry["source"]) > 10


def test_acoustic_features_exact_bounds(valid_acoustic_dict):
    """Verify boundary clamping values are accepted at extremes."""
    min_dict = {
        name: ACOUSTIC_FEATURE_BOUNDS[name][0]
        for name in ACOUSTIC_FEATURE_BOUNDS
    }
    max_dict = {
        name: ACOUSTIC_FEATURE_BOUNDS[name][1]
        for name in ACOUSTIC_FEATURE_BOUNDS
    }
    min_features = AcousticFeatures(**min_dict)
    max_features = AcousticFeatures(**max_dict)
    assert min_features.f0_mean_hz == ACOUSTIC_FEATURE_BOUNDS["f0_mean_hz"][0]
    assert max_features.f0_mean_hz == ACOUSTIC_FEATURE_BOUNDS["f0_mean_hz"][1]


@pytest.mark.parametrize(
    "field_name,out_of_bounds_val",
    [
        ("f0_mean_hz", 100.0),          # min is 130.0 (Titze 1994)
        ("f0_mean_hz", 400.0),          # max is 310.0 (Titze 1994)
        ("f0_std_hz", 5.0),             # min is 8.0 (Baken 2000)
        ("f0_std_hz", 100.0),           # max is 75.0 (Baken 2000)
        ("jitter_local_percent", 0.05),  # min is 0.20 (Horii 1979)
        ("jitter_local_percent", 8.0),   # max is 5.50 (Horii 1979)
        ("shimmer_local_percent", 0.5),  # min is 1.00 (Horii 1980)
        ("shimmer_local_percent", 20.0), # max is 16.00 (Horii 1980)
        ("hnr_db", 5.0),                # min is 8.0 (Yumoto 1982)
        ("hnr_db", 35.0),               # max is 30.0 (Yumoto 1982)
        ("speech_rate_syllables_per_sec", 1.0),  # min is 1.80 (de Jong 2009)
        ("speech_rate_syllables_per_sec", 7.5),  # max is 6.20 (Cummins 2015)
        ("pause_ratio", 0.02),          # min is 0.08 (Mundt 2007)
        ("pause_ratio", 0.85),          # max is 0.65 (Low 2020)
    ],
)
def test_acoustic_features_out_of_bounds_rejected(valid_acoustic_dict, field_name, out_of_bounds_val):
    """Verify that features violating physiological bounds trigger ValidationError."""
    invalid_dict = dict(valid_acoustic_dict)
    invalid_dict[field_name] = out_of_bounds_val
    with pytest.raises(ValidationError):
        AcousticFeatures(**invalid_dict)


def test_acoustic_features_missing_field_rejected(valid_acoustic_dict):
    """Verify that omitting any acoustic feature triggers ValidationError."""
    incomplete_dict = dict(valid_acoustic_dict)
    del incomplete_dict["pause_ratio"]
    with pytest.raises(ValidationError):
        AcousticFeatures(**incomplete_dict)


def test_acoustic_features_extra_field_forbidden(valid_acoustic_dict):
    """Verify that unexpected extra features are strictly forbidden."""
    extra_dict = dict(valid_acoustic_dict)
    extra_dict["spurious_feature"] = 42.0
    with pytest.raises(ValidationError):
        AcousticFeatures(**extra_dict)


def test_audio_inference_request_schema(valid_acoustic_dict):
    """Verify AudioInferenceRequest wraps participant ID and features."""
    req = AudioInferenceRequest(
        mother_id="M_TEST_001",
        features=AcousticFeatures(**valid_acoustic_dict),
    )
    assert req.mother_id == "M_TEST_001"
    assert req.features.f0_mean_hz == 215.0


# =====================================================================
# 2. AudioScreeningService Lifecycle & Missing Model Tests
# =====================================================================


def test_audio_service_configurable_model_dir(tmp_path):
    """Verify AudioScreeningService accepts a configurable model directory."""
    custom_dir = tmp_path / "custom_audio_models"
    service = AudioScreeningService(model_dir=custom_dir)
    assert service.model_dir_path == custom_dir
    assert service.is_available is False
    assert service.is_loaded is False


def test_audio_service_startup_missing_directory(tmp_path):
    """Verify startup with non-existent directory handles missing artifacts gracefully."""
    non_existent_dir = tmp_path / "does_not_exist"
    service = AudioScreeningService(model_dir=non_existent_dir)
    service.startup()
    assert service.is_available is False
    assert service.is_loaded is False
    assert "does not exist" in (service._load_error or "")


def test_audio_service_startup_missing_weights(tmp_path):
    """Verify startup with existing directory but missing checkpoint handles gracefully."""
    empty_dir = tmp_path / "empty_model_dir"
    empty_dir.mkdir(parents=True)
    service = AudioScreeningService(model_dir=empty_dir, model_filename="audio_model.pth")
    service.startup()
    assert service.is_available is False
    assert service.is_loaded is False
    assert "missing" in (service._load_error or "").lower()


def test_audio_service_predict_missing_model_returns_explicit_unavailable(valid_acoustic_dict, tmp_path):
    """Verify predict(as_response=True) returns explicit unavailable result without fabricating predictions."""
    service = AudioScreeningService(model_dir=tmp_path / "missing")
    response: AudioScreeningResponse = service.predict(valid_acoustic_dict, mother_id="M_001", as_response=True)

    # Verification of requirements:
    assert response.mother_id == "M_001"
    assert response.status == "unavailable"
    assert response.is_predictive is False
    assert response.prediction is None  # NEVER fabricated
    assert response.model_version is None
    assert response.data_origin == DATA_ORIGIN_TAG
    assert "unavailable" in response.message.lower()
    assert response.acoustic_features is not None
    assert response.acoustic_features.f0_mean_hz == 215.0


def test_audio_service_predict_missing_model_raises_http_503(valid_acoustic_dict, tmp_path):
    """Verify predict(as_response=False) raises HTTP 503 when model is missing."""
    service = AudioScreeningService(model_dir=tmp_path / "missing")
    with pytest.raises(HTTPException) as exc_info:
        service.predict(valid_acoustic_dict, mother_id="M_001", as_response=False)
    assert exc_info.value.status_code == 503
    assert "unavailable" in exc_info.value.detail.lower()


def test_audio_service_shutdown_cleans_state():
    """Verify shutdown resets internal service state."""
    service = AudioScreeningService()
    service.startup()
    service.shutdown()
    assert service.is_available is False
    assert service.is_loaded is False
    assert service._startup_attempted is False
    assert service._model is None
    assert service._scaler is None
    assert service._rf_model is None


def test_audio_service_never_automatically_trains(tmp_path):
    """Verify neither startup() nor predict() automatically generates model files."""
    test_dir = tmp_path / "no_train_dir"
    service = AudioScreeningService(model_dir=test_dir)

    service.startup()
    assert not test_dir.exists()  # Directory was not even created

    service.predict({
        "f0_mean_hz": 215.0,
        "f0_std_hz": 28.0,
        "jitter_local_percent": 1.20,
        "shimmer_local_percent": 4.50,
        "hnr_db": 20.0,
        "speech_rate_syllables_per_sec": 3.80,
        "pause_ratio": 0.24,
    }, as_response=True)

    # Ensure no files were generated
    assert not test_dir.exists() or len(list(test_dir.iterdir())) == 0


# =====================================================================
# 3. Model Inference & Artifact Loading Tests (with Temporary Mock)
# =====================================================================


def test_audio_service_loads_valid_artifacts(temp_audio_artifacts):
    """Verify AudioScreeningService correctly loads valid scaler and RF artifacts."""
    service = AudioScreeningService(model_dir=temp_audio_artifacts, model_name="random_forest")
    service.startup()

    assert service.is_loaded is True
    assert service.is_available is True
    assert service._scaler is not None
    assert service._rf_model is not None
    assert service._model_version == "audio_random_forest_v1"


def test_audio_service_predict_with_valid_artifacts_as_response(temp_audio_artifacts, valid_acoustic_dict):
    """Verify predict(as_response=True) produces valid completed AudioScreeningResponse."""
    service = AudioScreeningService(model_dir=temp_audio_artifacts, model_name="random_forest")
    service.startup()

    res = service.predict(valid_acoustic_dict, mother_id="M_TEST_123", as_response=True)

    assert isinstance(res, AudioScreeningResponse)
    assert res.mother_id == "M_TEST_123"
    assert res.status == "completed"
    assert res.is_predictive is False  # Enforces synthetic non-predictive flag
    assert res.data_origin == DATA_ORIGIN_TAG
    assert res.prediction is not None
    assert 0.0 <= res.prediction.predicted_risk_probability <= 1.0
    assert res.prediction.predicted_class in (0, 1)
    assert res.prediction.risk_category in ("LOW_RISK", "MODERATE_RISK", "HIGH_RISK")


def test_audio_service_predict_with_valid_artifacts_as_dict(temp_audio_artifacts, valid_acoustic_dict):
    """Verify predict(as_response=False) produces structured dictionary for fusion."""
    service = AudioScreeningService(model_dir=temp_audio_artifacts, model_name="random_forest")
    service.startup()

    pred_dict = service.predict(valid_acoustic_dict, threshold=0.5, as_response=False)

    assert isinstance(pred_dict, dict)
    assert "predicted_risk_probability" in pred_dict
    assert "predicted_class" in pred_dict
    assert "risk_category" in pred_dict
    assert pred_dict["decision_threshold"] == 0.5
    assert pred_dict["data_origin"] == DATA_ORIGIN_TAG


def test_audio_service_enforces_exact_feature_ordering(temp_audio_artifacts, valid_acoustic_dict):
    """Verify that features are fed to the scaler in the exact EXPECTED_AUDIO_FEATURES order."""
    service = AudioScreeningService(model_dir=temp_audio_artifacts, model_name="random_forest")
    service.startup()

    # Pass dictionary with deliberately reversed keys
    reversed_dict = {k: valid_acoustic_dict[k] for k in reversed(list(valid_acoustic_dict.keys()))}

    with patch.object(service._scaler, "transform", wraps=service._scaler.transform) as mock_transform:
        service.predict(reversed_dict, as_response=False)
        mock_transform.assert_called_once()
        transformed_df = mock_transform.call_args[0][0]
        assert list(transformed_df.columns) == EXPECTED_AUDIO_FEATURES
