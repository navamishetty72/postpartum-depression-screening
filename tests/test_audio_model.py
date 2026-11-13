"""Automated unit and integration test suite for the audio classification model.

Validates:
1. Participant ID alignment with canonical train/test split manifest across all 800 participants.
2. Feature selection and strict target leakage prevention (exactly 7 acoustic features).
3. 5-fold cross-validation fold separation and zero fold overlap.
4. Complete out-of-fold (OOF) prediction coverage across all 640 training participants.
5. Holdout test isolation (160 participants) and class balance.
6. Deterministic reproducibility across repeated training runs with fixed random seed.
7. Saved model artifact schemas, serialization integrity, and inference contracts.
"""

from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
import pytest

from pipelines.synthetic_audio.config import (
    ACOUSTIC_FEATURE_NAMES,
    SYNTHETIC_AUDIO_MANIFEST_PATH,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
)
from pipelines.synthetic_audio.train_audio_model import (
    ACOUSTIC_FEATURES,
    ARTIFACTS_DIR,
    CV_FOLDS,
    EXPECTED_TEST_PARTICIPANTS,
    EXPECTED_TOTAL_PARTICIPANTS,
    EXPECTED_TRAIN_PARTICIPANTS,
    PARTICIPANT_ID_COLUMN,
    RANDOM_SEED,
    SPLIT_COLUMN,
    TARGET_COLUMN,
    load_and_prepare_audio_data,
    train_audio_models,
)


@pytest.fixture(scope="module")
def split_manifest() -> pd.DataFrame:
    """Load authoritative frozen split manifest."""
    assert TRAIN_TEST_SPLIT_MANIFEST_PATH.is_file()
    return pd.read_csv(TRAIN_TEST_SPLIT_MANIFEST_PATH)


@pytest.fixture(scope="module")
def audio_manifest() -> pd.DataFrame:
    """Load synthetic audio manifest."""
    assert SYNTHETIC_AUDIO_MANIFEST_PATH.is_file()
    return pd.read_csv(SYNTHETIC_AUDIO_MANIFEST_PATH)


@pytest.fixture(scope="module")
def prepared_audio_data():
    """Load and partition audio dataset."""
    return load_and_prepare_audio_data()


@pytest.fixture(scope="module")
def audio_artifacts():
    """Ensure audio model artifacts exist, training if necessary."""
    required_files = [
        "logistic_regression.joblib",
        "random_forest.joblib",
        "scaler.joblib",
        "oof_predictions.csv",
        "test_predictions.csv",
        "metrics_summary.json",
    ]
    missing = [f for f in required_files if not (ARTIFACTS_DIR / f).is_file()]
    if missing:
        train_audio_models(artifacts_dir=ARTIFACTS_DIR, save_artifacts=True)
    return ARTIFACTS_DIR


# ==============================================================================
# 1. Participant Alignment
# ==============================================================================
def test_1_participant_alignment(split_manifest: pd.DataFrame, audio_artifacts: Path) -> None:
    """Requirement: All 800 participants are accounted for and aligned with split manifest."""
    oof_df = pd.read_csv(audio_artifacts / "oof_predictions.csv")
    test_df = pd.read_csv(audio_artifacts / "test_predictions.csv")

    assert len(oof_df) == EXPECTED_TRAIN_PARTICIPANTS == 640
    assert len(test_df) == EXPECTED_TEST_PARTICIPANTS == 160
    assert len(oof_df) + len(test_df) == EXPECTED_TOTAL_PARTICIPANTS == 800

    # Disjointness
    train_pids = set(oof_df[PARTICIPANT_ID_COLUMN])
    test_pids = set(test_df[PARTICIPANT_ID_COLUMN])
    assert train_pids.isdisjoint(test_pids)
    assert len(train_pids) == 640
    assert len(test_pids) == 160

    # Alignment with split manifest
    expected_train_pids = split_manifest[split_manifest[SPLIT_COLUMN] == "train"][
        PARTICIPANT_ID_COLUMN
    ].tolist()
    expected_test_pids = split_manifest[split_manifest[SPLIT_COLUMN] == "test"][
        PARTICIPANT_ID_COLUMN
    ].tolist()

    assert oof_df[PARTICIPANT_ID_COLUMN].tolist() == expected_train_pids
    assert test_df[PARTICIPANT_ID_COLUMN].tolist() == expected_test_pids


# ==============================================================================
# 2. Feature Selection & Leakage Prevention
# ==============================================================================
def test_2_feature_selection_and_leakage_prevention(prepared_audio_data) -> None:
    """Requirement: Strictly the 7 acoustic summary features are used; zero leakage."""
    X_train, y_train, train_df, X_test, y_test, test_df = prepared_audio_data

    # Check exact feature names and counts
    assert list(X_train.columns) == ACOUSTIC_FEATURES
    assert list(X_test.columns) == ACOUSTIC_FEATURES
    assert len(ACOUSTIC_FEATURES) == 7

    # Target and metadata must not exist in predictor matrix
    forbidden = [
        TARGET_COLUMN,
        PARTICIPANT_ID_COLUMN,
        SPLIT_COLUMN,
        "sr",
        "matrix_index",
        "sequence_length",
        "embedding_path",
        "data_origin",
        "generation_seed",
    ]
    for col in forbidden:
        assert col not in X_train.columns, f"Forbidden column {col} found in X_train"
        assert col not in X_test.columns, f"Forbidden column {col} found in X_test"

    # Verify no nulls or infinities in predictors
    assert not X_train.isnull().any().any()
    assert not X_test.isnull().any().any()
    assert np.isfinite(X_train.values).all()
    assert np.isfinite(X_test.values).all()


# ==============================================================================
# 3. 5-Fold Stratified CV Separation
# ==============================================================================
def test_3_fold_separation_and_zero_overlap(audio_artifacts: Path) -> None:
    """Requirement: 5-fold CV splits have exactly 128 validation records per fold with zero overlap."""
    oof_df = pd.read_csv(audio_artifacts / "oof_predictions.csv")

    assert "fold" in oof_df.columns
    folds = sorted(oof_df["fold"].unique().tolist())
    assert folds == [1, 2, 3, 4, 5]

    # Every fold must have exactly 640 / 5 = 128 validation participants
    fold_counts = oof_df["fold"].value_counts()
    for fold_num, count in fold_counts.items():
        assert count == 128, f"Fold {fold_num} expected 128 samples, got {count}"

    # Folds must partition the 640 participants completely and disjointly
    fold_pids = [set(oof_df[oof_df["fold"] == f][PARTICIPANT_ID_COLUMN]) for f in folds]
    for i in range(len(fold_pids)):
        for j in range(i + 1, len(fold_pids)):
            assert fold_pids[i].isdisjoint(fold_pids[j]), f"Overlap between fold {i+1} and fold {j+1}"


# ==============================================================================
# 4. Out-of-Fold Coverage & Prediction Schema
# ==============================================================================
def test_4_oof_coverage_and_schema(audio_artifacts: Path) -> None:
    """Requirement: Out-of-fold predictions cover all 640 training participants with valid probabilities."""
    oof_df = pd.read_csv(audio_artifacts / "oof_predictions.csv")

    assert len(oof_df) == EXPECTED_TRAIN_PARTICIPANTS == 640
    assert oof_df[PARTICIPANT_ID_COLUMN].nunique() == 640

    required_cols = [
        PARTICIPANT_ID_COLUMN,
        SPLIT_COLUMN,
        "true_target",
        "fold",
        "logistic_regression_prob",
        "logistic_regression_pred",
        "random_forest_prob",
        "random_forest_pred",
    ]
    for col in required_cols:
        assert col in oof_df.columns, f"Missing required column {col} in oof_predictions.csv"

    # Probabilities bounded in [0, 1]
    for model in ("logistic_regression", "random_forest"):
        prob_col = f"{model}_prob"
        pred_col = f"{model}_pred"
        assert (oof_df[prob_col] >= 0.0).all() and (oof_df[prob_col] <= 1.0).all()
        assert set(oof_df[pred_col].unique()).issubset({0, 1})
        # Check alignment between probability threshold and predicted label
        expected_pred = (oof_df[prob_col] >= 0.5).astype(int)
        assert (oof_df[pred_col] == expected_pred).all()


# ==============================================================================
# 5. Holdout Test Isolation
# ==============================================================================
def test_5_holdout_isolation_and_balance(audio_artifacts: Path) -> None:
    """Requirement: Holdout test set has 160 participants, canonical class balance, valid predictions."""
    test_df = pd.read_csv(audio_artifacts / "test_predictions.csv")

    assert len(test_df) == EXPECTED_TEST_PARTICIPANTS == 160
    assert test_df[PARTICIPANT_ID_COLUMN].nunique() == 160

    # Canonical test class distribution: 90 negative (0), 70 positive (1)
    class_counts = test_df["true_target"].value_counts().to_dict()
    assert class_counts.get(0) == 90, f"Expected 90 class 0 in test, got {class_counts.get(0)}"
    assert class_counts.get(1) == 70, f"Expected 70 class 1 in test, got {class_counts.get(1)}"

    for model in ("logistic_regression", "random_forest"):
        prob_col = f"{model}_prob"
        pred_col = f"{model}_pred"
        assert (test_df[prob_col] >= 0.0).all() and (test_df[prob_col] <= 1.0).all()
        assert set(test_df[pred_col].unique()).issubset({0, 1})


# ==============================================================================
# 6. Deterministic Reproducibility
# ==============================================================================
def test_6_reproducibility() -> None:
    """Requirement: Training runs with fixed random seed produce identical metrics."""
    res1 = train_audio_models(save_artifacts=False)
    res2 = train_audio_models(save_artifacts=False)

    for m in ("logistic_regression", "random_forest"):
        auc1 = res1["cross_validation"][m]["summary_across_folds"]["roc_auc"]["mean"]
        auc2 = res2["cross_validation"][m]["summary_across_folds"]["roc_auc"]["mean"]
        assert auc1 == auc2, f"Discrepancy in CV ROC-AUC for {m}: {auc1} vs {auc2}"

        test_auc1 = res1["holdout_test"][m]["roc_auc"]
        test_auc2 = res2["holdout_test"][m]["roc_auc"]
        assert test_auc1 == test_auc2, f"Discrepancy in test ROC-AUC for {m}: {test_auc1} vs {test_auc2}"


# ==============================================================================
# 7. Output Artifact Schemas & Serialization Integrity
# ==============================================================================
def test_7_output_artifacts_schemas_and_integrity(audio_artifacts: Path) -> None:
    """Requirement: All model binaries, scaler, predictions, and metrics JSON exist and load properly."""
    expected_files = [
        "logistic_regression.joblib",
        "random_forest.joblib",
        "scaler.joblib",
        "oof_predictions.csv",
        "test_predictions.csv",
        "metrics_summary.json",
    ]
    for fname in expected_files:
        p = audio_artifacts / fname
        assert p.is_file(), f"Missing artifact {fname} at {p}"
        assert p.stat().st_size > 0

    # Load models and test prediction contract
    lr_model = joblib.load(audio_artifacts / "logistic_regression.joblib")
    rf_model = joblib.load(audio_artifacts / "random_forest.joblib")
    scaler = joblib.load(audio_artifacts / "scaler.joblib")

    # Scaler must have 7 features fitted
    assert scaler.n_features_in_ == 7
    assert len(scaler.mean_) == 7

    # Models must have predict_proba and predict methods
    dummy_input = pd.DataFrame(np.zeros((2, 7)), columns=ACOUSTIC_FEATURES)
    dummy_scaled = scaler.transform(dummy_input)

    lr_probs = lr_model.predict_proba(dummy_scaled)
    assert lr_probs.shape == (2, 2)

    rf_probs = rf_model.predict_proba(dummy_scaled)
    assert rf_probs.shape == (2, 2)

    # Verify metrics JSON structure
    with open(audio_artifacts / "metrics_summary.json", "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert "metadata" in metrics
    assert "cross_validation" in metrics
    assert "holdout_test" in metrics
    assert metrics["metadata"]["random_seed"] == RANDOM_SEED
    assert metrics["metadata"]["features"] == ACOUSTIC_FEATURES

    for m in ("logistic_regression", "random_forest"):
        assert m in metrics["cross_validation"]
        assert m in metrics["holdout_test"]
        test_info = metrics["holdout_test"][m]
        assert "roc_auc" in test_info
        assert "pr_auc" in test_info
        assert "f1" in test_info
        assert "confidence_intervals_95" in test_info
        ci = test_info["confidence_intervals_95"]["roc_auc"]
        assert 0.0 <= ci["ci_lower"] <= ci["ci_upper"] <= 1.0

