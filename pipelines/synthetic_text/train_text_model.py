"""Training and evaluation pipeline for text narrative PPD classification baseline.

Postpartum Depression (PPD) Multimodal Recognition Research Prototype.

SCIENTIFIC INTEGRITY & METHODOLOGICAL NOTICE:
Architectural Benchmark Only: The Bangladeshi clinical survey cohort contains ZERO authentic
qualitative patient interview transcripts, audio recordings, or clinical intake notes.
The narrative text files in data/synthetic/text/narratives/ are fictional contextual vignettes
generated from 13 non-target demographic and domestic survey covariates.
The binary labels (target_canonical_epds_ge_13) originate from authentic clinical EPDS
questionnaire responses from the maternal survey.
This baseline learns statistical associations between the simulated domestic context
and clinical screening risk. It does NOT represent genuine patient language patterns
and cannot be used for clinical diagnostic purposes.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

# -----------------------------------------------------------------------------
# Configuration Constants
# -----------------------------------------------------------------------------
RANDOM_SEED: int = 42
CV_FOLDS: int = 5
DECISION_THRESHOLD: float = 0.5
EXPECTED_TRAIN_PARTICIPANTS: int = 640
EXPECTED_TEST_PARTICIPANTS: int = 160
EXPECTED_TOTAL_PARTICIPANTS: int = 800

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
TEXT_MANIFEST_PATH: Path = PROJECT_ROOT / "data" / "synthetic" / "text" / "text_manifest.csv"
SPLIT_MANIFEST_PATH: Path = (
    PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"
)
NARRATIVES_DIR: Path = PROJECT_ROOT / "data" / "synthetic" / "text" / "narratives"
ARTIFACTS_DIR: Path = PROJECT_ROOT / "models" / "text_model"

PARTICIPANT_ID_COLUMN: str = "participant_id"
SPLIT_COLUMN: str = "split_partition"
TARGET_COLUMN: str = "target_canonical_epds_ge_13"

# TF-IDF Specification
TFIDF_CONFIG: Dict[str, Any] = {
    "ngram_range": (1, 2),
    "min_df": 3,
    "max_features": 1000,
    "sublinear_tf": True,
}

# Logistic Regression Specification
LOGISTIC_CONFIG: Dict[str, Any] = {
    "C": 0.5,
    "penalty": "l2",
    "solver": "lbfgs",
    "class_weight": "balanced",
    "random_state": RANDOM_SEED,
    "max_iter": 1000,
}


def create_text_pipeline() -> Pipeline:
    """Build a scikit-learn Pipeline encapsulating TF-IDF and Logistic Regression."""
    return Pipeline([
        ("tfidf", TfidfVectorizer(**TFIDF_CONFIG)),
        ("classifier", LogisticRegression(**LOGISTIC_CONFIG)),
    ])


def load_and_validate_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load text and split manifests, merge on participant_id, and load raw narrative text.

    Returns:
        Tuple of (train_df, test_df) with verified schemas and text contents.
    """
    if not TEXT_MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing text manifest at {TEXT_MANIFEST_PATH}")
    if not SPLIT_MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing split manifest at {SPLIT_MANIFEST_PATH}")

    df_text = pd.read_csv(TEXT_MANIFEST_PATH)
    df_split = pd.read_csv(SPLIT_MANIFEST_PATH)

    if len(df_text) != EXPECTED_TOTAL_PARTICIPANTS:
        raise ValueError(f"Expected {EXPECTED_TOTAL_PARTICIPANTS} text records, got {len(df_text)}")
    if len(df_split) != EXPECTED_TOTAL_PARTICIPANTS:
        raise ValueError(f"Expected {EXPECTED_TOTAL_PARTICIPANTS} split records, got {len(df_split)}")

    merged = pd.merge(
        df_text,
        df_split[[PARTICIPANT_ID_COLUMN, TARGET_COLUMN, SPLIT_COLUMN]],
        on=PARTICIPANT_ID_COLUMN,
        suffixes=("_text", "_split"),
        how="inner",
    )

    if len(merged) != EXPECTED_TOTAL_PARTICIPANTS:
        raise ValueError(f"Merged manifest row count mismatch: {len(merged)}")

    # Verify partition alignment
    if (merged[f"{SPLIT_COLUMN}_text"] != merged[f"{SPLIT_COLUMN}_split"]).any():
        mismatches = merged[merged[f"{SPLIT_COLUMN}_text"] != merged[f"{SPLIT_COLUMN}_split"]][
            PARTICIPANT_ID_COLUMN
        ].tolist()
        raise ValueError(f"Partition mismatch between manifests for: {mismatches[:5]}")

    merged[SPLIT_COLUMN] = merged[f"{SPLIT_COLUMN}_split"]

    # Load narrative text directly from narrative files
    narratives: List[str] = []
    for _, row in merged.iterrows():
        rel_path = row["narrative_file_path"]
        abs_path = PROJECT_ROOT / rel_path
        if not abs_path.is_file():
            raise FileNotFoundError(f"Narrative file missing for {row[PARTICIPANT_ID_COLUMN]}: {abs_path}")
        text_content = abs_path.read_text(encoding="utf-8").strip()
        if not text_content:
            raise ValueError(f"Empty narrative text for {row[PARTICIPANT_ID_COLUMN]} at {abs_path}")
        narratives.append(text_content)

    merged["narrative_text"] = narratives

    train_df = (
        merged[merged[SPLIT_COLUMN] == "train"].copy().reset_index(drop=True)
    )
    test_df = (
        merged[merged[SPLIT_COLUMN] == "test"].copy().reset_index(drop=True)
    )

    if len(train_df) != EXPECTED_TRAIN_PARTICIPANTS:
        raise ValueError(f"Expected {EXPECTED_TRAIN_PARTICIPANTS} train samples, got {len(train_df)}")
    if len(test_df) != EXPECTED_TEST_PARTICIPANTS:
        raise ValueError(f"Expected {EXPECTED_TEST_PARTICIPANTS} test samples, got {len(test_df)}")

    # Check for zero participant ID overlap
    overlap = set(train_df[PARTICIPANT_ID_COLUMN]).intersection(set(test_df[PARTICIPANT_ID_COLUMN]))
    if overlap:
        raise ValueError(f"Train/test participant ID overlap detected: {overlap}")

    return train_df, test_df


def compute_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = DECISION_THRESHOLD,
) -> Dict[str, Any]:
    """Compute comprehensive classification performance metrics."""
    y_pred = (y_prob >= threshold).astype(int)

    roc_auc = float(roc_auc_score(y_true, y_prob))
    pr_auc = float(average_precision_score(y_true, y_prob))
    acc = float(accuracy_score(y_true, y_pred))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    brier = float(brier_score_loss(y_true, y_prob))

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = [int(v) for v in cm.ravel()]

    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "sensitivity": round(rec, 4),
        "specificity": round(spec, 4),
        "precision": round(prec, 4),
        "f1": round(f1, 4),
        "brier_score": round(brier, 4),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "sample_count": int(len(y_true)),
        "positive_count": int(np.sum(y_true == 1)),
        "negative_count": int(np.sum(y_true == 0)),
        "decision_threshold": threshold,
    }


def compute_bootstrap_ci(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    metric_name: str,
    n_bootstraps: int = 1000,
    alpha: float = 0.95,
    random_seed: int = RANDOM_SEED,
) -> Tuple[float, float]:
    """Compute 95% non-parametric bootstrap confidence interval."""
    rng = np.random.RandomState(random_seed)
    n_samples = len(y_true)
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


def generate_training_report_markdown(
    results: Dict[str, Any],
    top_positive_features: List[Tuple[str, float]],
    top_negative_features: List[Tuple[str, float]],
    classification_rep: str,
) -> str:
    """Generate comprehensive Markdown training report for text baseline."""
    meta = results["metadata"]
    cv = results["cross_validation"]["summary_across_folds"]
    oof = results["cross_validation"]["overall_oof_metrics"]
    test = results["holdout_test"]
    ci = test["confidence_intervals_95"]

    pos_rows = "\n".join(
        [f"| `{feat}` | +{weight:.4f} |" for feat, weight in top_positive_features[:10]]
    )
    neg_rows = "\n".join(
        [f"| `{feat}` | {weight:.4f} |" for feat, weight in top_negative_features[:10]]
    )

    return f"""# Supervised Text-Based PPD Classification Baseline Report

## 1. Executive Summary & Scientific Provenance
- **Modality:** Text (Synthetic Maternal Narratives)
- **Architecture:** `TfidfVectorizer` (1–2 grams, max 1000 features, sublinear TF) + `LogisticRegression` ($L_2$, $C=0.5$, balanced)
- **Target Label:** `target_canonical_epds_ge_13` (Binary: 1 = EPDS $\\ge 13$ High Risk, 0 = Low Risk)
- **Cohort:** 800 participants (640 Train / 160 Untouched Holdout Test)
- **Date Trained (UTC):** `{meta['timestamp']}`
- **Random Seed:** `{meta['random_seed']}`

> [!IMPORTANT]
> **Scientific Integrity & Modality Disclaimer:**
> The original clinical survey in Bangladesh collected structured numerical/categorical data, but **did not record authentic patient interview transcripts, audio files, or clinical intake notes**.
> The narrative text inputs in `data/synthetic/text/narratives/` are **fictional contextual vignettes** conditioned on 13 non-target demographic and domestic survey covariates.
> The binary classification target is **authentic clinical ground truth** derived from the administered 10-item EPDS instruments.
> This model learns statistical associations between the simulated maternal domestic context and clinical screening risk. It does **not** reflect authentic patient vocabulary or clinical language patterns and does not constitute a clinically validated diagnostic device.

---

## 2. 5-Fold Cross-Validation Performance ($N=640$ Training Cohort)

Vectorization was fit strictly inside each fold to ensure zero feature leakage across partitions.

| Metric | Fold Mean $\\pm$ SD | Overall Out-of-Fold ($N=640$) |
| :--- | :--- | :--- |
| **ROC-AUC** | **{cv['roc_auc']['mean']:.4f} $\\pm$ {cv['roc_auc']['std']:.4f}** | **{oof['roc_auc']:.4f}** |
| **PR-AUC** | {cv['pr_auc']['mean']:.4f} $\\pm$ {cv['pr_auc']['std']:.4f} | {oof['pr_auc']:.4f} |
| **Balanced Accuracy** | {cv['balanced_accuracy']['mean']:.4f} $\\pm$ {cv['balanced_accuracy']['std']:.4f} | {oof['balanced_accuracy']:.4f} |
| **Accuracy** | {cv['accuracy']['mean']:.4f} $\\pm$ {cv['accuracy']['std']:.4f} | {oof['accuracy']:.4f} |
| **Sensitivity (Recall)** | {cv['sensitivity']['mean']:.4f} $\\pm$ {cv['sensitivity']['std']:.4f} | {oof['sensitivity']:.4f} |
| **Specificity** | {cv['specificity']['mean']:.4f} $\\pm$ {cv['specificity']['std']:.4f} | {oof['specificity']:.4f} |
| **Precision** | {cv['precision']['mean']:.4f} $\\pm$ {cv['precision']['std']:.4f} | {oof['precision']:.4f} |
| **F1 Score** | {cv['f1']['mean']:.4f} $\\pm$ {cv['f1']['std']:.4f} | {oof['f1']:.4f} |
| **Brier Score** | {cv['brier_score']['mean']:.4f} $\\pm$ {cv['brier_score']['std']:.4f} | {oof['brier_score']:.4f} |

### Out-of-Fold Confusion Matrix ($N=640$)
- **True Negatives (TN):** {oof['confusion_matrix']['tn']}
- **False Positives (FP):** {oof['confusion_matrix']['fp']}
- **False Negatives (FN):** {oof['confusion_matrix']['fn']}
- **True Positives (TP):** {oof['confusion_matrix']['tp']}

---

## 3. Single-Shot Holdout Test Performance ($N=160$ Untouched Cohort)

Evaluated exactly once on the untouched holdout test partition (90 Negative, 70 Positive).

| Metric | Point Estimate | 95% Bootstrap Confidence Interval |
| :--- | :--- | :--- |
| **ROC-AUC** | **{test['roc_auc']:.4f}** | **[{ci['roc_auc']['ci_lower']:.4f}, {ci['roc_auc']['ci_upper']:.4f}]** |
| **PR-AUC** | **{test['pr_auc']:.4f}** | [{ci['pr_auc']['ci_lower']:.4f}, {ci['pr_auc']['ci_upper']:.4f}] |
| **Balanced Accuracy** | **{test['balanced_accuracy']:.4f}** | [{ci['balanced_accuracy']['ci_lower']:.4f}, {ci['balanced_accuracy']['ci_upper']:.4f}] |
| **Accuracy** | {test['accuracy']:.4f} | - |
| **Sensitivity** | {test['sensitivity']:.4f} ({test['confusion_matrix']['tp']}/70) | - |
| **Specificity** | {test['specificity']:.4f} ({test['confusion_matrix']['tn']}/90) | - |
| **Precision** | {test['precision']:.4f} | - |
| **F1 Score** | **{test['f1']:.4f}** | [{ci['f1']['ci_lower']:.4f}, {ci['f1']['ci_upper']:.4f}] |
| **Brier Score** | {test['brier_score']:.4f} | - |

### Holdout Confusion Matrix ($N=160$)
| | Predicted Negative (0) | Predicted Positive (1) |
| :--- | :--- | :--- |
| **Actual Negative (0)** | **{test['confusion_matrix']['tn']}** (TN) | {test['confusion_matrix']['fp']} (FP) |
| **Actual Positive (1)** | {test['confusion_matrix']['fn']} (FN) | **{test['confusion_matrix']['tp']}** (TP) |

### Detailed Classification Report (Holdout Test)
```
{classification_rep}
```

---

## 4. Top Learned TF-IDF Vocabulary Features

### Indicators Associated with Elevated PPD Risk (Positive Coefficients)
| Feature (N-Gram) | Logistic Weight |
| :--- | :--- |
{pos_rows}

### Indicators Associated with Low PPD Risk (Negative Coefficients)
| Feature (N-Gram) | Logistic Weight |
| :--- | :--- |
{neg_rows}

---

## 5. Artifact Manifest & Multimodal Fusion Readiness
The following production artifacts have been generated in `models/text_model/`:
- `text_pipeline.joblib`: Serialized end-to-end `Pipeline([('tfidf', ...), ('classifier', ...)])`
- `tfidf_vectorizer.joblib`: Standalone fitted vectorizer (1000 features)
- `logistic_regression.joblib`: Standalone fitted classifier
- `oof_predictions.csv`: 640 training participants $\times$ out-of-fold probability vectors
- `test_predictions.csv`: 160 holdout test participants $\times$ single-shot holdout prediction vectors
- `metrics_summary.json`: Machine-readable performance metrics and bootstrap CIs

**Multimodal Fusion Milestone:** With the completion of this text classification baseline, all four modalities (Clinical Numerical, Video Facial Dynamics, Audio Acoustics, and Maternal Narrative Text) now generate aligned out-of-fold probability vectors across all 800 participants for four-modality late fusion integration.
"""


def train_text_model(
    artifacts_dir: Path = ARTIFACTS_DIR,
    save_artifacts: bool = True,
) -> Dict[str, Any]:
    """Train and evaluate the text PPD classification baseline.

    Args:
        artifacts_dir: Target directory for serialized model artifacts.
        save_artifacts: Whether to serialize pipeline and prediction artifacts.

    Returns:
        Dictionary of cross-validation and holdout evaluation metrics.
    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    train_df, test_df = load_and_validate_data()

    X_train = train_df["narrative_text"].tolist()
    y_train = train_df[TARGET_COLUMN].values.astype(int)

    X_test = test_df["narrative_text"].tolist()
    y_test = test_df[TARGET_COLUMN].values.astype(int)

    results: Dict[str, Any] = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "random_seed": RANDOM_SEED,
            "cv_folds": CV_FOLDS,
            "decision_threshold": DECISION_THRESHOLD,
            "tfidf_config": TFIDF_CONFIG,
            "logistic_config": LOGISTIC_CONFIG,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "provenance_notice": (
                "SYNTHETIC_FICTIONAL_NARRATIVE: Narrative text generated from non-target "
                "survey covariates; labels derived from authentic clinical EPDS responses."
            ),
        },
        "cross_validation": {},
        "holdout_test": {},
    }

    # Prepare OOF prediction tracking
    oof_probs = np.zeros(len(y_train), dtype=float)
    fold_assignments = np.zeros(len(y_train), dtype=int)
    fold_metrics_list: List[Dict[str, Any]] = []

    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    # 1. 5-Fold Stratified Cross-Validation on 640 Training Participants
    for fold_idx, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train), 1):
        fold_assignments[val_idx] = fold_idx

        X_tr_fold = [X_train[i] for i in tr_idx]
        y_tr_fold = y_train[tr_idx]

        X_val_fold = [X_train[i] for i in val_idx]
        y_val_fold = y_train[val_idx]

        fold_pipeline = create_text_pipeline()
        fold_pipeline.fit(X_tr_fold, y_tr_fold)

        val_probs = fold_pipeline.predict_proba(X_val_fold)[:, 1]
        oof_probs[val_idx] = val_probs

        fold_m = compute_metrics(y_val_fold, val_probs, threshold=DECISION_THRESHOLD)
        fold_m["fold"] = fold_idx
        fold_metrics_list.append(fold_m)

    # Aggregate CV summary across folds
    metric_keys = [
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
    summary_across_folds: Dict[str, Dict[str, float]] = {}
    for k in metric_keys:
        vals = [fm[k] for fm in fold_metrics_list]
        summary_across_folds[k] = {
            "mean": round(float(np.mean(vals)), 4),
            "std": round(float(np.std(vals)), 4),
        }

    overall_oof_metrics = compute_metrics(y_train, oof_probs, threshold=DECISION_THRESHOLD)

    results["cross_validation"] = {
        "summary_across_folds": summary_across_folds,
        "overall_oof_metrics": overall_oof_metrics,
        "fold_details": fold_metrics_list,
    }

    # Prepare OOF Predictions DataFrame (with boundary-consistent rounded predictions)
    rounded_oof_probs = np.round(oof_probs, 4)
    oof_predictions_df = pd.DataFrame({
        PARTICIPANT_ID_COLUMN: train_df[PARTICIPANT_ID_COLUMN],
        SPLIT_COLUMN: "train",
        "true_target": y_train,
        "fold": fold_assignments,
        "predicted_probability": rounded_oof_probs,
        "predicted_class": (rounded_oof_probs >= DECISION_THRESHOLD).astype(int),
        "logistic_regression_prob": rounded_oof_probs,
        "logistic_regression_pred": (rounded_oof_probs >= DECISION_THRESHOLD).astype(int),
    })

    # 2. Fit Final Pipeline on All 640 Training Participants
    final_pipeline = create_text_pipeline()
    final_pipeline.fit(X_train, y_train)

    # 3. Single-Shot Holdout Evaluation on Untouched 160 Records
    test_probs = final_pipeline.predict_proba(X_test)[:, 1]
    test_metrics = compute_metrics(y_test, test_probs, threshold=DECISION_THRESHOLD)

    # 95% Bootstrap Confidence Intervals on Holdout
    ci_roc = compute_bootstrap_ci(y_test, test_probs, "roc_auc")
    ci_pr = compute_bootstrap_ci(y_test, test_probs, "pr_auc")
    ci_f1 = compute_bootstrap_ci(y_test, test_probs, "f1")
    ci_bal = compute_bootstrap_ci(y_test, test_probs, "balanced_accuracy")

    test_metrics["confidence_intervals_95"] = {
        "roc_auc": {"ci_lower": ci_roc[0], "ci_upper": ci_roc[1]},
        "pr_auc": {"ci_lower": ci_pr[0], "ci_upper": ci_pr[1]},
        "f1": {"ci_lower": ci_f1[0], "ci_upper": ci_f1[1]},
        "balanced_accuracy": {"ci_lower": ci_bal[0], "ci_upper": ci_bal[1]},
    }
    results["holdout_test"] = test_metrics

    # Prepare Holdout Predictions DataFrame (boundary-consistent)
    rounded_test_probs = np.round(test_probs, 4)
    test_predictions_df = pd.DataFrame({
        PARTICIPANT_ID_COLUMN: test_df[PARTICIPANT_ID_COLUMN],
        SPLIT_COLUMN: "test",
        "true_target": y_test,
        "predicted_probability": rounded_test_probs,
        "predicted_class": (rounded_test_probs >= DECISION_THRESHOLD).astype(int),
        "logistic_regression_prob": rounded_test_probs,
        "logistic_regression_pred": (rounded_test_probs >= DECISION_THRESHOLD).astype(int),
    })

    # Extract Feature Weights for Interpretability
    vectorizer: TfidfVectorizer = final_pipeline.named_steps["tfidf"]
    classifier: LogisticRegression = final_pipeline.named_steps["classifier"]
    feature_names = vectorizer.get_feature_names_out()
    coefs = classifier.coef_[0]

    sorted_indices = np.argsort(coefs)
    top_negative_features = [
        (feature_names[i], float(coefs[i])) for i in sorted_indices[:20]
    ]
    top_positive_features = [
        (feature_names[i], float(coefs[i])) for i in sorted_indices[-20:][::-1]
    ]

    test_preds = (rounded_test_probs >= DECISION_THRESHOLD).astype(int)
    classification_rep = classification_report(
        y_test,
        test_preds,
        target_names=["Low Risk (0)", "High Risk (1)"],
        digits=4,
    )

    # 4. Serialize Artifacts
    if save_artifacts:
        joblib.dump(final_pipeline, artifacts_dir / "text_pipeline.joblib")
        joblib.dump(vectorizer, artifacts_dir / "tfidf_vectorizer.joblib")
        joblib.dump(classifier, artifacts_dir / "logistic_regression.joblib")

        oof_predictions_df.to_csv(artifacts_dir / "oof_predictions.csv", index=False)
        test_predictions_df.to_csv(artifacts_dir / "test_predictions.csv", index=False)

        with open(artifacts_dir / "metrics_summary.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        report_md = generate_training_report_markdown(
            results=results,
            top_positive_features=top_positive_features,
            top_negative_features=top_negative_features,
            classification_rep=classification_rep,
        )
        (artifacts_dir / "training_report.md").write_text(report_md, encoding="utf-8")

    return results


if __name__ == "__main__":
    print("Executing supervised text baseline model training and evaluation...")
    metrics = train_text_model()
    cv_mean = metrics["cross_validation"]["summary_across_folds"]["roc_auc"]["mean"]
    test_roc = metrics["holdout_test"]["roc_auc"]
    test_ci = metrics["holdout_test"]["confidence_intervals_95"]["roc_auc"]
    print("Training complete. Holdout test summary:")
    print(f"5-Fold CV Mean ROC-AUC: {cv_mean:.4f}")
    print(f"Holdout ROC-AUC: {test_roc:.4f} (95% CI: [{test_ci['ci_lower']:.4f}, {test_ci['ci_upper']:.4f}])")
    print(f"Holdout F1: {metrics['holdout_test']['f1']:.4f}")
    print(f"Holdout Balanced Acc: {metrics['holdout_test']['balanced_accuracy']:.4f}")

