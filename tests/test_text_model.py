"""Unit and integration test suite for the text PPD classification baseline model.

Validates:
1. Participant ID and split alignment against canonical manifest (640 train / 160 test).
2. Feature selection and strict target leakage prevention.
3. 5-Fold Stratified cross-validation separation and zero inter-fold overlap.
4. Out-of-fold prediction coverage ($N=640$), schema, and threshold consistency.
5. Holdout test set isolation ($N=160$), class balance (90 neg / 70 pos), and predictions.
6. Deterministic reproducibility under fixed seed.
7. Output artifacts schema, serialization integrity, and inference contract.
"""

import json
from pathlib import Path
from typing import Dict, List
import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from pipelines.synthetic_text.train_text_model import (
    ARTIFACTS_DIR,
    CV_FOLDS,
    DECISION_THRESHOLD,
    EXPECTED_TEST_PARTICIPANTS,
    EXPECTED_TOTAL_PARTICIPANTS,
    EXPECTED_TRAIN_PARTICIPANTS,
    PARTICIPANT_ID_COLUMN,
    RANDOM_SEED,
    SPLIT_COLUMN,
    SPLIT_MANIFEST_PATH,
    TARGET_COLUMN,
    TEXT_MANIFEST_PATH,
    create_text_pipeline,
    load_and_validate_data,
    train_text_model,
)

EXPECTED_ARTIFACT_FILES: List[str] = [
    "text_pipeline.joblib",
    "tfidf_vectorizer.joblib",
    "logistic_regression.joblib",
    "oof_predictions.csv",
    "test_predictions.csv",
    "metrics_summary.json",
    "training_report.md",
]


@pytest.fixture(scope="module")
def text_artifacts() -> Path:
    """Fixture ensuring text baseline artifacts exist, training if necessary."""
    missing = [f for f in EXPECTED_ARTIFACT_FILES if not (ARTIFACTS_DIR / f).is_file()]
    if missing:
        train_text_model(artifacts_dir=ARTIFACTS_DIR, save_artifacts=True)
    return ARTIFACTS_DIR


@pytest.fixture(scope="module")
def datasets() -> tuple:
    """Fixture providing loaded train and test datasets."""
    return load_and_validate_data()


# ==============================================================================
# 1. Participant Alignment and Split Integrity
# ==============================================================================
def test_1_participant_alignment(datasets: tuple) -> None:
    """Requirement: All 800 participants are mapped to the canonical 640/160 split."""
    train_df, test_df = datasets
    split_manifest = pd.read_csv(SPLIT_MANIFEST_PATH)

    assert len(train_df) == EXPECTED_TRAIN_PARTICIPANTS == 640
    assert len(test_df) == EXPECTED_TEST_PARTICIPANTS == 160
    assert (len(train_df) + len(test_df)) == EXPECTED_TOTAL_PARTICIPANTS == 800

    # Ensure zero overlap
    train_pids = set(train_df[PARTICIPANT_ID_COLUMN])
    test_pids = set(test_df[PARTICIPANT_ID_COLUMN])
    assert len(train_pids) == 640
    assert len(test_pids) == 160
    assert len(train_pids.intersection(test_pids)) == 0

    # Verify matching split manifest assignments
    train_canon = set(
        split_manifest[split_manifest[SPLIT_COLUMN] == "train"][PARTICIPANT_ID_COLUMN]
    )
    test_canon = set(
        split_manifest[split_manifest[SPLIT_COLUMN] == "test"][PARTICIPANT_ID_COLUMN]
    )
    assert train_pids == train_canon
    assert test_pids == test_canon


# ==============================================================================
# 2. Feature Selection & Target Isolation
# ==============================================================================
def test_2_feature_selection_and_leakage_prevention(datasets: tuple) -> None:
    """Requirement: Input consists strictly of raw narrative text strings without labels or IDs."""
    train_df, test_df = datasets

    for df in (train_df, test_df):
        assert "narrative_text" in df.columns
        for text in df["narrative_text"]:
            assert isinstance(text, str)
            assert len(text.strip()) > 100
            # Ensure participant ID is not leaked into the text body
            assert "BGD_" not in text
            assert "participant_id" not in text
            # Ensure target labels are not in text body
            assert "target_canonical_epds_ge_13" not in text

    # Verify target column is strictly binary integer
    assert set(train_df[TARGET_COLUMN].unique()).issubset({0, 1})
    assert set(test_df[TARGET_COLUMN].unique()).issubset({0, 1})


# ==============================================================================
# 3. Cross-Validation Fold Disjointness
# ==============================================================================
def test_3_fold_separation_and_zero_overlap(text_artifacts: Path) -> None:
    """Requirement: 5 Stratified folds partition the 640 training participants without overlap."""
    oof_df = pd.read_csv(text_artifacts / "oof_predictions.csv")

    assert "fold" in oof_df.columns
    folds = sorted(oof_df["fold"].unique().tolist())
    assert folds == list(range(1, CV_FOLDS + 1))

    fold_pid_sets = [
        set(oof_df[oof_df["fold"] == f][PARTICIPANT_ID_COLUMN]) for f in folds
    ]

    total_fold_samples = sum(len(s) for s in fold_pid_sets)
    assert total_fold_samples == EXPECTED_TRAIN_PARTICIPANTS == 640

    for i in range(len(folds)):
        for j in range(i + 1, len(folds)):
            overlap = fold_pid_sets[i].intersection(fold_pid_sets[j])
            assert len(overlap) == 0, f"Leakage detected between fold {folds[i]} and {folds[j]}"


# ==============================================================================
# 4. Out-of-Fold Coverage and Schema
# ==============================================================================
def test_4_oof_coverage_and_schema(text_artifacts: Path) -> None:
    """Requirement: Out-of-fold predictions cover all 640 training participants with valid probabilities."""
    oof_df = pd.read_csv(text_artifacts / "oof_predictions.csv")

    assert len(oof_df) == EXPECTED_TRAIN_PARTICIPANTS == 640
    assert oof_df[PARTICIPANT_ID_COLUMN].nunique() == 640

    required_cols = [
        PARTICIPANT_ID_COLUMN,
        SPLIT_COLUMN,
        "true_target",
        "fold",
        "predicted_probability",
        "predicted_class",
    ]
    for col in required_cols:
        assert col in oof_df.columns, f"Missing required column '{col}' in oof_predictions.csv"

    # Probabilities bounded in [0, 1]
    assert (oof_df["predicted_probability"] >= 0.0).all()
    assert (oof_df["predicted_probability"] <= 1.0).all()
    assert set(oof_df["predicted_class"].unique()).issubset({0, 1})

    # Exact threshold alignment: pred == (prob >= 0.5)
    expected_pred = (oof_df["predicted_probability"] >= DECISION_THRESHOLD).astype(int)
    assert (oof_df["predicted_class"] == expected_pred).all()


# ==============================================================================
# 5. Holdout Test Isolation & Class Balance
# ==============================================================================
def test_5_holdout_isolation_and_balance(text_artifacts: Path) -> None:
    """Requirement: Holdout test set has 160 participants, canonical class balance, valid predictions."""
    test_df = pd.read_csv(text_artifacts / "test_predictions.csv")

    assert len(test_df) == EXPECTED_TEST_PARTICIPANTS == 160
    assert test_df[PARTICIPANT_ID_COLUMN].nunique() == 160

    # Canonical test class distribution: 90 negative (0), 70 positive (1)
    class_counts = test_df["true_target"].value_counts().to_dict()
    assert class_counts.get(0) == 90, f"Expected 90 class 0 in test, got {class_counts.get(0)}"
    assert class_counts.get(1) == 70, f"Expected 70 class 1 in test, got {class_counts.get(1)}"

    assert (test_df["predicted_probability"] >= 0.0).all()
    assert (test_df["predicted_probability"] <= 1.0).all()
    assert set(test_df["predicted_class"].unique()).issubset({0, 1})

    expected_pred = (test_df["predicted_probability"] >= DECISION_THRESHOLD).astype(int)
    assert (test_df["predicted_class"] == expected_pred).all()


# ==============================================================================
# 6. Deterministic Reproducibility
# ==============================================================================
def test_6_reproducibility() -> None:
    """Requirement: Training runs with fixed random seed produce identical metrics."""
    res1 = train_text_model(save_artifacts=False)
    res2 = train_text_model(save_artifacts=False)

    auc1 = res1["cross_validation"]["summary_across_folds"]["roc_auc"]["mean"]
    auc2 = res2["cross_validation"]["summary_across_folds"]["roc_auc"]["mean"]
    assert auc1 == auc2, f"Discrepancy in CV ROC-AUC: {auc1} vs {auc2}"

    test_auc1 = res1["holdout_test"]["roc_auc"]
    test_auc2 = res2["holdout_test"]["roc_auc"]
    assert test_auc1 == test_auc2, f"Discrepancy in test ROC-AUC: {test_auc1} vs {test_auc2}"


# ==============================================================================
# 7. Output Artifacts Schemas and Integrity
# ==============================================================================
def test_7_output_artifacts_schemas_and_integrity(text_artifacts: Path) -> None:
    """Requirement: All required model, data, metric, and report files exist, loadable, and non-empty."""
    for fname in EXPECTED_ARTIFACT_FILES:
        p = text_artifacts / fname
        assert p.is_file(), f"Missing artifact {fname} at {p}"
        assert p.stat().st_size > 0, f"Artifact {fname} is empty"

    # Load pipeline and test inference contract
    pipeline = joblib.load(text_artifacts / "text_pipeline.joblib")
    assert isinstance(pipeline, Pipeline)

    # Test single-string prediction
    sample_text = ["A mother navigating domestic infant routines with family assistance."]
    probs = pipeline.predict_proba(sample_text)
    assert probs.shape == (1, 2)
    assert 0.0 <= probs[0, 1] <= 1.0

    # Verify metrics JSON structure
    with open(text_artifacts / "metrics_summary.json", "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert "metadata" in metrics
    assert "cross_validation" in metrics
    assert "holdout_test" in metrics
    assert metrics["metadata"]["random_seed"] == RANDOM_SEED
    assert metrics["metadata"]["train_samples"] == 640
    assert metrics["metadata"]["test_samples"] == 160

    test_info = metrics["holdout_test"]
    assert "roc_auc" in test_info
    assert "pr_auc" in test_info
    assert "f1" in test_info
    assert "confidence_intervals_95" in test_info
    ci = test_info["confidence_intervals_95"]["roc_auc"]
    assert 0.0 <= ci["ci_lower"] <= ci["ci_upper"] <= 1.0

    # Verify markdown report
    report_text = (text_artifacts / "training_report.md").read_text(encoding="utf-8")
    assert "Supervised Text-Based PPD Classification Baseline Report" in report_text
    assert "Scientific Integrity & Modality Disclaimer" in report_text
    assert "Out-of-Fold Confusion Matrix" in report_text
    assert "Top Learned TF-IDF Vocabulary Features" in report_text

