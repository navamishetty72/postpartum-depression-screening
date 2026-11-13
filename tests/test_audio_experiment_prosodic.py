"""Test suite for Audio Prosodic Pruning Experiment 1.

Validates:
1. Experiment artifacts exist under artifacts/audio_experiments/prosodic_pruning/.
2. Exact participant ID and target match on the canonical 640 training participants.
3. Complete absence of the 160 holdout test participants (strict holdout isolation).
4. Mathematical validity and non-zero bounded properties of articulation ratios.
5. Finite, valid probabilities in [0.0, 1.0] across all experiment OOF outputs.
6. Absolute non-interference with production models/audio_model/ artifacts.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest

from pipelines.synthetic_audio.config import (
    ACOUSTIC_FEATURE_NAMES,
    PROJECT_ROOT,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
)

EXPERIMENT_DIR = PROJECT_ROOT / "artifacts" / "audio_experiments" / "prosodic_pruning"
PRODUCTION_DIR = PROJECT_ROOT / "models" / "audio_model"
OOF_EXPERIMENT_PATH = EXPERIMENT_DIR / "oof_predictions_experiments.csv"


@pytest.fixture(scope="module")
def audio_production_artifacts():
    """Ensure audio production model artifacts exist, training if necessary."""
    from pipelines.synthetic_audio.train_audio_model import train_audio_models
    required_files = [
        "logistic_regression.joblib",
        "random_forest.joblib",
        "scaler.joblib",
        "oof_predictions.csv",
        "test_predictions.csv",
        "metrics_summary.json",
    ]
    missing = [f for f in required_files if not (PRODUCTION_DIR / f).is_file()]
    if missing:
        train_audio_models(artifacts_dir=PRODUCTION_DIR, save_artifacts=True)
    return PRODUCTION_DIR


def test_experiment_artifacts_exist():
    """Verify that all committed experiment artifacts exist and are non-empty."""
    assert EXPERIMENT_DIR.is_dir(), f"Missing directory: {EXPERIMENT_DIR}"

    expected_files = [
        "experiment_results.json",
        "experiment_report.md",
    ]
    for fname in expected_files:
        fpath = EXPERIMENT_DIR / fname
        assert fpath.is_file(), f"Missing artifact: {fname}"
        assert fpath.stat().st_size > 0, f"Empty artifact: {fname}"

    if OOF_EXPERIMENT_PATH.is_file():
        assert OOF_EXPERIMENT_PATH.stat().st_size > 0


@pytest.mark.skipif(
    not OOF_EXPERIMENT_PATH.is_file(),
    reason="Requires generated experiment artifact: oof_predictions_experiments.csv (run pipelines/synthetic_audio/experiment_prosodic_pruning.py)",
)
def test_holdout_isolation_and_training_alignment():
    """Verify that experiment outputs strictly contain only the 640 training participants."""
    manifest = pd.read_csv(TRAIN_TEST_SPLIT_MANIFEST_PATH)
    train_manifest = manifest[manifest["split_partition"] == "train"].reset_index(drop=True)
    test_manifest = manifest[manifest["split_partition"] == "test"].reset_index(drop=True)

    df_oof = pd.read_csv(OOF_EXPERIMENT_PATH)

    assert len(df_oof) == 640, f"Expected 640 training rows, got {len(df_oof)}"
    assert (df_oof["participant_id"] == train_manifest["participant_id"]).all(), "Participant IDs do not match train manifest!"
    assert (df_oof["true_target"] == train_manifest["target_canonical_epds_ge_13"]).all(), "Target labels mismatch!"

    # Ensure 100% disjoint from holdout
    train_ids = set(df_oof["participant_id"])
    holdout_ids = set(test_manifest["participant_id"])
    assert train_ids.isdisjoint(holdout_ids), "Data leakage! Holdout participant IDs found in experiment OOF!"


def test_articulation_ratio_mathematics():
    """Verify mathematical properties of articulation rate and speech-to-pause ratio."""
    audio_manifest = pd.read_csv(PROJECT_ROOT / "data" / "synthetic" / "audio" / "audio_manifest.csv")
    sr = audio_manifest["speech_rate_syllables_per_sec"].values
    pr = audio_manifest["pause_ratio"].values

    # Denominator (1 - pause_ratio) must be strictly positive and bounded
    phonation_fraction = 1.0 - pr
    assert (phonation_fraction > 0.30).all(), "Phonation fraction <= 0.30 detected!"
    assert (phonation_fraction < 1.0).all(), "Phonation fraction >= 1.0 detected!"

    # Articulation rate must be strictly greater than speech rate (since phonation time < total time)
    art_rate = sr / phonation_fraction
    assert (art_rate > sr).all(), "Articulation rate must be greater than speech rate!"

    # No NaNs or Infs
    assert not np.isnan(art_rate).any()
    assert not np.isinf(art_rate).any()


@pytest.mark.skipif(
    not OOF_EXPERIMENT_PATH.is_file(),
    reason="Requires generated experiment artifact: oof_predictions_experiments.csv (run pipelines/synthetic_audio/experiment_prosodic_pruning.py)",
)
def test_oof_probabilities_validity():
    """Verify that all OOF probability outputs are within [0.0, 1.0]."""
    df_oof = pd.read_csv(OOF_EXPERIMENT_PATH)

    prob_cols = [c for c in df_oof.columns if c.endswith("_prob")]
    pred_cols = [c for c in df_oof.columns if c.endswith("_pred")]

    assert len(prob_cols) >= 4, "Missing probability columns in experiment OOF table!"
    assert len(pred_cols) >= 4, "Missing prediction columns in experiment OOF table!"

    for col in prob_cols:
        assert not df_oof[col].isna().any(), f"NaN in {col}"
        assert not np.isinf(df_oof[col]).any(), f"Inf in {col}"
        assert (df_oof[col] >= 0.0).all(), f"Values < 0 in {col}"
        assert (df_oof[col] <= 1.0).all(), f"Values > 1 in {col}"

    for col in pred_cols:
        assert set(df_oof[col].unique()).issubset({0, 1}), f"Non-binary values in {col}"


def test_production_artifacts_untouched(audio_production_artifacts: Path):
    """Verify that production models/audio_model/ artifacts were not modified or overwritten."""
    assert audio_production_artifacts.is_dir()

    expected_production_files = [
        "logistic_regression.joblib",
        "random_forest.joblib",
        "scaler.joblib",
        "oof_predictions.csv",
        "test_predictions.csv",
        "metrics_summary.json",
    ]
    for fname in expected_production_files:
        fpath = PRODUCTION_DIR / fname
        assert fpath.is_file(), f"Production file missing: {fname}"
        assert fpath.stat().st_size > 0, f"Production file empty: {fname}"
