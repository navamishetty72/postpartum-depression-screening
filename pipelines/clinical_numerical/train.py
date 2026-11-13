"""Training and evaluation pipeline for clinical numerical baseline models.

Executes 5-fold Stratified CV on the training partition and unbiased holdout
test evaluation with non-parametric bootstrap confidence intervals.
"""

from pathlib import Path
from typing import Dict, Any, List
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from .config import (
    ARTIFACTS_DIR,
    CV_FOLDS,
    RANDOM_SEED,
    MODEL_CONFIGS,
    DECISION_THRESHOLD,
)
from .data_loader import load_clinical_data
from .preprocessor import ClinicalPreprocessor
from .models import get_model
from .metrics import compute_classification_metrics, compute_bootstrap_ci


def train_and_evaluate(
    artifacts_dir: Path = ARTIFACTS_DIR,
    save_artifacts: bool = True,
) -> Dict[str, Any]:
    """Train and evaluate all baseline classifiers with strict leakage isolation.

    Args:
        artifacts_dir: Directory where models, metrics, and predictions will be stored.
        save_artifacts: Whether to serialize artifacts to disk.

    Returns:
        Dictionary containing CV metrics, test metrics, and model summaries.
    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load data with participant validation
    X_train, y_train, manifest_train, X_test, y_test, manifest_test = load_clinical_data()

    y_train_arr = y_train.values.astype(int)
    y_test_arr = y_test.values.astype(int)

    # 2. Fit shared preprocessor exclusively on training set
    preprocessor = ClinicalPreprocessor()
    preprocessor.fit(X_train)
    X_train_trans = preprocessor.transform(X_train)
    X_test_trans = preprocessor.transform(X_test)

    if save_artifacts:
        preprocessor.save(artifacts_dir / "preprocessor.joblib")

    # Storage for all evaluation results
    results: Dict[str, Any] = {
        "metadata": {
            "random_seed": RANDOM_SEED,
            "cv_folds": CV_FOLDS,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_count_raw": X_train.shape[1],
            "feature_count_encoded": X_train_trans.shape[1],
        },
        "cross_validation": {},
        "holdout_test": {},
    }

    oof_predictions_df = pd.DataFrame({
        "participant_id": manifest_train["participant_id"],
        "sr": manifest_train["sr"],
        "y_true": y_train_arr,
    })

    test_predictions_df = pd.DataFrame({
        "participant_id": manifest_test["participant_id"],
        "sr": manifest_test["sr"],
        "y_true": y_test_arr,
    })

    # 3. Iterate over baseline models
    model_names = list(MODEL_CONFIGS.keys())
    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    for name in model_names:
        # Cross-validation setup
        oof_probs = np.zeros(len(y_train_arr), dtype=float)
        fold_metrics_list: List[Dict[str, Any]] = []

        for fold, (train_idx, val_idx) in enumerate(skf.split(X_train, y_train_arr), 1):
            # Strict fold-level preprocessing to eliminate any CV leakage
            fold_preprocessor = ClinicalPreprocessor()
            X_tr_fold = X_train.iloc[train_idx]
            y_tr_fold = y_train_arr[train_idx]
            X_val_fold = X_train.iloc[val_idx]
            y_val_fold = y_train_arr[val_idx]

            fold_preprocessor.fit(X_tr_fold)
            X_tr_fold_trans = fold_preprocessor.transform(X_tr_fold)
            X_val_fold_trans = fold_preprocessor.transform(X_val_fold)

            fold_model = get_model(name)
            fold_model.fit(X_tr_fold_trans, y_tr_fold)

            val_probs = fold_model.predict_proba(X_val_fold_trans)[:, 1]
            oof_probs[val_idx] = val_probs

            fold_metrics = compute_classification_metrics(y_val_fold, val_probs, threshold=DECISION_THRESHOLD)
            fold_metrics["fold"] = fold
            fold_metrics_list.append(fold_metrics)

        # Aggregate CV metrics across folds
        cv_summary = {
            metric: {
                "mean": round(float(np.mean([fm[metric] for fm in fold_metrics_list])), 4),
                "std": round(float(np.std([fm[metric] for fm in fold_metrics_list])), 4),
            }
            for metric in [
                "roc_auc",
                "pr_auc",
                "accuracy",
                "balanced_accuracy",
                "sensitivity",
                "specificity",
                "precision",
                "f1",
                "brier_score",
            ]
        }

        # Overall Out-of-Fold (OOF) pooled metrics
        oof_overall = compute_classification_metrics(y_train_arr, oof_probs, threshold=DECISION_THRESHOLD)

        results["cross_validation"][name] = {
            "summary_across_folds": cv_summary,
            "overall_oof_metrics": oof_overall,
            "fold_details": fold_metrics_list,
        }

        oof_predictions_df[f"{name}_prob"] = np.round(oof_probs, 4)
        oof_predictions_df[f"{name}_pred"] = (oof_probs >= DECISION_THRESHOLD).astype(int)

        # 4. Train final model on entire training set (640 records)
        final_model = get_model(name)
        final_model.fit(X_train_trans, y_train_arr)

        # 5. Evaluate final model ONCE on unseen holdout test set (160 records)
        test_probs = final_model.predict_proba(X_test_trans)[:, 1]
        test_metrics = compute_classification_metrics(y_test_arr, test_probs, threshold=DECISION_THRESHOLD)

        # Compute 95% Bootstrap Confidence Intervals on test set
        ci_roc_auc = compute_bootstrap_ci(y_test_arr, test_probs, "roc_auc", n_bootstraps=1000, seed=RANDOM_SEED)
        ci_pr_auc = compute_bootstrap_ci(y_test_arr, test_probs, "pr_auc", n_bootstraps=1000, seed=RANDOM_SEED)
        ci_f1 = compute_bootstrap_ci(y_test_arr, test_probs, "f1", n_bootstraps=1000, seed=RANDOM_SEED)
        ci_bal_acc = compute_bootstrap_ci(y_test_arr, test_probs, "balanced_accuracy", n_bootstraps=1000, seed=RANDOM_SEED)

        test_metrics["confidence_intervals_95"] = {
            "roc_auc": {"ci_lower": ci_roc_auc[0], "ci_upper": ci_roc_auc[1]},
            "pr_auc": {"ci_lower": ci_pr_auc[0], "ci_upper": ci_pr_auc[1]},
            "f1": {"ci_lower": ci_f1[0], "ci_upper": ci_f1[1]},
            "balanced_accuracy": {"ci_lower": ci_bal_acc[0], "ci_upper": ci_bal_acc[1]},
        }

        results["holdout_test"][name] = test_metrics

        test_predictions_df[f"{name}_prob"] = np.round(test_probs, 4)
        test_predictions_df[f"{name}_pred"] = (test_probs >= DECISION_THRESHOLD).astype(int)

        if save_artifacts:
            joblib.dump(final_model, artifacts_dir / f"{name}.joblib")

    # 6. Save tabular and JSON artifacts
    if save_artifacts:
        oof_predictions_df.to_csv(artifacts_dir / "oof_predictions.csv", index=False)
        test_predictions_df.to_csv(artifacts_dir / "test_predictions.csv", index=False)

        with open(artifacts_dir / "metrics_summary.json", "w") as f:
            json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    print("Executing clinical numerical pipeline training and evaluation...")
    results = train_and_evaluate()
    print("Execution complete. Model results summary:")
    for model_name, test_m in results["holdout_test"].items():
        cv_auc = results["cross_validation"][model_name]["summary_across_folds"]["roc_auc"]["mean"]
        test_auc = test_m["roc_auc"]
        test_f1 = test_m["f1"]
        print(f"[{model_name}] CV ROC-AUC: {cv_auc:.4f} | Test ROC-AUC: {test_auc:.4f} (95% CI: {test_m['confidence_intervals_95']['roc_auc']}) | Test F1: {test_f1:.4f}")

