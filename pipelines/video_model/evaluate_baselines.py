"""Evaluation utilities and metrics computation for baseline video screening models.

Computes:
- ROC-AUC, PR-AUC (Average Precision)
- Balanced Accuracy, Precision, Recall, F1-Score
- Confusion Matrix & Class Prevalence
- Stratified non-parametric bootstrap 95% confidence intervals

SCIENTIFIC INTEGRITY NOTICE:
Synthetic Video V2 features are abstract numerical simulations. Video features alone
do not represent authentic patient observations or diagnostic biomarkers.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def compute_classification_metrics(
    y_true: Union[np.ndarray, List[int]],
    y_pred: Union[np.ndarray, List[int]],
    y_prob: Union[np.ndarray, List[float]],
) -> Dict[str, Any]:
    """Compute comprehensive diagnostic classification metrics.

    Args:
        y_true: Ground truth binary targets {0, 1}.
        y_pred: Predicted discrete binary classes {0, 1}.
        y_prob: Predicted positive-class probabilities [0.0, 1.0].

    Returns:
        Dict[str, Any]: Dictionary of evaluated metrics and confusion matrix.
    """
    y_true_arr = np.asarray(y_true).astype(int)
    y_pred_arr = np.asarray(y_pred).astype(int)
    y_prob_arr = np.asarray(y_prob).astype(float)

    if len(y_true_arr) == 0:
        raise ValueError("Cannot compute metrics on empty arrays.")

    n_total = len(y_true_arr)
    n_pos = int(np.sum(y_true_arr))
    n_neg = int(n_total - n_pos)
    prevalence = float(n_pos / n_total) if n_total > 0 else 0.0

    # ROC-AUC (requires at least one positive and one negative sample)
    if len(np.unique(y_true_arr)) > 1:
        roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))
        pr_auc = float(average_precision_score(y_true_arr, y_prob_arr))
    else:
        roc_auc = 0.5
        pr_auc = prevalence

    bal_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))
    prec = float(precision_score(y_true_arr, y_pred_arr, zero_division=0))
    rec = float(recall_score(y_true_arr, y_pred_arr, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred_arr, zero_division=0))

    # Confusion matrix
    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "balanced_accuracy": bal_acc,
        "precision": prec,
        "recall": rec,
        "f1_score": f1,
        "class_prevalence": prevalence,
        "total_samples": n_total,
        "positive_samples": n_pos,
        "negative_samples": n_neg,
        "confusion_matrix": {
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "tp": tp,
            "raw_matrix": cm.tolist(),
        },
    }


def compute_bootstrap_confidence_intervals(
    y_true: Union[np.ndarray, List[int]],
    y_pred: Union[np.ndarray, List[int]],
    y_prob: Union[np.ndarray, List[float]],
    n_bootstraps: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> Dict[str, Dict[str, float]]:
    """Compute non-parametric percentile bootstrap confidence intervals.

    Args:
        y_true: Ground truth binary targets {0, 1}.
        y_pred: Predicted discrete binary classes {0, 1}.
        y_prob: Predicted positive-class probabilities [0.0, 1.0].
        n_bootstraps: Number of bootstrap resamples (default: 1000).
        confidence_level: Two-sided confidence level (default: 0.95).
        seed: Random seed for reproducible resampling.

    Returns:
        Dict mapping each metric name to {"ci_lower": float, "ci_upper": float}.
    """
    y_true_arr = np.asarray(y_true).astype(int)
    y_pred_arr = np.asarray(y_pred).astype(int)
    y_prob_arr = np.asarray(y_prob).astype(float)

    n_samples = len(y_true_arr)
    rng = np.random.RandomState(seed)

    alpha = 1.0 - confidence_level
    lower_pct = (alpha / 2.0) * 100.0
    upper_pct = (1.0 - alpha / 2.0) * 100.0

    boot_roc_auc: List[float] = []
    boot_pr_auc: List[float] = []
    boot_bal_acc: List[float] = []
    boot_prec: List[float] = []
    boot_rec: List[float] = []
    boot_f1: List[float] = []

    pos_idx = np.where(y_true_arr == 1)[0]
    neg_idx = np.where(y_true_arr == 0)[0]

    for _ in range(n_bootstraps):
        # Stratified resampling to ensure both classes are represented in each resample
        boot_pos = rng.choice(pos_idx, size=len(pos_idx), replace=True)
        boot_neg = rng.choice(neg_idx, size=len(neg_idx), replace=True)
        idx = np.concatenate([boot_pos, boot_neg])

        yt = y_true_arr[idx]
        yp = y_pred_arr[idx]
        ypr = y_prob_arr[idx]

        if len(np.unique(yt)) > 1:
            boot_roc_auc.append(float(roc_auc_score(yt, ypr)))
            boot_pr_auc.append(float(average_precision_score(yt, ypr)))
        boot_bal_acc.append(float(balanced_accuracy_score(yt, yp)))
        boot_prec.append(float(precision_score(yt, yp, zero_division=0)))
        boot_rec.append(float(recall_score(yt, yp, zero_division=0)))
        boot_f1.append(float(f1_score(yt, yp, zero_division=0)))

    cis: Dict[str, Dict[str, float]] = {}
    metric_arrays = {
        "roc_auc": boot_roc_auc,
        "pr_auc": boot_pr_auc,
        "balanced_accuracy": boot_bal_acc,
        "precision": boot_prec,
        "recall": boot_rec,
        "f1_score": boot_f1,
    }

    for name, arr in metric_arrays.items():
        if len(arr) > 0:
            low = float(np.percentile(arr, lower_pct))
            high = float(np.percentile(arr, upper_pct))
            cis[name] = {"ci_lower": round(low, 4), "ci_upper": round(high, 4)}
        else:
            cis[name] = {"ci_lower": 0.0, "ci_upper": 0.0}

    return cis


def format_metrics_table(
    metrics: Dict[str, Any],
    cis: Optional[Dict[str, Dict[str, float]]] = None,
    title: str = "Evaluation Metrics",
) -> str:
    """Format metrics and confidence intervals as a GitHub-flavored Markdown table.

    Args:
        metrics: Dictionary returned by compute_classification_metrics.
        cis: Optional dictionary returned by compute_bootstrap_confidence_intervals.
        title: Title header for the table.

    Returns:
        Formatted markdown table string.
    """
    lines: List[str] = [
        f"### {title}",
        "",
        "| Metric | Value | 95% Confidence Interval |",
        "| :--- | :---: | :---: |",
    ]

    metric_labels = [
        ("roc_auc", "ROC-AUC"),
        ("pr_auc", "PR-AUC (Average Precision)"),
        ("balanced_accuracy", "Balanced Accuracy"),
        ("f1_score", "F1-Score"),
        ("precision", "Precision"),
        ("recall", "Recall / Sensitivity"),
    ]

    for key, label in metric_labels:
        val = metrics.get(key, 0.0)
        if cis and key in cis:
            ci_str = f"[{cis[key]['ci_lower']:.4f}, {cis[key]['ci_upper']:.4f}]"
        else:
            ci_str = "N/A"
        lines.append(f"| {label} | {val:.4f} | {ci_str} |")

    lines.extend([
        "",
        f"- **Total Participants**: {metrics.get('total_samples')}",
        f"- **Prevalence**: {metrics.get('class_prevalence', 0.0):.2%} ({metrics.get('positive_samples')} positive / {metrics.get('negative_samples')} negative)",
    ])

    cm = metrics.get("confusion_matrix", {})
    if "tp" in cm:
        lines.extend([
            f"- **Confusion Matrix**: TP={cm['tp']}, FP={cm['fp']}, TN={cm['tn']}, FN={cm['fn']}",
        ])

    return "\n".join(lines)


def save_metrics_to_json(metrics: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """Save metrics dictionary to a formatted JSON file."""
    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

