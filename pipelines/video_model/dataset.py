"""PyTorch Dataset loader for PPD video modeling.

Loads 24-channel temporal video feature tensors linked to Bangladesh cohort participant IDs,
validates schemas and ground-truth targets, and strictly enforces frozen train/test partition boundaries.

SCIENTIFIC INTEGRITY NOTICE:
Synthetic Video V2 features are abstract numerical simulations. Video features alone
do not represent authentic patient observations or diagnostic biomarkers.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from pipelines.video_model.config import (
    CONFIDENCE_THRESHOLD,
    EXPECTED_DTYPE,
    FEATURE_DIM,
    MAX_SEQUENCE_LENGTH,
    MIN_SEQUENCE_LENGTH,
    PARTICIPANT_ID_COLUMN,
    SPLIT_COLUMN,
    SPLIT_MANIFEST_PATH,
    TARGET_COLUMN,
    V2_FEATURE_DIR,
    V2_MANIFEST_PATH,
    VALID_SPLIT_PARTITIONS,
)
from pipelines.video_model.preprocessing import VideoFeatureNormalizer


class PPDVideoDataset(Dataset):
    """PyTorch Dataset for loading and validating video feature sequence tensors."""

    def __init__(
        self,
        features_dir: Union[str, Path] = V2_FEATURE_DIR,
        video_manifest_path: Union[str, Path] = V2_MANIFEST_PATH,
        split_manifest_path: Union[str, Path] = SPLIT_MANIFEST_PATH,
        partition: str = "train",
        normalizer: Optional[VideoFeatureNormalizer] = None,
        return_as_torch: bool = True,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        validate_on_init: bool = True,
    ) -> None:
        """Initialize PPDVideoDataset.

        Args:
            features_dir: Directory containing individual .npy feature tensors.
            video_manifest_path: Path to video_manifest.csv.
            split_manifest_path: Path to train_test_split_manifest.csv.
            partition: Split partition to load ('train', 'test', or 'all').
            normalizer: Optional fitted VideoFeatureNormalizer.
            return_as_torch: Whether to return torch.Tensor instances in __getitem__.
            confidence_threshold: Minimum tracking confidence to consider frame valid.
            validate_on_init: Whether to verify all feature files exist during initialization.
        """
        self.features_dir = Path(features_dir)
        self.video_manifest_path = Path(video_manifest_path)
        self.split_manifest_path = Path(split_manifest_path)
        self.partition = partition.lower()
        self.normalizer = normalizer
        self.return_as_torch = return_as_torch
        self.confidence_threshold = confidence_threshold

        if self.partition not in VALID_SPLIT_PARTITIONS:
            raise ValueError(
                f"Invalid partition '{self.partition}'. Choose from {VALID_SPLIT_PARTITIONS}."
            )

        # 1. Load and Validate Manifests
        self._load_and_validate_manifests()

        # 2. Verify all tensor files exist
        if validate_on_init:
            self._validate_file_existence()

    def _load_and_validate_manifests(self) -> None:
        """Load manifests, merge strictly on participant_id, and validate integrity."""
        if not self.video_manifest_path.exists():
            raise FileNotFoundError(f"Video manifest not found at {self.video_manifest_path}")
        if not self.split_manifest_path.exists():
            raise FileNotFoundError(f"Split manifest not found at {self.split_manifest_path}")

        df_video = pd.read_csv(self.video_manifest_path)
        df_split = pd.read_csv(self.split_manifest_path)

        # Check for required columns
        for col in [PARTICIPANT_ID_COLUMN, SPLIT_COLUMN]:
            if col not in df_video.columns:
                raise ValueError(f"Missing required column '{col}' in video manifest.")
            if col not in df_split.columns:
                raise ValueError(f"Missing required column '{col}' in split manifest.")

        if TARGET_COLUMN not in df_split.columns:
            raise ValueError(f"Missing target column '{TARGET_COLUMN}' in split manifest.")

        # Check for duplicate participant IDs in individual manifests
        if df_video[PARTICIPANT_ID_COLUMN].duplicated().any():
            dups = df_video[df_video[PARTICIPANT_ID_COLUMN].duplicated()][PARTICIPANT_ID_COLUMN].tolist()
            raise ValueError(f"Duplicate participant IDs found in video manifest: {dups[:5]}")

        if df_split[PARTICIPANT_ID_COLUMN].duplicated().any():
            dups = df_split[df_split[PARTICIPANT_ID_COLUMN].duplicated()][PARTICIPANT_ID_COLUMN].tolist()
            raise ValueError(f"Duplicate participant IDs found in split manifest: {dups[:5]}")

        # Validate target labels (must be strictly binary 0 or 1, non-null)
        targets = df_split[TARGET_COLUMN]
        if targets.isnull().any():
            raise ValueError("Null values found in target column.")
        unique_targets = set(targets.unique())
        if not unique_targets.issubset({0, 1}):
            raise ValueError(f"Invalid target labels detected: {unique_targets}. Expected subset of {{0, 1}}.")

        # Merge strictly on participant_id (never row index!)
        merged = pd.merge(
            df_video,
            df_split[[PARTICIPANT_ID_COLUMN, TARGET_COLUMN, f"{SPLIT_COLUMN}"]],
            on=PARTICIPANT_ID_COLUMN,
            suffixes=("", "_split"),
            how="inner",
        )

        if len(merged) == 0:
            raise ValueError("Zero overlapping participant IDs between video manifest and split manifest.")

        # Verify partition alignment between video and split manifest
        if (merged[SPLIT_COLUMN] != merged[f"{SPLIT_COLUMN}_split"]).any():
            mismatches = merged[merged[SPLIT_COLUMN] != merged[f"{SPLIT_COLUMN}_split"]][PARTICIPANT_ID_COLUMN].tolist()
            raise ValueError(f"Split partition mismatch between manifests for participants: {mismatches[:5]}")

        # Filter to requested partition
        if self.partition in ("train", "test"):
            self.metadata_df = (
                merged[merged[SPLIT_COLUMN] == self.partition].copy().reset_index(drop=True)
            )
        else:  # "all"
            self.metadata_df = merged.copy().reset_index(drop=True)

        if len(self.metadata_df) == 0:
            raise ValueError(f"No records found for partition '{self.partition}'.")

    def _validate_file_existence(self) -> None:
        """Verify that every tensor .npy file exists on disk."""
        for _, row in self.metadata_df.iterrows():
            pid = str(row[PARTICIPANT_ID_COLUMN])
            tensor_path = self.features_dir / f"{pid}.npy"
            if not tensor_path.is_file():
                raise FileNotFoundError(f"Feature tensor file missing for {pid} at {tensor_path}")

    def __len__(self) -> int:
        """Return the number of participants in this dataset partition."""
        return len(self.metadata_df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """Load, validate, and return a single participant sequence tensor.

        Args:
            idx: Integer index within the filtered dataset partition.

        Returns:
            Dict[str, Any] containing:
                - participant_id: str
                - features: (T, 24) tensor/array
                - target: scalar long tensor/int
                - tracking_mask: (T,) boolean mask
                - tracking_confidence: (T,) float array/tensor
                - sequence_length: int
                - split_partition: str
        """
        row = self.metadata_df.iloc[idx]
        pid = str(row[PARTICIPANT_ID_COLUMN])
        target_val = int(row[TARGET_COLUMN])
        split_val = str(row[SPLIT_COLUMN])

        tensor_path = self.features_dir / f"{pid}.npy"
        if not tensor_path.exists():
            raise FileNotFoundError(f"Tensor file missing for {pid} at {tensor_path}")

        arr = np.load(tensor_path)

        # Strict Tensor Integrity Assertions
        if not isinstance(arr, np.ndarray):
            raise ValueError(f"File {tensor_path} does not contain a numpy array.")

        if arr.ndim != 2:
            raise ValueError(f"Expected 2D array (T, {FEATURE_DIM}), got {arr.ndim}D array for {pid}.")

        if arr.shape[1] != FEATURE_DIM:
            raise ValueError(
                f"Expected {FEATURE_DIM} channels, got {arr.shape[1]} channels for {pid}."
            )

        if arr.shape[0] < 1:
            raise ValueError(f"Sequence length is 0 for {pid}.")

        if arr.dtype != EXPECTED_DTYPE:
            raise ValueError(f"Expected dtype {EXPECTED_DTYPE}, got {arr.dtype} for {pid}.")

        if np.isnan(arr).any():
            raise ValueError(f"NaN value detected in tensor for participant {pid}.")

        if np.isinf(arr).any():
            raise ValueError(f"Infinite value detected in tensor for participant {pid}.")

        T = arr.shape[0]

        # Extract tracking channels: 22=tracking_confidence, 23=success_flag
        tracking_conf = arr[:, 22].copy()
        success_flag = arr[:, 23].copy()

        # Construct tracking validity mask
        tracking_mask = (success_flag == 1.0) & (tracking_conf >= self.confidence_threshold)

        # Apply normalizer if provided
        features = self.normalizer.transform(arr) if self.normalizer is not None else arr.copy()

        if self.return_as_torch:
            features = torch.from_numpy(features).float()
            tracking_mask = torch.from_numpy(tracking_mask).bool()
            tracking_conf = torch.from_numpy(tracking_conf).float()
            target_out = torch.tensor(target_val, dtype=torch.long)
        else:
            target_out = target_val

        return {
            "participant_id": pid,
            "features": features,
            "target": target_out,
            "tracking_mask": tracking_mask,
            "tracking_confidence": tracking_conf,
            "sequence_length": T,
            "split_partition": split_val,
        }

    def get_participant_ids(self) -> List[str]:
        """Return list of participant IDs in this dataset partition."""
        return self.metadata_df[PARTICIPANT_ID_COLUMN].tolist()

    def get_targets(self) -> np.ndarray:
        """Return 1D array of binary targets for this dataset partition."""
        return self.metadata_df[TARGET_COLUMN].values.astype(int)

    def get_split_partitions(self) -> List[str]:
        """Return list of split partition labels for this dataset partition."""
        return self.metadata_df[SPLIT_COLUMN].tolist()

    def get_all_raw_tensors(self) -> List[np.ndarray]:
        """Load and return all unnormalized numpy tensors in this dataset partition."""
        tensors: List[np.ndarray] = []
        for pid in self.get_participant_ids():
            path = self.features_dir / f"{pid}.npy"
            tensors.append(np.load(path))
        return tensors

