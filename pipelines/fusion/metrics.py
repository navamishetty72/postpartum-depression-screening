"""Evaluation metrics and statistical bootstrapping module for multimodal fusion."""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
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


def compute_classification_metrics(
    y_true: Union[np.ndarray, List[int]],
    y_prob: Union[np.ndarray, List[float]],
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Compute comprehensive diagnostic, ranking, and calibration metrics.

    Args:
        y_true: Binary ground truth targets (0 or 1).
        y_prob: Predicted probabilities for the positive class (class 1).
        threshold: Decision threshold for discrete classification (default: 0.5).

    Returns:
        Dictionary of performance metrics.
    """
    y_true_arr = np.asarray(y_true).astype(int)
    y_prob_arr = np.asarray(y_prob).astype(float)
    y_pred_arr = (y_prob_arr >= threshold).astype(int)

    n_total = len(y_true_arr)
    n_pos = int(np.sum(y_true_arr))
    n_neg = int(n_total - n_pos)

    # Confusion Matrix
    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    # Diagnostic Rates
    sensitivity = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = sensitivity

    # Balanced Accuracy: (Sensitivity + Specificity) / 2
    balanced_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))
    acc = float(accuracy_score(y_true_arr, y_pred_arr))
    f1 = float(f1_score(y_true_arr, y_pred_arr, zero_division=0))

    # Ranking curves
    try:
        if len(np.unique(y_true_arr)) > 1:
            roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))
            pr_auc = float(average_precision_score(y_true_arr, y_prob_arr))
        else:
            roc_auc = 0.5
            pr_auc = float(n_pos / max(1, n_total))
    except Exception:
        roc_auc = 0.5
        pr_auc = 0.0

    brier = float(brier_score_loss(y_true_arr, y_prob_arr))

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "sensitivity": round(sensitivity, 4),
        "specificity": round(specificity, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "balanced_accuracy": round(balanced_acc, 4),
        "accuracy": round(acc, 4),
        "brier_score": round(brier, 4),
        "confusion_matrix": {
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "tp": tp,
            "raw_matrix": [[tn, fp], [fn, tp]],
        },
        "sample_count": n_total,
        "positive_count": n_pos,
        "negative_count": n_neg,
        "decision_threshold": threshold,
    }


def compute_bootstrap_confidence_intervals(
    y_true: Union[np.ndarray, List[int]],
    y_prob: Union[np.ndarray, List[float]],
    threshold: float = 0.5,
    n_bootstraps: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> Dict[str, Dict[str, float]]:
    """Compute empirical non-parametric bootstrap confidence intervals for all metrics.

    Args:
        y_true: Binary ground truth targets.
        y_prob: Predicted positive class probabilities.
        threshold: Decision threshold for discrete classification.
        n_bootstraps: Number of bootstrap iterations (default: 1000).
        confidence_level: Desired coverage probability (default: 0.95).
        seed: Random seed for reproducibility.

    Returns:
        Dictionary mapping metric names to {'ci_lower': ..., 'ci_upper': ...}.
    """
    y_true_arr = np.asarray(y_true).astype(int)
    y_prob_arr = np.asarray(y_prob).astype(float)
    n = len(y_true_arr)

    rng = np.random.RandomState(seed)
    alpha = (1.0 - confidence_level) / 2.0
    lower_pct = alpha * 100.0
    upper_pct = (1.0 - alpha) * 100.0

    boot_metrics: Dict[str, List[float]] = {
        "roc_auc": [],
        "pr_auc": [],
        "sensitivity": [],
        "specificity": [],
        "precision": [],
        "f1": [],
        "balanced_accuracy": [],
        "accuracy": [],
    }

    for _ in range(n_bootstraps):
        boot_idx = rng.randint(0, n, size=n)
        y_true_b = y_true_arr[boot_idx]
        y_prob_b = y_prob_arr[boot_idx]

        # Require both classes in bootstrap sample for ranking metrics
        if len(np.unique(y_true_b)) < 2:
            continue

        y_pred_b = (y_prob_b >= threshold).astype(int)
        cm = confusion_matrix(y_true_b, y_pred_b, labels=[0, 1])
        tn, fp, fn, tp = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]

        sens = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        f1_val = float(f1_score(y_true_b, y_pred_b, zero_division=0))
        bal_acc = (sens + spec) / 2.0
        acc_val = float(accuracy_score(y_true_b, y_pred_b))

        try:
            roc_val = float(roc_auc_score(y_true_b, y_prob_b))
        except Exception:
            roc_val = 0.5

        try:
            pr_val = float(average_precision_score(y_true_b, y_prob_b))
        except Exception:
            pr_val = 0.0

        boot_metrics["roc_auc"].append(roc_val)
        boot_metrics["pr_auc"].append(pr_val)
        boot_metrics["sensitivity"].append(sens)
        boot_metrics["specificity"].append(spec)
        boot_metrics["precision"].append(prec)
        boot_metrics["f1"].append(f1_val)
        boot_metrics["balanced_accuracy"].append(bal_acc)
        boot_metrics["accuracy"].append(acc_val)

    ci_dict: Dict[str, Dict[str, float]] = {}
    for metric_name, vals in boot_metrics.items():
        if len(vals) > 0:
            lo = float(np.percentile(vals, lower_pct))
            hi = float(np.percentile(vals, upper_pct))
        else:
            lo, hi = 0.0, 0.0
        ci_dict[metric_name] = {
            "ci_lower": round(lo, 4),
            "ci_upper": round(hi, 4),
        }

    return ci_dict

