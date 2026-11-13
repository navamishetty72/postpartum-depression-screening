"""Evaluation metrics module for the clinical numerical pipeline.

Computes comprehensive diagnostic, ranking, and calibration metrics
along with bootstrap confidence intervals.
"""

from typing import Dict, Any, Tuple, Optional, Callable
import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
    confusion_matrix,
)


def compute_classification_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Compute comprehensive performance metrics for binary screening models.

    Args:
        y_true: Ground truth binary targets (0 or 1).
        y_prob: Predicted probabilities for the positive class (class 1).
        threshold: Decision threshold for discrete classification (default: 0.5).

    Returns:
        Dictionary of performance metrics.
    """
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    y_pred = (y_prob >= threshold).astype(int)

    # Confusion matrix components
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    # Diagnostic rates
    sensitivity = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0

    # Probabilistic curves
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
    seed: int = 42,
) -> Tuple[float, float]:
    """Compute empirical non-parametric bootstrap confidence interval for a metric.

    Args:
        y_true: Binary ground truth array.
        y_prob: Predicted positive class probabilities.
        metric_name: One of 'roc_auc', 'pr_auc', 'f1', 'accuracy', 'balanced_accuracy'.
        n_bootstraps: Number of bootstrap resamples (default: 1000).
        alpha: Confidence level (default: 0.95 for 95% CI).
        seed: Random seed for reproducible bootstrapping.

    Returns:
        Tuple of (ci_lower, ci_upper).
    """
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    rng = np.random.RandomState(seed)

    bootstrapped_scores = []
    n_samples = len(y_true)

    for _ in range(n_bootstraps):
        indices = rng.randint(0, n_samples, n_samples)
        if len(np.unique(y_true[indices])) < 2:
            # Skip degenerate single-class resamples
            continue

        sample_true = y_true[indices]
        sample_prob = y_prob[indices]
        sample_pred = (sample_prob >= 0.5).astype(int)

        if metric_name == "roc_auc":
            score = roc_auc_score(sample_true, sample_prob)
        elif metric_name == "pr_auc":
            score = average_precision_score(sample_true, sample_prob)
        elif metric_name == "f1":
            score = f1_score(sample_true, sample_pred, zero_division=0)
        elif metric_name == "accuracy":
            score = accuracy_score(sample_true, sample_pred)
        elif metric_name == "balanced_accuracy":
            score = balanced_accuracy_score(sample_true, sample_pred)
        else:
            raise ValueError(f"Unsupported metric for bootstrapping: {metric_name}")

        bootstrapped_scores.append(score)

    if not bootstrapped_scores:
        return (0.0, 0.0)

    lower_pct = ((1.0 - alpha) / 2.0) * 100
    upper_pct = (alpha + (1.0 - alpha) / 2.0) * 100

    ci_lower = float(np.percentile(bootstrapped_scores, lower_pct))
    ci_upper = float(np.percentile(bootstrapped_scores, upper_pct))

    return round(ci_lower, 4), round(ci_upper, 4)

