"""Evaluation and embedding extraction utilities for recurrent video models (GRU and BiLSTM).

Provides:
- PyTorch evaluation loop for batched variable-length sequences.
- Metric calculation (ROC-AUC, PR-AUC, Balanced Accuracy, Precision, Recall, F1, Confusion Matrix).
- Non-parametric bootstrap 95% confidence intervals.
- Fixed 128-dimensional participant embedding extraction for multimodal late fusion.

SCIENTIFIC INTEGRITY NOTICE:
Synthetic Video V2 features are abstract numerical simulations. Video features alone
do not represent authentic patient observations or diagnostic biomarkers.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from pipelines.video_model.evaluate_baselines import (
    compute_bootstrap_confidence_intervals,
    compute_classification_metrics,
)


def evaluate_model(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: Optional[nn.Module] = None,
    device: Union[str, torch.device] = "cpu",
) -> Dict[str, Any]:
    """Evaluate a recurrent video model on a batched DataLoader.

    Args:
        model: Trained VideoGRUModel or VideoBiLSTMModel instance.
        dataloader: DataLoader yielding collated batches (from pad_collate_fn).
        criterion: Optional loss module (e.g. nn.BCEWithLogitsLoss).
        device: Device to run evaluation on (default: 'cpu').

    Returns:
        Dict[str, Any] containing:
            - 'loss': Average loss over all batches (or 0.0 if no criterion).
            - 'metrics': Classification metrics dictionary.
            - 'predictions_df': DataFrame with participant_id, true_target, predicted_label, predicted_probability.
            - 'embeddings': (N, 128) float32 numpy array of participant embeddings.
    """
    model.eval()
    dev = torch.device(device)
    model.to(dev)

    total_loss = 0.0
    total_samples = 0

    all_pids: List[str] = []
    all_targets: List[int] = []
    all_probs: List[float] = []
    all_preds: List[int] = []
    all_embeddings: List[np.ndarray] = []

    with torch.no_grad():
        for batch in dataloader:
            features = batch["features"].to(dev)
            padding_mask = batch["padding_mask"].to(dev)
            tracking_mask = batch["tracking_mask"].to(dev)
            sequence_lengths = batch["sequence_lengths"].to(dev)
            targets = batch["targets"].to(dev)
            pids = batch["participant_ids"]

            # Forward pass requesting both logits and 128-dim embedding
            out = model(
                features=features,
                padding_mask=padding_mask,
                tracking_mask=tracking_mask,
                sequence_lengths=sequence_lengths,
                return_embedding=True,
            )

            logits = out["logits"].squeeze(-1)  # (B,)
            embeddings = out["embedding"].cpu().numpy()  # (B, 128)

            if criterion is not None:
                loss = criterion(logits, targets.float())
                batch_size = targets.size(0)
                total_loss += float(loss.item()) * batch_size
                total_samples += batch_size

            probs = torch.sigmoid(logits).cpu().numpy()
            preds = (probs >= 0.5).astype(int)

            all_pids.extend(pids)
            all_targets.extend(targets.cpu().numpy().tolist())
            all_probs.extend(probs.tolist())
            all_preds.extend(preds.tolist())
            all_embeddings.append(embeddings)

    avg_loss = (total_loss / total_samples) if total_samples > 0 else 0.0
    metrics = compute_classification_metrics(all_targets, all_preds, all_probs)
    emb_matrix = np.vstack(all_embeddings) if len(all_embeddings) > 0 else np.zeros((0, 128), dtype=np.float32)

    df_preds = pd.DataFrame({
        "participant_id": all_pids,
        "true_target": all_targets,
        "predicted_label": all_preds,
        "predicted_probability": np.round(all_probs, 4),
    })

    return {
        "loss": avg_loss,
        "metrics": metrics,
        "predictions_df": df_preds,
        "embeddings": emb_matrix,
    }


def extract_embeddings_only(
    model: nn.Module,
    dataloader: DataLoader,
    device: Union[str, torch.device] = "cpu",
) -> Tuple[np.ndarray, List[str], np.ndarray]:
    """Extract participant embeddings directly from model encoder.

    Args:
        model: VideoGRUModel or VideoBiLSTMModel instance.
        dataloader: DataLoader yielding collated batches.
        device: Device to run on ('cpu').

    Returns:
        Tuple of:
            - embeddings: (N, 128) float32 numpy array.
            - participant_ids: List[str] of length N.
            - targets: (N,) int numpy array.
    """
    model.eval()
    dev = torch.device(device)
    model.to(dev)

    all_embeddings: List[np.ndarray] = []
    all_pids: List[str] = []
    all_targets: List[int] = []

    with torch.no_grad():
        for batch in dataloader:
            features = batch["features"].to(dev)
            padding_mask = batch["padding_mask"].to(dev)
            tracking_mask = batch["tracking_mask"].to(dev)
            sequence_lengths = batch["sequence_lengths"].to(dev)
            targets = batch["targets"]
            pids = batch["participant_ids"]

            emb = model.extract_embedding(
                features=features,
                padding_mask=padding_mask,
                tracking_mask=tracking_mask,
                sequence_lengths=sequence_lengths,
            )

            all_embeddings.append(emb.cpu().numpy())
            all_pids.extend(pids)
            all_targets.extend(targets.numpy().tolist())

    emb_mat = np.vstack(all_embeddings) if len(all_embeddings) > 0 else np.zeros((0, 128), dtype=np.float32)
    return emb_mat, all_pids, np.array(all_targets, dtype=int)


def evaluate_holdout_with_confidence_intervals(
    model: nn.Module,
    test_dataloader: DataLoader,
    seed: int = 42,
    device: Union[str, torch.device] = "cpu",
) -> Dict[str, Any]:
    """Evaluate trained model on holdout set and compute bootstrap 95% confidence intervals.

    Args:
        model: Trained recurrent model.
        test_dataloader: DataLoader for frozen holdout test set.
        seed: Random seed for bootstrap reproducibility.
        device: Device to run evaluation on.

    Returns:
        Dict with metrics, confidence intervals, predictions DataFrame, and holdout embeddings.
    """
    res = evaluate_model(model, test_dataloader, device=device)
    df_preds = res["predictions_df"]

    y_true = df_preds["true_target"].values
    y_pred = df_preds["predicted_label"].values
    y_prob = df_preds["predicted_probability"].values

    cis = compute_bootstrap_confidence_intervals(
        y_true=y_true,
        y_pred=y_pred,
        y_prob=y_prob,
        n_bootstraps=1000,
        seed=seed,
    )

    return {
        "metrics": res["metrics"],
        "cis": cis,
        "predictions_df": df_preds,
        "embeddings": res["embeddings"],
    }

