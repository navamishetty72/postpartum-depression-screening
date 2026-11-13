"""Automated unit and integration test suite for statistical baseline training and evaluation.

Validates the core contracts of Phase 4A:
1. 5-Fold Stratified Cross-Validation fold separation and zero fold overlap.
2. Leak-free preprocessing: imputer and scaler fitted strictly inside training folds.
3. Complete out-of-fold prediction coverage across all 640 training participants.
4. Holdout isolation: test participants (160) are completely disjoint from CV training data.
5. Deterministic reproducibility across repeated runs with fixed random seeds.
6. Ablation subset dimensions and feature partition disjointness (198 + 22 = 220).
7. Evaluation metrics calculation and bootstrap confidence interval validity.
8. Artifact persistence and integrity.
"""

from pathlib import Path
from typing import Dict, List
import numpy as np
import pandas as pd
import pytest

from pipelines.video_model.config import (
    BASELINE_ARTIFACTS_DIR,
    CV_FOLDS,
    EXPECTED_TEST_PARTICIPANTS,
    EXPECTED_TOTAL_PARTICIPANTS,
    EXPECTED_TRAIN_PARTICIPANTS,
    SPLIT_MANIFEST_PATH,
)
from pipelines.video_model.dataset import PPDVideoDataset
from pipelines.video_model.evaluate_baselines import (
    compute_bootstrap_confidence_intervals,
    compute_classification_metrics,
    format_metrics_table,
)
from pipelines.video_model.models.statistical_baseline import (
    ParticipantStatisticalFeatureExtractor,
    SUPPORTED_FEATURE_SUBSETS,
    VideoLogisticRegressionBaseline,
    VideoRandomForestBaseline,
)
from pipelines.video_model.preprocessing import get_stratified_cv_splits
from pipelines.video_model.train_baselines import (
    run_cross_validation,
    train_and_evaluate_holdout,
)


@pytest.fixture(scope="module")
def train_dataset() -> PPDVideoDataset:
    """Fixture providing initialized training dataset (640 participants)."""
    return PPDVideoDataset(partition="train", validate_on_init=False)


@pytest.fixture(scope="module")
def test_dataset() -> PPDVideoDataset:
    """Fixture providing initialized holdout testing dataset (160 participants)."""
    return PPDVideoDataset(partition="test", validate_on_init=False)


# ==============================================================================
# 1. Fold Separation & Coverage
# ==============================================================================
def test_cv_fold_separation_and_leakage_isolation(train_dataset: PPDVideoDataset) -> None:
    """Requirement: 5-fold CV splits have zero overlap between train and validation indices."""
    splits = get_stratified_cv_splits(train_dataset, n_splits=5, seed=42)
    assert len(splits) == 5

    all_val_indices: List[int] = []
    for train_idx, val_idx in splits:
        train_set = set(train_idx)
        val_set = set(val_idx)

        # Zero overlap between train and validation sets in this fold
        assert train_set.isdisjoint(val_set)
        assert len(train_set) + len(val_set) == EXPECTED_TRAIN_PARTICIPANTS
        all_val_indices.extend(val_idx.tolist())

    # Every training index must appear in validation exactly once
    assert sorted(all_val_indices) == list(range(EXPECTED_TRAIN_PARTICIPANTS))
    assert len(set(all_val_indices)) == EXPECTED_TRAIN_PARTICIPANTS


# ==============================================================================
# 2. No Preprocessing Leakage
# ==============================================================================
def test_no_preprocessing_leakage() -> None:
    """Requirement: Imputer and scaler parameters depend strictly on the training fold."""
    np.random.seed(42)
    # Synthetic sequences
    X_train = [np.random.normal(loc=10.0, scale=2.0, size=(50, 24)).astype(np.float32) for _ in range(10)]
    for arr in X_train:
        arr[:, 22] = 0.90
        arr[:, 23] = 1.0

    X_val = [np.random.normal(loc=50.0, scale=2.0, size=(50, 24)).astype(np.float32) for _ in range(5)]
    for arr in X_val:
        arr[:, 22] = 0.90
        arr[:, 23] = 1.0

    y_train = np.array([0, 1] * 5)
    model = VideoLogisticRegressionBaseline(feature_subset="facial_motion")
    model.fit(X_train, y_train)

    scaler = model.pipeline.named_steps["scaler"]
    # Mean of scaler must be close to 10.0 (training fold mean), not 50.0 (validation)
    assert np.all(scaler.mean_ < 20.0)


# ==============================================================================
# 3. Out-of-Fold Prediction Coverage & Schema
# ==============================================================================
def test_oof_prediction_coverage_and_schema(train_dataset: PPDVideoDataset) -> None:
    """Requirement: Out-of-fold predictions cover all 640 training participants exactly once."""
    cv_res = run_cross_validation(
        model_name="logistic_regression",
        feature_subset="tracking_only",
        dataset=train_dataset,
        seed=42,
    )

    oof_df = cv_res["oof_df"]
    assert len(oof_df) == EXPECTED_TRAIN_PARTICIPANTS == 640

    required_cols = {"participant_id", "fold", "true_target", "predicted_label", "predicted_probability"}
    assert required_cols.issubset(set(oof_df.columns))

    # All participant IDs must match train dataset exactly
    assert oof_df["participant_id"].tolist() == train_dataset.get_participant_ids()

    # Probabilities must be strictly bounded in [0, 1]
    assert (oof_df["predicted_probability"] >= 0.0).all()
    assert (oof_df["predicted_probability"] <= 1.0).all()

    # Labels must be binary {0, 1}
    assert set(oof_df["predicted_label"].unique()).issubset({0, 1})

    # All 5 folds represented with balanced counts
    assert sorted(oof_df["fold"].unique().tolist()) == [0, 1, 2, 3, 4]
    fold_counts = oof_df["fold"].value_counts()
    for count in fold_counts:
        assert count == 128  # 640 / 5 = 128 per fold


# ==============================================================================
# 4. Holdout Isolation
# ==============================================================================
def test_holdout_isolation(train_dataset: PPDVideoDataset, test_dataset: PPDVideoDataset) -> None:
    """Requirement: Holdout test participants are completely disjoint from training participants."""
    train_pids = set(train_dataset.get_participant_ids())
    test_pids = set(test_dataset.get_participant_ids())

    assert train_pids.isdisjoint(test_pids)
    assert len(train_pids) == EXPECTED_TRAIN_PARTICIPANTS == 640
    assert len(test_pids) == EXPECTED_TEST_PARTICIPANTS == 160
    assert len(train_pids | test_pids) == EXPECTED_TOTAL_PARTICIPANTS == 800


# ==============================================================================
# 5. Deterministic Reproducibility
# ==============================================================================
def test_reproducibility_of_results(train_dataset: PPDVideoDataset) -> None:
    """Requirement: Fixed random seed produces identical predictions and metrics."""
    res1 = run_cross_validation(
        model_name="logistic_regression",
        feature_subset="tracking_only",
        dataset=train_dataset,
        seed=123,
    )
    res2 = run_cross_validation(
        model_name="logistic_regression",
        feature_subset="tracking_only",
        dataset=train_dataset,
        seed=123,
    )

    p1 = res1["oof_df"]["predicted_probability"].values
    p2 = res2["oof_df"]["predicted_probability"].values
    assert np.allclose(p1, p2, atol=1e-5)
    assert res1["overall_oof_metrics"]["roc_auc"] == res2["overall_oof_metrics"]["roc_auc"]


# ==============================================================================
# 6. Ablation Subsets Dimensions & Disjointness
# ==============================================================================
def test_ablation_subsets_dimension_and_disjointness() -> None:
    """Requirement: Feature subsets partition exactly: 198 (facial) + 22 (tracking) = 220 (all)."""
    ext_all = ParticipantStatisticalFeatureExtractor(feature_subset="all")
    ext_facial = ParticipantStatisticalFeatureExtractor(feature_subset="facial_motion")
    ext_tracking = ParticipantStatisticalFeatureExtractor(feature_subset="tracking_only")

    assert ext_all.n_features_out_ == 220
    assert ext_facial.n_features_out_ == 198
    assert ext_tracking.n_features_out_ == 22

    names_all = ext_all.get_feature_names_out()
    names_facial = ext_facial.get_feature_names_out()
    names_tracking = ext_tracking.get_feature_names_out()

    assert len(names_all) == 220
    assert len(names_facial) == 198
    assert len(names_tracking) == 22

    # Facial and tracking subsets must be completely disjoint
    assert set(names_facial).isdisjoint(set(names_tracking))

    # Union of facial and tracking feature sets must equal all 220 features
    assert set(names_facial) | set(names_tracking) == set(names_all)


# ==============================================================================
# 7. Metrics & Confidence Interval Calculation
# ==============================================================================
def test_metrics_calculation_and_bootstrap_cis() -> None:
    """Requirement: Classification metrics and bootstrap confidence intervals are bounded and valid."""
    np.random.seed(42)
    y_true = np.array([0] * 50 + [1] * 50)
    y_prob = np.random.uniform(0.0, 1.0, size=100)
    y_pred = (y_prob >= 0.5).astype(int)

    metrics = compute_classification_metrics(y_true, y_pred, y_prob)
    assert "roc_auc" in metrics
    assert "pr_auc" in metrics
    assert "balanced_accuracy" in metrics
    assert "f1_score" in metrics
    assert "confusion_matrix" in metrics
    assert metrics["total_samples"] == 100
    assert metrics["class_prevalence"] == 0.50

    cis = compute_bootstrap_confidence_intervals(y_true, y_pred, y_prob, n_bootstraps=200, seed=42)
    for m in ("roc_auc", "pr_auc", "balanced_accuracy", "f1_score"):
        assert m in cis
        ci = cis[m]
        assert 0.0 <= ci["ci_lower"] <= 1.0
        assert 0.0 <= ci["ci_upper"] <= 1.0
        assert ci["ci_lower"] <= ci["ci_upper"]

    table = format_metrics_table(metrics, cis, title="Test Table")
    assert "ROC-AUC" in table
    assert "Confusion Matrix" in table


# ==============================================================================
# 8. Saved Artifacts Integrity
# ==============================================================================
def test_saved_artifacts_integrity() -> None:
    """Requirement: Artifact directory contains valid summaries, prediction CSVs, and model files."""
    assert BASELINE_ARTIFACTS_DIR.exists()

    required_files = [
        "experiment_config.json",
        "cross_validation_results.json",
        "holdout_results.json",
        "statistical_baseline_report.md",
    ]
    for fname in required_files:
        p = BASELINE_ARTIFACTS_DIR / fname
        assert p.is_file(), f"Expected artifact {fname} missing at {p}"
        assert p.stat().st_size > 0

    # Check that OOF and holdout CSVs exist and have correct row counts
    for model in ("logistic_regression", "random_forest"):
        for subset in ("all", "facial_motion", "tracking_only"):
            oof_file = BASELINE_ARTIFACTS_DIR / f"oof_predictions_{model}_{subset}.csv"
            holdout_file = BASELINE_ARTIFACTS_DIR / f"holdout_predictions_{model}_{subset}.csv"
            model_file = BASELINE_ARTIFACTS_DIR / f"fitted_model_{model}_{subset}.joblib"

            assert oof_file.is_file(), f"Missing {oof_file}"
            assert holdout_file.is_file(), f"Missing {holdout_file}"
            assert model_file.is_file(), f"Missing {model_file}"

            df_oof = pd.read_csv(oof_file)
            assert len(df_oof) == EXPECTED_TRAIN_PARTICIPANTS == 640

            df_holdout = pd.read_csv(holdout_file)
            assert len(df_holdout) == EXPECTED_TEST_PARTICIPANTS == 160

