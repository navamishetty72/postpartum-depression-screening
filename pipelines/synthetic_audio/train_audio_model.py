"""Training and evaluation pipeline for acoustic feature audio classification baselines.

Postpartum Depression (PPD) Multimodal Recognition Research Prototype.

SCIENTIFIC INTEGRITY NOTICE:
Architectural Benchmark Only: The Bangladeshi clinical survey cohort contains ZERO physical
audio recordings. The synthetic audio feature profiles used here are computationally conditioned
fixtures derived from non-target clinical covariates. They exist solely to benchmark multimodal
fusion architectures and stress-test pipeline integration. They do NOT represent genuine clinical
observations and cannot validate real-world clinical diagnostic efficacy.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
# pyrefly: ignore[missing-import]
import joblib
# pyrefly: ignore[missing-import]
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

# Reproducibility & Pipeline Defaults
RANDOM_SEED: int = 42
CV_FOLDS: int = 5
DECISION_THRESHOLD: float = 0.5

# Repository Paths
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
AUDIO_MANIFEST_PATH: Path = PROJECT_ROOT / "data" / "synthetic" / "audio" / "audio_manifest.csv"
SPLIT_MANIFEST_PATH: Path = (
    PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"
)
ARTIFACTS_DIR: Path = PROJECT_ROOT / "models" / "audio_model"

# Exactly 7 physiological acoustic summary features
ACOUSTIC_FEATURES: List[str] = [
    "f0_mean_hz",
    "f0_std_hz",
    "jitter_local_percent",
    "shimmer_local_percent",
    "hnr_db",
    "speech_rate_syllables_per_sec",
    "pause_ratio",
]

TARGET_COLUMN: str = "target_canonical_epds_ge_13"
PARTICIPANT_ID_COLUMN: str = "participant_id"
SPLIT_COLUMN: str = "split_partition"

EXPECTED_TOTAL_PARTICIPANTS: int = 800
EXPECTED_TRAIN_PARTICIPANTS: int = 640
EXPECTED_TEST_PARTICIPANTS: int = 160


def load_and_prepare_audio_data(
    audio_manifest_path: Path = AUDIO_MANIFEST_PATH,
    split_manifest_path: Path = SPLIT_MANIFEST_PATH,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]:
    """Load, validate, and partition audio summary features with canonical split alignment.

    Args:
        audio_manifest_path: Path to synthetic audio manifest CSV.
        split_manifest_path: Path to authoritative train/test split manifest CSV.

    Returns:
        Tuple of (X_train, y_train, manifest_train, X_test, y_test, manifest_test).

    Raises:
        ValueError: If record counts, feature schema, or participant alignment fail.
    """
    if not audio_manifest_path.is_file():
        raise FileNotFoundError(f"Audio manifest not found at {audio_manifest_path}")
    if not split_manifest_path.is_file():
        raise FileNotFoundError(f"Split manifest not found at {split_manifest_path}")

    audio_df = pd.read_csv(audio_manifest_path)
    split_df = pd.read_csv(split_manifest_path)

    # 1. Dimensionality and Participant Verification
    if len(audio_df) != EXPECTED_TOTAL_PARTICIPANTS:
        raise ValueError(
            f"Expected {EXPECTED_TOTAL_PARTICIPANTS} records in audio manifest, got {len(audio_df)}"
        )
    if len(split_df) != EXPECTED_TOTAL_PARTICIPANTS:
        raise ValueError(
            f"Expected {EXPECTED_TOTAL_PARTICIPANTS} records in split manifest, got {len(split_df)}"
        )

    # Validate exact participant ID alignment in original order
    if audio_df[PARTICIPANT_ID_COLUMN].tolist() != split_df[PARTICIPANT_ID_COLUMN].tolist():
        raise ValueError("Participant ID ordering mismatch between audio and split manifests.")

    # 2. Merge canonical target and split assignment
    merged_df = pd.merge(
        audio_df,
        split_df[[PARTICIPANT_ID_COLUMN, TARGET_COLUMN, SPLIT_COLUMN]],
        on=PARTICIPANT_ID_COLUMN,
        suffixes=("_audio", ""),
    )

    if len(merged_df) != EXPECTED_TOTAL_PARTICIPANTS:
        raise ValueError(f"Merged audio dataset row count divergence: {len(merged_df)}")

    # Verify features exist and have zero nulls
    missing_feats = [f for f in ACOUSTIC_FEATURES if f not in merged_df.columns]
    if missing_feats:
        raise ValueError(f"Missing required acoustic features in manifest: {missing_feats}")
    if merged_df[ACOUSTIC_FEATURES].isnull().any().any():
        raise ValueError("Null or NaN values detected in acoustic features.")

    # 3. Partitioning
    train_mask = merged_df[SPLIT_COLUMN] == "train"
    test_mask = merged_df[SPLIT_COLUMN] == "test"

    train_df = merged_df[train_mask].copy().reset_index(drop=True)
    test_df = merged_df[test_mask].copy().reset_index(drop=True)

    if len(train_df) != EXPECTED_TRAIN_PARTICIPANTS:
        raise ValueError(
            f"Expected {EXPECTED_TRAIN_PARTICIPANTS} train participants, got {len(train_df)}"
        )
    if len(test_df) != EXPECTED_TEST_PARTICIPANTS:
        raise ValueError(
            f"Expected {EXPECTED_TEST_PARTICIPANTS} test participants, got {len(test_df)}"
        )

    # Disjointness check
    train_pids = set(train_df[PARTICIPANT_ID_COLUMN])
    test_pids = set(test_df[PARTICIPANT_ID_COLUMN])
    if not train_pids.isdisjoint(test_pids):
        raise ValueError("Overlap detected between training and test participant IDs.")

    # Class balance check
    if train_df[TARGET_COLUMN].value_counts().to_dict() != {0: 359, 1: 281}:
        raise ValueError(
            f"Unexpected train class distribution: {train_df[TARGET_COLUMN].value_counts().to_dict()}"
        )
    if test_df[TARGET_COLUMN].value_counts().to_dict() != {0: 90, 1: 70}:
        raise ValueError(
            f"Unexpected test class distribution: {test_df[TARGET_COLUMN].value_counts().to_dict()}"
        )

    # Feature isolation: X strictly contains the 7 acoustic features
    X_train = train_df[ACOUSTIC_FEATURES].copy()
    y_train = train_df[TARGET_COLUMN].copy()
    X_test = test_df[ACOUSTIC_FEATURES].copy()
    y_test = test_df[TARGET_COLUMN].copy()

    return X_train, y_train, train_df, X_test, y_test, test_df


def compute_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = DECISION_THRESHOLD,
) -> Dict[str, Any]:
    """Compute binary classification metrics for screening models."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    y_pred = (y_prob >= threshold).astype(int)

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    sensitivity = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0

    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc_auc = 0.5

    try:
        pr_auc = float(average_precision_score(y_true, y_prob))
    except Exception:
        pr_auc = 0.0

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 4),
        "sensitivity": round(sensitivity, 4),
        "specificity": round(specificity, 4),
        "precision": round(precision, 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "brier_score": round(float(brier_score_loss(y_true, y_prob)), 4),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
        "sample_count": len(y_true),
        "positive_count": int(tp + fn),
        "negative_count": int(tn + fp),
        "decision_threshold": threshold,
    }


def compute_bootstrap_ci(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    metric_name: str = "roc_auc",
    n_bootstraps: int = 1000,
    alpha: float = 0.95,
    seed: int = RANDOM_SEED,
) -> Tuple[float, float]:
    """Compute empirical non-parametric bootstrap confidence interval for a metric."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    n_samples = len(y_true)
    rng = np.random.RandomState(seed)

    bootstrapped_scores: List[float] = []
    for _ in range(n_bootstraps):
        indices = rng.randint(0, n_samples, n_samples)
        if len(np.unique(y_true[indices])) < 2:
            continue
        y_t = y_true[indices]
        y_p = y_prob[indices]
        y_hat = (y_p >= DECISION_THRESHOLD).astype(int)

        if metric_name == "roc_auc":
            score = roc_auc_score(y_t, y_p)
        elif metric_name == "pr_auc":
            score = average_precision_score(y_t, y_p)
        elif metric_name == "f1":
            score = f1_score(y_t, y_hat, zero_division=0)
        elif metric_name == "balanced_accuracy":
            score = balanced_accuracy_score(y_t, y_hat)
        else:
            raise ValueError(f"Unsupported metric for bootstrap: {metric_name}")
        bootstrapped_scores.append(float(score))

    if not bootstrapped_scores:
        return 0.0, 0.0

    lower_p = ((1.0 - alpha) / 2.0) * 100
    upper_p = (alpha + ((1.0 - alpha) / 2.0)) * 100
    ci_lower = float(np.percentile(bootstrapped_scores, lower_p))
    ci_upper = float(np.percentile(bootstrapped_scores, upper_p))
    return round(ci_lower, 4), round(ci_upper, 4)


def create_model(model_name: str) -> Any:
    """Create fresh baseline model instance with fixed seed."""
    if model_name == "logistic_regression":
        return LogisticRegression(
            penalty="l2",
            C=0.1,
            solver="lbfgs",
            class_weight="balanced",
            random_state=RANDOM_SEED,
            max_iter=1000,
        )
    elif model_name == "random_forest":
        return RandomForestClassifier(
            n_estimators=100,
            max_depth=4,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=RANDOM_SEED,
        )
    else:
        raise ValueError(f"Unknown model name: {model_name}")


def train_audio_models(
    artifacts_dir: Path = ARTIFACTS_DIR,
    save_artifacts: bool = True,
) -> Dict[str, Any]:
    """Execute 5-fold cross-validation and holdout evaluation for audio models.

    Args:
        artifacts_dir: Destination directory for model weights and prediction tables.
        save_artifacts: Whether to serialize artifacts to disk.

    Returns:
        Dictionary of cross-validation and holdout test metrics.
    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    X_train, y_train, manifest_train, X_test, y_test, manifest_test = load_and_prepare_audio_data()

    y_train_arr = y_train.values.astype(int)
    y_test_arr = y_test.values.astype(int)

    results: Dict[str, Any] = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "random_seed": RANDOM_SEED,
            "cv_folds": CV_FOLDS,
            "decision_threshold": DECISION_THRESHOLD,
            "features": ACOUSTIC_FEATURES,
            "feature_count": len(ACOUSTIC_FEATURES),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "provenance_notice": (
                "CLINICALLY_CONDITIONED_SYNTHETIC: Generated acoustic feature profiles, "
                "not authentic patient recordings."
            ),
        },
        "cross_validation": {},
        "holdout_test": {},
    }

    oof_predictions_df = pd.DataFrame({
        PARTICIPANT_ID_COLUMN: manifest_train[PARTICIPANT_ID_COLUMN],
        SPLIT_COLUMN: "train",
        "true_target": y_train_arr,
        "fold": 0,
    })

    test_predictions_df = pd.DataFrame({
        PARTICIPANT_ID_COLUMN: manifest_test[PARTICIPANT_ID_COLUMN],
        SPLIT_COLUMN: "test",
        "true_target": y_test_arr,
    })

    model_names = ["logistic_regression", "random_forest"]
    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    # 1. 5-Fold Stratified Cross-Validation on Training Partition
    for name in model_names:
        oof_probs = np.zeros(len(y_train_arr), dtype=float)
        fold_assignments = np.zeros(len(y_train_arr), dtype=int)
        fold_metrics_list: List[Dict[str, Any]] = []

        for fold_idx, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train_arr), 1):
            fold_assignments[val_idx] = fold_idx

            # Strict fold-level standardization to isolate validation folds
            scaler = StandardScaler()
            X_tr_fold = scaler.fit_transform(X_train.iloc[tr_idx])
            X_val_fold = scaler.transform(X_train.iloc[val_idx])

            y_tr_fold = y_train_arr[tr_idx]
            y_val_fold = y_train_arr[val_idx]

            fold_model = create_model(name)
            fold_model.fit(X_tr_fold, y_tr_fold)

            val_probs = fold_model.predict_proba(X_val_fold)[:, 1]
            oof_probs[val_idx] = val_probs

            fold_m = compute_metrics(y_val_fold, val_probs, threshold=DECISION_THRESHOLD)
            fold_m["fold"] = fold_idx
            fold_metrics_list.append(fold_m)

        rounded_oof = np.round(oof_probs, 4)
        oof_predictions_df["fold"] = fold_assignments
        oof_predictions_df[f"{name}_prob"] = rounded_oof
        oof_predictions_df[f"{name}_pred"] = (rounded_oof >= DECISION_THRESHOLD).astype(int)

        # Aggregate CV summary across folds
        cv_summary: Dict[str, Dict[str, float]] = {}
        for metric_key in [
            "roc_auc",
            "pr_auc",
            "accuracy",
            "balanced_accuracy",
            "sensitivity",
            "specificity",
            "precision",
            "f1",
            "brier_score",
        ]:
            vals = [fm[metric_key] for fm in fold_metrics_list]
            cv_summary[metric_key] = {
                "mean": round(float(np.mean(vals)), 4),
                "std": round(float(np.std(vals)), 4),
            }

        pooled_oof_m = compute_metrics(y_train_arr, oof_probs, threshold=DECISION_THRESHOLD)

        results["cross_validation"][name] = {
            "summary_across_folds": cv_summary,
            "overall_oof_metrics": pooled_oof_m,
            "fold_details": fold_metrics_list,
        }

        # 2. Final Model Training on Full 640 Records
        final_scaler = StandardScaler()
        X_train_scaled = final_scaler.fit_transform(X_train)
        X_test_scaled = final_scaler.transform(X_test)

        final_model = create_model(name)
        final_model.fit(X_train_scaled, y_train_arr)

        # 3. Single-Shot Holdout Evaluation on Untouched 160 Records
        test_probs = final_model.predict_proba(X_test_scaled)[:, 1]
        test_metrics = compute_metrics(y_test_arr, test_probs, threshold=DECISION_THRESHOLD)

        # 95% Bootstrap Confidence Intervals on Holdout
        ci_roc = compute_bootstrap_ci(y_test_arr, test_probs, "roc_auc")
        ci_pr = compute_bootstrap_ci(y_test_arr, test_probs, "pr_auc")
        ci_f1 = compute_bootstrap_ci(y_test_arr, test_probs, "f1")
        ci_bal = compute_bootstrap_ci(y_test_arr, test_probs, "balanced_accuracy")

        test_metrics["confidence_intervals_95"] = {
            "roc_auc": {"ci_lower": ci_roc[0], "ci_upper": ci_roc[1]},
            "pr_auc": {"ci_lower": ci_pr[0], "ci_upper": ci_pr[1]},
            "f1": {"ci_lower": ci_f1[0], "ci_upper": ci_f1[1]},
            "balanced_accuracy": {"ci_lower": ci_bal[0], "ci_upper": ci_bal[1]},
        }

        results["holdout_test"][name] = test_metrics

        rounded_test = np.round(test_probs, 4)
        test_predictions_df[f"{name}_prob"] = rounded_test
        test_predictions_df[f"{name}_pred"] = (rounded_test >= DECISION_THRESHOLD).astype(int)

        if save_artifacts:
            joblib.dump(final_model, artifacts_dir / f"{name}.joblib")

    if save_artifacts:
        joblib.dump(final_scaler, artifacts_dir / "scaler.joblib")
        oof_predictions_df.to_csv(artifacts_dir / "oof_predictions.csv", index=False)
        test_predictions_df.to_csv(artifacts_dir / "test_predictions.csv", index=False)
        with open(artifacts_dir / "metrics_summary.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    print("Executing audio baseline model training and evaluation...")
    res = train_audio_models()
    print("Training complete. Holdout test summary:")
    for m_name, test_info in res["holdout_test"].items():
        cv_auc = res["cross_validation"][m_name]["summary_across_folds"]["roc_auc"]["mean"]
        test_auc = test_info["roc_auc"]
        test_f1 = test_info["f1"]
        print(
            f"[{m_name}] CV ROC-AUC: {cv_auc:.4f} | "
            f"Holdout ROC-AUC: {test_auc:.4f} (95% CI: {test_info['confidence_intervals_95']['roc_auc']}) | "
            f"Holdout F1: {test_f1:.4f}"
        )

