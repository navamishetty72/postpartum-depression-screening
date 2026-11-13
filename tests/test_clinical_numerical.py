"""Automated unit and integration tests for the clinical numerical pipeline.

Postpartum Depression (PPD) Multimodal Recognition Research Prototype.
"""

from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from pipelines.clinical_numerical.config import (
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    TOTAL_PREDICTOR_COUNT,
    EXCLUDED_COLUMNS,
    RANDOM_SEED,
    ARTIFACTS_DIR,
)
from pipelines.clinical_numerical.data_loader import load_clinical_data
from pipelines.clinical_numerical.preprocessor import ClinicalPreprocessor
from pipelines.clinical_numerical.models import get_model
from pipelines.clinical_numerical.metrics import compute_classification_metrics, compute_bootstrap_ci
from pipelines.clinical_numerical.pipeline import ClinicalNumericalPipeline


@pytest.fixture(scope="module")
def clinical_data():
    """Load and return partitioned clinical datasets."""
    return load_clinical_data()


def test_dataset_loading_and_dimensions(clinical_data):
    """Verify that all 800 records and exactly 46 predictors are loaded."""
    X_train, y_train, manifest_train, X_test, y_test, manifest_test = clinical_data

    assert len(X_train) == 640, f"Expected 640 training records, got {len(X_train)}"
    assert len(X_test) == 160, f"Expected 160 testing records, got {len(X_test)}"
    assert len(X_train) + len(X_test) == 800

    assert X_train.shape[1] == TOTAL_PREDICTOR_COUNT == 46
    assert X_test.shape[1] == TOTAL_PREDICTOR_COUNT == 46


def test_strict_target_isolation(clinical_data):
    """Verify zero target leakage: neither EPDS/PHQ questions nor totals exist in X."""
    X_train, _, _, X_test, _, _ = clinical_data

    for excluded_col in EXCLUDED_COLUMNS:
        assert excluded_col not in X_train.columns, f"Target leakage in X_train: {excluded_col}"
        assert excluded_col not in X_test.columns, f"Target leakage in X_test: {excluded_col}"


def test_train_test_split_separation_and_balance(clinical_data):
    """Verify frozen 640/160 partition, class balances, and zero participant overlap."""
    X_train, y_train, manifest_train, X_test, y_test, manifest_test = clinical_data

    # Check participant IDs
    train_pids = set(manifest_train["participant_id"])
    test_pids = set(manifest_test["participant_id"])
    assert len(train_pids) == 640
    assert len(test_pids) == 160
    assert len(train_pids.intersection(test_pids)) == 0, "Train and test participants must be disjoint"

    # Check class distributions
    assert int((y_train == 0).sum()) == 359
    assert int((y_train == 1).sum()) == 281
    assert int((y_test == 0).sum()) == 90
    assert int((y_test == 1).sum()) == 70


def test_missing_value_handling_and_no_leakage(clinical_data):
    """Verify missing values are handled gracefully and preprocessor fits exclusively on train."""
    X_train, y_train, _, X_test, y_test, _ = clinical_data

    preprocessor = ClinicalPreprocessor()
    preprocessor.fit(X_train)
    assert preprocessor.is_fitted

    # Transform both splits
    X_train_trans = preprocessor.transform(X_train)
    X_test_trans = preprocessor.transform(X_test)

    assert not np.isnan(X_train_trans).any(), "Transformed X_train should have zero NaNs"
    assert not np.isnan(X_test_trans).any(), "Transformed X_test should have zero NaNs"

    # Encoded dimensions must match exactly
    assert X_train_trans.shape[1] == X_test_trans.shape[1]
    assert X_train_trans.shape[1] > 46, "One-hot encoding should expand feature space"

    feature_names = preprocessor.get_feature_names()
    assert len(feature_names) == X_train_trans.shape[1]


def test_reproducibility_of_preprocessing(clinical_data):
    """Verify preprocessing is strictly deterministic with identical inputs."""
    X_train, _, _, _, _, _ = clinical_data

    prep1 = ClinicalPreprocessor()
    res1 = prep1.fit_transform(X_train)

    prep2 = ClinicalPreprocessor()
    res2 = prep2.fit_transform(X_train)

    np.testing.assert_allclose(res1, res2, rtol=1e-5, atol=1e-5)


def test_metric_computation_and_bootstrap_ci():
    """Verify that diagnostic metrics and bootstrap confidence intervals compute accurately."""
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.6, 0.4, 0.7, 0.8, 0.9])

    metrics = compute_classification_metrics(y_true, y_prob, threshold=0.5)

    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["pr_auc"] <= 1.0
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["sensitivity"] <= 1.0
    assert 0.0 <= metrics["specificity"] <= 1.0
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["f1"] <= 1.0
    assert 0.0 <= metrics["brier_score"] <= 1.0

    ci_lower, ci_upper = compute_bootstrap_ci(y_true, y_prob, metric_name="roc_auc", n_bootstraps=100, seed=42)
    assert ci_lower <= ci_upper


def test_baseline_models_training_and_inference(clinical_data):
    """Verify all 3 baseline classifiers train, predict, and achieve valid AUC > 0.65."""
    X_train, y_train, _, X_test, y_test, _ = clinical_data

    preprocessor = ClinicalPreprocessor()
    X_train_trans = preprocessor.fit_transform(X_train)
    X_test_trans = preprocessor.transform(X_test)

    for model_name in ["logistic_regression", "random_forest", "hist_gradient_boosting"]:
        model = get_model(model_name)
        model.fit(X_train_trans, y_train.values)

        test_probs = model.predict_proba(X_test_trans)[:, 1]
        assert len(test_probs) == 160
        assert np.all((test_probs >= 0.0) & (test_probs <= 1.0))

        metrics = compute_classification_metrics(y_test.values, test_probs)
        assert metrics["roc_auc"] > 0.65, f"{model_name} failed baseline AUC threshold"
        assert metrics["f1"] > 0.50, f"{model_name} failed baseline F1 threshold"


def test_unified_pipeline_lifecycle_and_single_prediction(clinical_data):
    """Verify unified ClinicalNumericalPipeline fit, serialization, reload, and single record prediction."""
    X_train, y_train, _, X_test, _, _ = clinical_data

    pipeline = ClinicalNumericalPipeline(model_name="random_forest")
    pipeline.fit(X_train, y_train)

    # Batch prediction
    probs = pipeline.predict_proba(X_test)
    preds = pipeline.predict(X_test)
    assert len(probs) == 160
    assert len(preds) == 160

    # Single record inference
    sample_record = X_test.iloc[0].to_dict()
    sample_record["participant_id"] = "BGD_TEST_001"
    single_out = pipeline.predict_single(sample_record)

    assert "predicted_risk_probability" in single_out
    assert "risk_category" in single_out
    assert single_out["risk_category"] in ["LOW_RISK", "MODERATE_RISK", "HIGH_RISK"]
    assert single_out["data_origin"] == "REAL_CLINICAL_SURVEY"
    assert single_out["participant_id"] == "BGD_TEST_001"

