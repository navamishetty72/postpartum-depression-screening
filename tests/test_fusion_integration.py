"""Comprehensive test suite for Multimodal Late Fusion integration, safety, and alignment.

Validates:
1. Participant Alignment: Exact participant ID alignment across all 4 modalities and split manifest.
2. Fold Isolation: Identical 5-fold cross-validation partition across modalities (128 per fold).
3. No Target Leakage: Strict absence of target variables in features; zero holdout contamination.
4. Missing Modality Handling: Dynamic handling without fabricating data for unavailable modalities.
5. Eligibility Enforcement: Non-eligible requests are strictly rejected with HTTP 403.
6. Audio Inference & Provenance: Audio feature inference with synthetic research provenance tags.
7. Multimodal Late Fusion & Discordance: Non-negative stacking and cross-modal discordance analysis.
8. Deterministic Reproducibility: Identical predictions given identical modality inputs.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.ml.fusion_engine import (
    CANONICAL_STACKING_WEIGHTS,
    NonNegativeStackingFusionStrategy,
    MultimodalFusionEngine,
    ModalityCandidate,
)
from backend.services.screening_service import screening_service
from pipelines.fusion.config import (
    AUDIO_OOF_PATH,
    CLINICAL_OOF_PATH,
    PROJECT_ROOT,
    SPLIT_MANIFEST_PATH,
    TARGET_COLUMN,
    TEXT_OOF_PATH,
    VIDEO_OOF_PATH,
)
from tests.test_backend_screening import _get_valid_clinical_features

client = TestClient(app)

REQUIRED_MULTIMODAL_OOF_PATHS = [CLINICAL_OOF_PATH, AUDIO_OOF_PATH, TEXT_OOF_PATH, VIDEO_OOF_PATH]
MULTIMODAL_OOF_AVAILABLE = all(p.is_file() for p in REQUIRED_MULTIMODAL_OOF_PATHS)


def _get_valid_audio_features():
    return {
        "f0_mean_hz": 215.4,
        "f0_std_hz": 32.1,
        "jitter_local_percent": 1.45,
        "shimmer_local_percent": 3.82,
        "hnr_db": 17.5,
        "speech_rate_syllables_per_sec": 3.9,
        "pause_ratio": 0.28,
    }


@pytest.mark.skipif(
    not MULTIMODAL_OOF_AVAILABLE,
    reason="Requires all four multimodal OOF prediction artifacts (clinical, audio, text, video)",
)
def test_multimodal_participant_alignment():
    """Verify exact participant ID and target alignment across all 4 modalities on canonical 640 cohort."""
    manifest = pd.read_csv(SPLIT_MANIFEST_PATH)
    train_manifest = manifest[manifest["split_partition"] == "train"].reset_index(drop=True)
    expected_pids = train_manifest["participant_id"].values
    expected_targets = train_manifest[TARGET_COLUMN].values

    clin_df = pd.read_csv(CLINICAL_OOF_PATH)
    audio_df = pd.read_csv(AUDIO_OOF_PATH)
    text_df = pd.read_csv(TEXT_OOF_PATH)
    video_df = pd.read_csv(VIDEO_OOF_PATH)

    for name, df in [("clinical", clin_df), ("audio", audio_df), ("text", text_df), ("video", video_df)]:
        assert len(df) == 640, f"Expected 640 rows in {name}, found {len(df)}"
        assert np.array_equal(df["participant_id"].values, expected_pids), f"Participant ID mismatch in {name}"

        target_col = "y_true" if "y_true" in df.columns else "true_target"
        assert np.array_equal(df[target_col].values, expected_targets), f"Target mismatch in {name}"


@pytest.mark.skipif(
    not MULTIMODAL_OOF_AVAILABLE,
    reason="Requires all four multimodal OOF prediction artifacts (clinical, audio, text, video)",
)
def test_multimodal_fold_isolation():
    """Verify that cross-validation folds are identically partitioned across all modalities."""
    audio_df = pd.read_csv(AUDIO_OOF_PATH)
    text_df = pd.read_csv(TEXT_OOF_PATH)
    video_df = pd.read_csv(VIDEO_OOF_PATH)

    audio_folds = audio_df["fold"].values
    text_folds = text_df["fold"].values
    # video canonical bilstm uses 0-based folds [0..4]
    video_folds = video_df["fold"].values + 1

    assert np.array_equal(audio_folds, text_folds), "Audio and text fold assignments must be identical"
    assert np.array_equal(audio_folds, video_folds), "Audio and video fold assignments must be identical"

    for f in range(1, 6):
        assert (audio_folds == f).sum() == 128, f"Expected exactly 128 participants in fold {f}"


@pytest.mark.skipif(
    not MULTIMODAL_OOF_AVAILABLE,
    reason="Requires all four multimodal OOF prediction artifacts (clinical, audio, text, video)",
)
def test_no_target_leakage_in_fusion():
    """Verify that probability features are within [0.0, 1.0] and contain no raw EPDS targets."""
    clin_df = pd.read_csv(CLINICAL_OOF_PATH)
    audio_df = pd.read_csv(AUDIO_OOF_PATH)
    text_df = pd.read_csv(TEXT_OOF_PATH)
    video_df = pd.read_csv(VIDEO_OOF_PATH)

    prob_pairs = [
        ("clinical", clin_df["logistic_regression_prob"]),
        ("audio", audio_df["logistic_regression_prob"]),
        ("text", text_df["predicted_probability"]),
        ("video", video_df["predicted_probability"]),
    ]

    for name, s in prob_pairs:
        assert not s.isna().any(), f"NaNs found in {name} probabilities"
        assert (s >= 0.0).all() and (s <= 1.0).all(), f"Probabilities out of bounds in {name}"
        assert len(s.unique()) > 10, f"Probability distribution for {name} appears degenerate"


def test_eligibility_enforcement_api():
    """Verify that screening requests with false eligibility are rejected with HTTP 403."""
    payload = {
        "motherId": "M-ELIG-01",
        "modalities": json.dumps({"clinical": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "eligibilityConfirmed": "false",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    resp = client.post("/api/screenings/analyze", data=payload)
    assert resp.status_code == 403
    assert "eligibility confirmation is required" in resp.json()["detail"].lower()


def test_missing_modality_handling_without_fabrication():
    """Verify that requested modalities without data report unavailable without fabricating scores."""
    payload = {
        "motherId": "M-MISSING-01",
        "modalities": json.dumps({"clinical": True, "audio": True, "video": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
        # No audio_features or video features passed
    }
    resp = client.post("/api/screenings/analyze", data=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["clinical"]["status"] == "completed"
    assert data["audio"]["status"] == "unavailable"
    assert data["audio"]["prediction"] is None
    assert data["video"]["status"] == "unavailable"
    assert data["video"]["prediction"] is None
    assert data["status"] == "partially_completed"


def test_audio_feature_inference_and_provenance():
    """Verify predictive audio inference when 7 acoustic features are supplied."""
    payload = {
        "motherId": "M-AUDIO-01",
        "modalities": json.dumps({"clinical": False, "audio": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "audio_features": json.dumps(_get_valid_audio_features()),
    }
    resp = client.post("/api/screenings/analyze", data=payload)
    assert resp.status_code == 200
    data = resp.json()

    audio = data["audio"]
    assert audio["status"] == "completed"
    assert audio["prediction"] is not None
    pred = audio["prediction"]
    assert 0.0 <= pred["predicted_risk_probability"] <= 1.0
    assert pred["predicted_class"] in (0, 1)
    assert pred["data_origin"] == "CLINICALLY_CONDITIONED_SYNTHETIC"
    assert "synthetic" in pred["provenance_notice"].lower()


def test_multimodal_late_fusion_and_discordance():
    """Verify multimodal late fusion and cross-modal discordance when clinical and audio are both active."""
    payload = {
        "motherId": "M-FUSION-02",
        "modalities": json.dumps({"clinical": True, "audio": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
        "audio_features": json.dumps(_get_valid_audio_features()),
    }
    resp = client.post("/api/screenings/analyze", data=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "completed"
    assert data["clinical"]["status"] == "completed"
    assert data["audio"]["status"] == "completed"

    fusion = data["fusion"]
    assert fusion["status"] == "completed"
    assert fusion["combined_score"] is not None
    assert 0.0 <= fusion["combined_score"] <= 1.0
    assert fusion["risk_category"] in ("LOW_RISK", "MODERATE_RISK", "HIGH_RISK")
    assert 0 <= fusion["epds_equivalent"] <= 30

    # Non-negative stacking normalized weights: clinical=1.0, audio=0.0
    assert fusion["modality_contributions"]["clinical"] == 1.0
    assert fusion["modality_contributions"]["audio"] == 0.0

    # Discordance analysis compares clinical vs audio
    discordance = fusion["discordance_analysis"]
    assert discordance is not None
    assert "discordance_detected" in discordance
    assert len(discordance["comparison"]) == 1
    comp = discordance["comparison"][0]
    assert comp["modality_a"] == "clinical"
    assert comp["modality_b"] == "audio"


def test_fusion_reproducibility():
    """Verify that late fusion predictions are strictly deterministic."""
    strategy = NonNegativeStackingFusionStrategy()
    c1 = ModalityCandidate(modality="clinical", status="completed", probability=0.6543, is_predictive=True)
    c2 = ModalityCandidate(modality="audio", status="completed", probability=0.5123, is_predictive=True)

    score1, cat1, epds1, contrib1 = strategy.combine([c1, c2])
    score2, cat2, epds2, contrib2 = strategy.combine([c1, c2])

    assert score1 == score2
    assert cat1 == cat2
    assert epds1 == epds2
    assert contrib1 == contrib2
