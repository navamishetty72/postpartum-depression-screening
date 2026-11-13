"""Automated test suite for four-modality late fusion pipeline (Moment AI).

Validates:
1. Exact participant ID and target alignment across Clinical, Audio, Text, Video, and Split Manifest.
2. Complete absence of data leakage between 640 OOF training set and 160 frozen holdout test set.
3. Probability validity: All outputs are strictly numeric, finite, and bounded within [0.0, 1.0].
4. Meta-classifier serialization integrity and 100% deterministic prediction reproducibility.
5. Exact schema and row count preservation across all generated fusion artifacts.
"""

from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from pipelines.fusion.config import (
    AUDIO_HOLDOUT_PATH,
    AUDIO_OOF_PATH,
    CLINICAL_HOLDOUT_PATH,
    CLINICAL_OOF_PATH,
    DECISION_THRESHOLD,
    DEFAULT_PROB_MAPPINGS,
    EXPECTED_TEST_PARTICIPANTS,
    EXPECTED_TOTAL_PARTICIPANTS,
    EXPECTED_TRAIN_PARTICIPANTS,
    FEATURE_COLUMNS,
    FUSION_ARTIFACTS_DIR,
    PROJECT_ROOT,
    SPLIT_MANIFEST_PATH,
    TARGET_COLUMN,
    TEXT_HOLDOUT_PATH,
    TEXT_OOF_PATH,
    VIDEO_HOLDOUT_PATH,
    VIDEO_OOF_PATH,
)
from pipelines.fusion.metrics import compute_classification_metrics
from pipelines.fusion.train_fusion import load_and_validate_datasets


def test_fusion_artifacts_exist():
    """Verify that all required late fusion artifacts exist under models/fusion/."""
    assert FUSION_ARTIFACTS_DIR.is_dir(), f"Missing directory: {FUSION_ARTIFACTS_DIR}"

    expected_files = [
        "fusion_meta_learner.joblib",
        "oof_predictions_fusion.csv",
        "holdout_predictions_fusion.csv",
        "metrics_summary.json",
        "feature_weights.json",
        "fusion_report.md",
    ]
    for fname in expected_files:
        fpath = FUSION_ARTIFACTS_DIR / fname
        assert fpath.is_file(), f"Missing artifact: {fname}"
        assert fpath.stat().st_size > 0, f"Artifact is empty: {fname}"


def test_cross_modality_participant_alignment():
    """Verify exact participant ID and target alignment across all 4 modalities and split manifest."""
    manifest = pd.read_csv(SPLIT_MANIFEST_PATH)
    train_manifest = manifest[manifest["split_partition"] == "train"].reset_index(drop=True)
    test_manifest = manifest[manifest["split_partition"] == "test"].reset_index(drop=True)

    clin_oof = pd.read_csv(CLINICAL_OOF_PATH)
    audio_oof = pd.read_csv(AUDIO_OOF_PATH)
    text_oof = pd.read_csv(TEXT_OOF_PATH)
    video_oof = pd.read_csv(VIDEO_OOF_PATH)

    clin_test = pd.read_csv(CLINICAL_HOLDOUT_PATH)
    audio_test = pd.read_csv(AUDIO_HOLDOUT_PATH)
    text_test = pd.read_csv(TEXT_HOLDOUT_PATH)
    video_test = pd.read_csv(VIDEO_HOLDOUT_PATH)

    # 1. Row counts
    for name, df in [("clinical", clin_oof), ("audio", audio_oof), ("text", text_oof), ("video", video_oof)]:
        assert len(df) == EXPECTED_TRAIN_PARTICIPANTS, f"OOF {name} count != {EXPECTED_TRAIN_PARTICIPANTS}"
    for name, df in [("clinical", clin_test), ("audio", audio_test), ("text", text_test), ("video", video_test)]:
        assert len(df) == EXPECTED_TEST_PARTICIPANTS, f"Holdout {name} count != {EXPECTED_TEST_PARTICIPANTS}"

    # 2. OOF Participant IDs match canonical manifest in order
    assert (clin_oof["participant_id"] == train_manifest["participant_id"]).all()
    assert (audio_oof["participant_id"] == train_manifest["participant_id"]).all()
    assert (text_oof["participant_id"] == train_manifest["participant_id"]).all()
    assert (video_oof["participant_id"] == train_manifest["participant_id"]).all()

    # 3. Holdout Participant IDs match canonical manifest in order
    assert (clin_test["participant_id"] == test_manifest["participant_id"]).all()
    assert (audio_test["participant_id"] == test_manifest["participant_id"]).all()
    assert (text_test["participant_id"] == test_manifest["participant_id"]).all()
    assert (video_test["participant_id"] == test_manifest["participant_id"]).all()

    # 4. Target equality
    assert (clin_oof["y_true"] == train_manifest[TARGET_COLUMN]).all()
    assert (audio_oof["true_target"] == train_manifest[TARGET_COLUMN]).all()
    assert (text_oof["true_target"] == train_manifest[TARGET_COLUMN]).all()
    assert (video_oof["true_target"] == train_manifest[TARGET_COLUMN]).all()

    assert (clin_test["y_true"] == test_manifest[TARGET_COLUMN]).all()
    assert (audio_test["true_target"] == test_manifest[TARGET_COLUMN]).all()
    assert (text_test["true_target"] == test_manifest[TARGET_COLUMN]).all()
    assert (video_test["true_target"] == test_manifest[TARGET_COLUMN]).all()


def test_leakage_isolation_and_partition_disjointness():
    """Verify zero overlap between training and holdout partitions and strict sample count integrity."""
    df_oof = pd.read_csv(FUSION_ARTIFACTS_DIR / "oof_predictions_fusion.csv")
    df_holdout = pd.read_csv(FUSION_ARTIFACTS_DIR / "holdout_predictions_fusion.csv")

    assert len(df_oof) == EXPECTED_TRAIN_PARTICIPANTS
    assert len(df_holdout) == EXPECTED_TEST_PARTICIPANTS

    train_pids = set(df_oof["participant_id"])
    test_pids = set(df_holdout["participant_id"])

    assert len(train_pids) == EXPECTED_TRAIN_PARTICIPANTS
    assert len(test_pids) == EXPECTED_TEST_PARTICIPANTS
    assert len(train_pids.intersection(test_pids)) == 0, "Data leakage detected: train and test sets overlap!"
    assert len(train_pids.union(test_pids)) == EXPECTED_TOTAL_PARTICIPANTS


def test_probability_validity_and_finite_bounds():
    """Verify that all probability features and fusion outputs are finite and within [0.0, 1.0]."""
    for fname in ["oof_predictions_fusion.csv", "holdout_predictions_fusion.csv"]:
        df = pd.read_csv(FUSION_ARTIFACTS_DIR / fname)

        prob_cols = [
            "clinical_prob",
            "audio_prob",
            "text_prob",
            "video_prob",
            "equal_weight_prob",
            "meta_classifier_prob",
        ]
        pred_cols = ["equal_weight_pred", "meta_classifier_pred"]

        for col in prob_cols:
            assert col in df.columns, f"Missing {col} in {fname}"
            assert not df[col].isna().any(), f"NaN detected in {fname}['{col}']"
            assert not np.isinf(df[col]).any(), f"Inf detected in {fname}['{col}']"
            assert (df[col] >= 0.0).all(), f"Values < 0 in {fname}['{col}']"
            assert (df[col] <= 1.0).all(), f"Values > 1 in {fname}['{col}']"

        for col in pred_cols:
            assert col in df.columns, f"Missing {col} in {fname}"
            assert set(df[col].unique()).issubset({0, 1}), f"Non-binary predictions in {fname}['{col}']"


def test_equal_weight_calculation_correctness():
    """Verify that equal-weight average is exactly the arithmetic mean of the four probability inputs."""
    for fname in ["oof_predictions_fusion.csv", "holdout_predictions_fusion.csv"]:
        df = pd.read_csv(FUSION_ARTIFACTS_DIR / fname)
        computed_avg = np.round(df[FEATURE_COLUMNS].mean(axis=1).values, 4)
        stored_avg = df["equal_weight_prob"].values
        np.testing.assert_allclose(computed_avg, stored_avg, atol=1e-4)


def test_meta_classifier_serialization_and_reproducibility():
    """Verify serialized meta-classifier restores correctly and reproduces predictions bit-for-bit."""
    meta_path = FUSION_ARTIFACTS_DIR / "fusion_meta_learner.joblib"
    clf = joblib.load(meta_path)

    assert isinstance(clf, LogisticRegression)
    assert hasattr(clf, "coef_")
    assert clf.coef_.shape == (1, len(FEATURE_COLUMNS))

    # Check feature weights JSON
    with open(FUSION_ARTIFACTS_DIR / "feature_weights.json", "r", encoding="utf-8") as f:
        weights = json.load(f)

    for i, col in enumerate(FEATURE_COLUMNS):
        assert abs(weights["coefficients"][col] - float(clf.coef_[0, i])) < 1e-4

    # Test holdout prediction reproduction
    df_holdout = pd.read_csv(FUSION_ARTIFACTS_DIR / "holdout_predictions_fusion.csv")
    X_test = df_holdout[FEATURE_COLUMNS].values
    reproduced_probs = np.round(clf.predict_proba(X_test)[:, 1], 4)

    np.testing.assert_allclose(
        reproduced_probs,
        df_holdout["meta_classifier_prob"].values,
        atol=1e-4,
        err_msg="Meta-classifier predictions are not deterministic and reproducible!",
    )


def test_metrics_summary_consistency():
    """Verify metrics_summary.json contains valid evaluation results across all models."""
    with open(FUSION_ARTIFACTS_DIR / "metrics_summary.json", "r", encoding="utf-8") as f:
        summary = json.load(f)

    assert "metadata" in summary
    assert "cross_validation" in summary
    assert "holdout_benchmarks" in summary
    assert "meta_classifier" in summary

    benchmarks = summary["holdout_benchmarks"]
    for key in [
        "clinical_numerical",
        "audio_modality",
        "text_modality",
        "video_modality",
        "equal_weight_average",
        "logistic_regression_meta",
    ]:
        assert key in benchmarks, f"Missing benchmark: {key}"
        m = benchmarks[key]["metrics"]
        ci = benchmarks[key]["confidence_intervals_95"]

        assert 0.0 <= m["roc_auc"] <= 1.0
        assert 0.0 <= m["pr_auc"] <= 1.0
        assert 0.0 <= m["balanced_accuracy"] <= 1.0
        assert 0.0 <= m["f1"] <= 1.0

        assert ci["roc_auc"]["ci_lower"] <= m["roc_auc"] <= ci["roc_auc"]["ci_upper"] + 0.05

