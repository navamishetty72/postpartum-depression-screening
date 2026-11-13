"""Video feature preprocessing and normalization module.

Implements:
1. Leak-free feature normalization fitted strictly on training participants.
2. Variable-length sequence padding and mask construction.
3. Tracking validity masking and confidence-aware temporal pooling.
4. Stratified cross-validation splitting support for training partition.

SCIENTIFIC INTEGRITY NOTICE:
All normalization parameters (mean, standard deviation) must be calculated exclusively
from training participants (split_partition == 'train'). Computing scaling statistics
across the whole cohort or exposing test participants to fitting constitutes data leakage.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import torch
from sklearn.model_selection import StratifiedKFold

from pipelines.video_model.config import (
    CONFIDENCE_THRESHOLD,
    CONTINUOUS_FEATURE_INDICES,
    CV_FOLDS,
    DEFAULT_RANDOM_SEED,
    FEATURE_DIM,
    TRACKING_FEATURE_INDICES,
)


class VideoFeatureNormalizer:
    """Standardizes continuous video features using statistics fitted strictly on training data."""

    def __init__(
        self,
        continuous_indices: Optional[List[int]] = None,
        tracking_indices: Optional[List[int]] = None,
        mask_untracked_frames: bool = True,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        eps: float = 1e-7,
    ) -> None:
        self.continuous_indices = (
            continuous_indices if continuous_indices is not None else CONTINUOUS_FEATURE_INDICES
        )
        self.tracking_indices = (
            tracking_indices if tracking_indices is not None else TRACKING_FEATURE_INDICES
        )
        self.mask_untracked_frames = mask_untracked_frames
        self.confidence_threshold = confidence_threshold
        self.eps = eps

        # Fitted parameters (24-channel arrays)
        self.mean_: Optional[np.ndarray] = None
        self.scale_: Optional[np.ndarray] = None
        self.fitted_participant_count_: int = 0
        self.fitted_frame_count_: int = 0

    @property
    def is_fitted(self) -> bool:
        """Return True if the normalizer has been fitted."""
        return self.mean_ is not None and self.scale_ is not None

    def fit(
        self,
        tensors: List[np.ndarray],
        participant_splits: Optional[List[str]] = None,
    ) -> "VideoFeatureNormalizer":
        """Compute normalization mean and standard deviation strictly on training sequences.

        Args:
            tensors: List of (T_i, 24) float32 feature arrays.
            participant_splits: Optional list of split partition strings ('train', 'test').
                If provided, explicitly verifies that ZERO 'test' participants are included.

        Returns:
            self: The fitted normalizer instance.

        Raises:
            ValueError: If test participants are present or tensors are invalid.
        """
        if participant_splits is not None:
            if len(participant_splits) != len(tensors):
                raise ValueError("Mismatch between tensors count and participant_splits count.")
            for idx, split in enumerate(participant_splits):
                if str(split).lower() != "train":
                    raise ValueError(
                        f"Data leakage violation: fit() received non-training participant at index {idx} with split '{split}'."
                    )

        if len(tensors) == 0:
            raise ValueError("Cannot fit normalizer on empty tensor list.")

        # Initialize accumulator for 24 channels
        mean_accum = np.zeros(FEATURE_DIM, dtype=np.float64)
        m2_accum = np.zeros(FEATURE_DIM, dtype=np.float64)
        count_accum = np.zeros(FEATURE_DIM, dtype=np.int64)

        for arr in tensors:
            if not isinstance(arr, np.ndarray) or arr.ndim != 2 or arr.shape[1] != FEATURE_DIM:
                raise ValueError(f"Expected 2D array of shape (T, {FEATURE_DIM}), got {getattr(arr, 'shape', None)}")

            T = arr.shape[0]
            if self.mask_untracked_frames:
                # Mask out frames where tracking failed
                conf = arr[:, 22]
                succ = arr[:, 23]
                valid_mask = (succ == 1.0) & (conf >= self.confidence_threshold)
            else:
                valid_mask = np.ones(T, dtype=bool)

            for ch in self.continuous_indices:
                ch_data = arr[valid_mask, ch].astype(np.float64)
                n = len(ch_data)
                if n == 0:
                    continue

                # Online Welford update or batch summation
                sum_ch = np.sum(ch_data)
                sum_sq_ch = np.sum(ch_data**2)

                count_accum[ch] += n
                mean_accum[ch] += sum_ch
                m2_accum[ch] += sum_sq_ch

        # Finalize mean and std
        mean_arr = np.zeros(FEATURE_DIM, dtype=np.float32)
        scale_arr = np.ones(FEATURE_DIM, dtype=np.float32)

        for ch in self.continuous_indices:
            n = count_accum[ch]
            if n > 1:
                mu = mean_accum[ch] / n
                var = (m2_accum[ch] / n) - (mu**2)
                var = max(float(var), 0.0)
                sigma = np.sqrt(var) + self.eps
                mean_arr[ch] = np.float32(mu)
                scale_arr[ch] = np.float32(sigma)
            else:
                mean_arr[ch] = 0.0
                scale_arr[ch] = 1.0

        # Keep tracking channels unscaled (passthrough identity transform)
        for ch in self.tracking_indices:
            mean_arr[ch] = 0.0
            scale_arr[ch] = 1.0

        self.mean_ = mean_arr
        self.scale_ = scale_arr
        self.fitted_participant_count_ = len(tensors)
        self.fitted_frame_count_ = int(np.max(count_accum))
        return self

    def transform(
        self,
        tensor: Union[np.ndarray, torch.Tensor],
    ) -> Union[np.ndarray, torch.Tensor]:
        """Apply fitted normalization to a single sequence or 2D/3D batch.

        Args:
            tensor: NumPy array or PyTorch Tensor with last dimension 24.

        Returns:
            Normalized tensor with identical shape and dtype.
        """
        if not self.is_fitted:
            raise ValueError("VideoFeatureNormalizer is not fitted yet. Call fit() before transform().")

        is_torch = isinstance(tensor, torch.Tensor)
        data = tensor.clone() if is_torch else tensor.copy()

        if is_torch:
            mean_t = torch.from_numpy(self.mean_).to(device=data.device, dtype=data.dtype)
            scale_t = torch.from_numpy(self.scale_).to(device=data.device, dtype=data.dtype)
            # Normalize continuous channels in-place or return transformed
            data[..., self.continuous_indices] = (
                data[..., self.continuous_indices] - mean_t[self.continuous_indices]
            ) / scale_t[self.continuous_indices]
        else:
            data[..., self.continuous_indices] = (
                data[..., self.continuous_indices] - self.mean_[self.continuous_indices]
            ) / self.scale_[self.continuous_indices]

        return data

    def to_dict(self) -> Dict[str, Any]:
        """Serialize normalizer parameters to a dictionary."""
        if not self.is_fitted:
            raise ValueError("Cannot serialize unfitted normalizer.")
        return {
            "mean": self.mean_.tolist(),
            "scale": self.scale_.tolist(),
            "continuous_indices": self.continuous_indices,
            "tracking_indices": self.tracking_indices,
            "mask_untracked_frames": self.mask_untracked_frames,
            "confidence_threshold": self.confidence_threshold,
            "fitted_participant_count": self.fitted_participant_count_,
            "fitted_frame_count": self.fitted_frame_count_,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VideoFeatureNormalizer":
        """Reconstruct a normalizer instance from a dictionary."""
        norm = cls(
            continuous_indices=d.get("continuous_indices"),
            tracking_indices=d.get("tracking_indices"),
            mask_untracked_frames=d.get("mask_untracked_frames", True),
            confidence_threshold=d.get("confidence_threshold", CONFIDENCE_THRESHOLD),
        )
        norm.mean_ = np.array(d["mean"], dtype=np.float32)
        norm.scale_ = np.array(d["scale"], dtype=np.float32)
        norm.fitted_participant_count_ = d.get("fitted_participant_count", 0)
        norm.fitted_frame_count_ = d.get("fitted_frame_count", 0)
        return norm

    def save(self, file_path: Union[str, Path]) -> None:
        """Save normalizer parameters as JSON."""
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "VideoFeatureNormalizer":
        """Load normalizer parameters from JSON."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Normalizer file not found at {p}")
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        return cls.from_dict(d)


def pad_collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Collate function for PyTorch DataLoader handling variable-length video tensors.

    Pads sequences to max length within batch and produces:
    - features: (B, T_max, 24) float32 tensor (padded with 0.0).
    - padding_mask: (B, T_max) bool tensor (True for valid real frames, False for padded).
    - tracking_mask: (B, T_max) bool tensor (True for real tracked frames where
      success_flag == 1.0 and tracking_confidence >= 0.60, False otherwise).
    - tracking_confidence: (B, T_max) float32 tensor (padded with 0.0).
    - targets: (B,) long tensor.
    - sequence_lengths: (B,) long tensor.
    - participant_ids: List[str] of length B.

    Args:
        batch: List of item dictionaries returned by PPDVideoDataset.

    Returns:
        Dict[str, Any]: Collated and padded batch tensors.
    """
    if len(batch) == 0:
        raise ValueError("Cannot collate an empty batch.")

    batch_size = len(batch)
    lengths = [item["sequence_length"] for item in batch]
    max_len = max(lengths)

    # Allocate padded batch tensors
    padded_features = torch.zeros((batch_size, max_len, FEATURE_DIM), dtype=torch.float32)
    padding_mask = torch.zeros((batch_size, max_len), dtype=torch.bool)
    tracking_mask = torch.zeros((batch_size, max_len), dtype=torch.bool)
    tracking_conf = torch.zeros((batch_size, max_len), dtype=torch.float32)
    targets = torch.zeros(batch_size, dtype=torch.long)
    seq_lengths = torch.tensor(lengths, dtype=torch.long)
    participant_ids: List[str] = []

    for i, item in enumerate(batch):
        T = item["sequence_length"]
        feat = item["features"]
        padded_features[i, :T, :] = feat if isinstance(feat, torch.Tensor) else torch.from_numpy(feat)
        padding_mask[i, :T] = True

        t_mask = item["tracking_mask"]
        tracking_mask[i, :T] = t_mask if isinstance(t_mask, torch.Tensor) else torch.from_numpy(t_mask)

        t_conf = item["tracking_confidence"]
        tracking_conf[i, :T] = t_conf if isinstance(t_conf, torch.Tensor) else torch.from_numpy(t_conf)

        tgt = item["target"]
        targets[i] = tgt if isinstance(tgt, torch.Tensor) else torch.tensor(tgt, dtype=torch.long)
        participant_ids.append(str(item["participant_id"]))

    return {
        "features": padded_features,
        "padding_mask": padding_mask,
        "tracking_mask": tracking_mask,
        "tracking_confidence": tracking_conf,
        "targets": targets,
        "sequence_lengths": seq_lengths,
        "participant_ids": participant_ids,
    }


def get_stratified_cv_splits(
    dataset: Any,
    n_splits: int = CV_FOLDS,
    seed: int = DEFAULT_RANDOM_SEED,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Generate stratified K-fold cross-validation index splits for training partition.

    Args:
        dataset: PPDVideoDataset instance.
        n_splits: Number of cross-validation folds (default: 5).
        seed: Random seed for deterministic fold assignment (default: 42).

    Returns:
        List of (train_fold_indices, val_fold_indices) tuples.

    Raises:
        ValueError: If dataset is not strictly partitioned to 'train'.
    """
    if getattr(dataset, "partition", None) != "train":
        raise ValueError(
            f"Cross-validation splitting is permitted only on 'train' partition. Received: '{getattr(dataset, 'partition', None)}'."
        )

    targets = np.array(dataset.get_targets(), dtype=int)
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)

    splits: List[Tuple[np.ndarray, np.ndarray]] = []
    indices = np.arange(len(dataset))
    for train_idx, val_idx in skf.split(indices, targets):
        splits.append((train_idx, val_idx))

    return splits


def masked_temporal_pooling(
    features: torch.Tensor,
    mask: torch.Tensor,
    method: str = "mean",
) -> torch.Tensor:
    """Pool variable-length temporal sequences ignoring masked or invalid frames.

    Args:
        features: (B, T, D) tensor.
        mask: (B, T) boolean mask (True for valid frames, False to ignore).
        method: Pooling method ('mean', 'max', or 'mean_max').

    Returns:
        Pooled tensor: (B, D) for 'mean' or 'max'; (B, 2*D) for 'mean_max'.
    """
    if features.dim() != 3 or mask.dim() != 2:
        raise ValueError(f"Expected features (B, T, D) and mask (B, T), got {features.shape}, {mask.shape}")

    mask_expanded = mask.unsqueeze(-1).to(dtype=features.dtype)  # (B, T, 1)
    mask_counts = torch.clamp(mask_expanded.sum(dim=1), min=1.0)  # (B, 1)

    if method == "mean":
        masked_sum = (features * mask_expanded).sum(dim=1)
        return masked_sum / mask_counts

    elif method == "max":
        # Fill masked frames with large negative number before max
        masked_feat = features.masked_fill(~mask.unsqueeze(-1), -1e9)
        max_vals, _ = masked_feat.max(dim=1)
        return max_vals

    elif method == "mean_max":
        masked_sum = (features * mask_expanded).sum(dim=1)
        mean_vals = masked_sum / mask_counts
        masked_feat = features.masked_fill(~mask.unsqueeze(-1), -1e9)
        max_vals, _ = masked_feat.max(dim=1)
        return torch.cat([mean_vals, max_vals], dim=-1)

    else:
        raise ValueError(f"Unsupported pooling method: '{method}'. Choose 'mean', 'max', or 'mean_max'.")

