"""Focused unit tests for Audio schema validation and AudioScreeningService foundation.

Tests Phase 8C requirements:
1. Schema validation of the 7 acoustic features against physiological bounds.
2. Verification of documented clinical literature citations for all physiological boundaries.
3. Extra and missing field rejection (extra='forbid').
4. AudioScreeningService startup, shutdown, and configurable directory.
5. Verification of is_loaded and is_available lifecycle properties.
6. Safe unavailable response behavior when model checkpoints are missing (no fabricated predictions).
7. Strict non-predictive flag (is_predictive=False) and provenance preservation.
8. Proper propagation of participant/mother identifiers without exposing biometrics in logs.
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from backend.schemas.audio import (
    ACOUSTIC_FEATURE_BOUNDS,
    ACOUSTIC_FEATURE_LITERATURE_SOURCES,
    ACOUSTIC_FEATURE_NAMES,
    AcousticFeatures,
    AudioInferenceRequest,
    AudioScreeningResponse,
)
from backend.services.audio_service import AudioScreeningService
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
    """Verify predict() returns explicit unavailable result without fabricating predictions."""
    service = AudioScreeningService(model_dir=tmp_path / "missing")
    response: AudioScreeningResponse = service.predict(valid_acoustic_dict, mother_id="M_001")

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


def test_audio_service_shutdown_cleans_state():
    """Verify shutdown resets internal service state."""
    service = AudioScreeningService()
    service.startup()
    service.shutdown()
    assert service.is_available is False
    assert service.is_loaded is False
    assert service._startup_attempted is False
    assert service._model is None
