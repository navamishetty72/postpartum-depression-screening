"""Automated unit and integration test suite for video model dataset loading and preprocessing.

Validates the core contracts of Phase 2:
1. Dataset loading for train (640) and test (160) partitions.
2. Participant ID alignment and join on participant_id.
3. Strict train/test separation and zero participant overlap.
4. Variable sequence length handling (45 <= T <= 120).
5. Padding collation and attention/padding masks.
6. Tracking masks and confidence consistency.
7. Leak-free feature normalization fitted strictly on training data.
8. Normalizer serialization and reconstruction.
9. Invalid tensor handling (wrong dimensions, NaNs, Infs).
10. Missing participant file rejection.
11. Label validation and duplicate ID rejection.
12. Stratified 5-fold cross-validation generation on training partition.
13. Confidence-aware masked temporal pooling.
"""

from pathlib import Path
from typing import Dict, List
# pyrefly: ignore[missing-import]
import numpy as np
import pandas as pd
# pyrefly: ignore[missing-import]
import pytest
torch = pytest.importorskip("torch", reason="torch is required for video deep learning tests")
# pyrefly: ignore[missing-import]
from torch.utils.data import DataLoader

from pipelines.video_model.config import (
    CONFIDENCE_THRESHOLD,
    CONTINUOUS_FEATURE_INDICES,
    CV_FOLDS,
    EXPECTED_TEST_PARTICIPANTS,
    EXPECTED_TOTAL_PARTICIPANTS,
    EXPECTED_TRAIN_PARTICIPANTS,
    FEATURE_DIM,
    MAX_SEQUENCE_LENGTH,
    MIN_SEQUENCE_LENGTH,
    SPLIT_MANIFEST_PATH,
    TRACKING_FEATURE_INDICES,
    V2_FEATURE_DIR,
    V2_MANIFEST_PATH,
)
from pipelines.video_model.dataset import PPDVideoDataset
from pipelines.video_model.preprocessing import (
    VideoFeatureNormalizer,
    get_stratified_cv_splits,
    masked_temporal_pooling,
    pad_collate_fn,
)


@pytest.fixture(scope="module")
def train_dataset() -> PPDVideoDataset:
    """Fixture providing initialized training dataset (640 participants)."""
    if not V2_MANIFEST_PATH.exists():
        from pipelines.synthetic_video.generator_v2 import run_generation_v2
        run_generation_v2()
    return PPDVideoDataset(partition="train", validate_on_init=True)


@pytest.fixture(scope="module")
def test_dataset() -> PPDVideoDataset:
    """Fixture providing initialized holdout testing dataset (160 participants)."""
    if not V2_MANIFEST_PATH.exists():
        from pipelines.synthetic_video.generator_v2 import run_generation_v2
        run_generation_v2()
    return PPDVideoDataset(partition="test", validate_on_init=True)


# ==============================================================================
# 1. Dataset Loading & Partition Counts
# ==============================================================================
def test_1_dataset_loading_train_and_test(
    train_dataset: PPDVideoDataset, test_dataset: PPDVideoDataset
) -> None:
    """Requirement 1: Exactly 640 train and 160 test records loaded."""
    assert len(train_dataset) == EXPECTED_TRAIN_PARTICIPANTS == 640
    assert len(test_dataset) == EXPECTED_TEST_PARTICIPANTS == 160
    assert len(train_dataset) + len(test_dataset) == EXPECTED_TOTAL_PARTICIPANTS == 800


# ==============================================================================
# 2. Participant ID Alignment & Merging
# ==============================================================================
def test_2_participant_id_alignment(
    train_dataset: PPDVideoDataset, test_dataset: PPDVideoDataset
) -> None:
    """Requirement 2: Participant IDs join on participant_id and match frozen manifest."""
    split_df = pd.read_csv(SPLIT_MANIFEST_PATH)
    expected_train_pids = split_df[split_df["split_partition"] == "train"]["participant_id"].tolist()
    expected_test_pids = split_df[split_df["split_partition"] == "test"]["participant_id"].tolist()

    actual_train_pids = train_dataset.get_participant_ids()
    actual_test_pids = test_dataset.get_participant_ids()

    assert actual_train_pids == expected_train_pids
    assert actual_test_pids == expected_test_pids
    assert actual_train_pids[0] == expected_train_pids[0]
    assert actual_train_pids[-1] == expected_train_pids[-1]
    assert actual_test_pids[0] == expected_test_pids[0]
    assert actual_test_pids[-1] == expected_test_pids[-1]
    assert len(actual_train_pids) == EXPECTED_TRAIN_PARTICIPANTS
    assert len(actual_test_pids) == EXPECTED_TEST_PARTICIPANTS


# ==============================================================================
# 3. Train/Test Separation & Class Balance
# ==============================================================================
def test_3_train_test_strict_separation(
    train_dataset: PPDVideoDataset, test_dataset: PPDVideoDataset
) -> None:
    """Requirement 3: Zero participant overlap and frozen class balance preservation."""
    train_pids = set(train_dataset.get_participant_ids())
    test_pids = set(test_dataset.get_participant_ids())

    overlap = train_pids.intersection(test_pids)
    assert len(overlap) == 0, f"Participant overlap detected between train and test: {overlap}"

    # Class balance check
    y_train = train_dataset.get_targets()
    y_test = test_dataset.get_targets()

    assert (y_train == 1).sum() == 281
    assert (y_train == 0).sum() == 359
    assert (y_test == 1).sum() == 70
    assert (y_test == 0).sum() == 90


# ==============================================================================
# 4. Variable Sequence Lengths & Shapes
# ==============================================================================
def test_4_variable_sequence_lengths_and_shapes(train_dataset: PPDVideoDataset) -> None:
    """Requirement 4: Tensors have (T, 24) float32 shape with 45 <= T <= 120."""
    sample_indices = [0, 10, 50, 100, 200]
    lengths = []

    for idx in sample_indices:
        item = train_dataset[idx]
        assert isinstance(item, dict)
        assert "features" in item
        assert "target" in item
        assert "tracking_mask" in item
        assert "tracking_confidence" in item
        assert "sequence_length" in item
        assert "participant_id" in item

        feat = item["features"]
        assert isinstance(feat, torch.Tensor)
        assert feat.dtype == torch.float32
        assert feat.ndim == 2
        assert feat.shape[1] == FEATURE_DIM == 24

        T = feat.shape[0]
        assert MIN_SEQUENCE_LENGTH <= T <= MAX_SEQUENCE_LENGTH
        assert T == item["sequence_length"]
        assert item["tracking_mask"].shape == (T,)
        assert item["tracking_confidence"].shape == (T,)
        assert item["target"].item() in (0, 1)
        lengths.append(T)

    # Confirm variable lengths across samples
    assert len(set(lengths)) > 1, "Expected variable sequence lengths across dataset"


# ==============================================================================
# 5. Padding Collation & Attention Masks
# ==============================================================================
def test_5_pad_collate_fn_and_padding_masks(train_dataset: PPDVideoDataset) -> None:
    """Requirement 5: Variable-length collation produces valid padded tensors and masks."""
    batch = [train_dataset[i] for i in range(4)]
    collated = pad_collate_fn(batch)

    lengths = [b["sequence_length"] for b in batch]
    max_len = max(lengths)

    features = collated["features"]
    padding_mask = collated["padding_mask"]
    tracking_mask = collated["tracking_mask"]
    tracking_conf = collated["tracking_confidence"]
    targets = collated["targets"]
    seq_lengths = collated["sequence_lengths"]

    assert features.shape == (4, max_len, FEATURE_DIM)
    assert padding_mask.shape == (4, max_len)
    assert tracking_mask.shape == (4, max_len)
    assert tracking_conf.shape == (4, max_len)
    assert targets.shape == (4,)
    assert (seq_lengths == torch.tensor(lengths)).all()

    for i, T in enumerate(lengths):
        # Valid region
        assert padding_mask[i, :T].all()
        # Padded region
        if T < max_len:
            assert (~padding_mask[i, T:]).all()
            assert (features[i, T:, :] == 0.0).all()
            assert (~tracking_mask[i, T:]).all()
            assert (tracking_conf[i, T:] == 0.0).all()


# ==============================================================================
# 6. Tracking Mask Consistency
# ==============================================================================
def test_6_tracking_mask_consistency(train_dataset: PPDVideoDataset) -> None:
    """Requirement 6: tracking_mask is True iff success_flag == 1.0 and confidence >= 0.60."""
    for idx in [0, 5, 15, 25]:
        item = train_dataset[idx]
        feat = item["features"]
        t_mask = item["tracking_mask"]
        t_conf = item["tracking_confidence"]

        conf_channel = feat[:, 22]
        succ_channel = feat[:, 23]

        expected_mask = (succ_channel == 1.0) & (conf_channel >= CONFIDENCE_THRESHOLD)
        assert (t_mask == expected_mask).all()
        assert (t_conf == conf_channel).all()


# ==============================================================================
# 7. Training-Only Normalization & Leakage Prevention
# ==============================================================================
def test_7_training_only_normalization_leak_free(
    train_dataset: PPDVideoDataset, test_dataset: PPDVideoDataset
) -> None:
    """Requirement 7: Normalizer fits strictly on training sequences without test contamination."""
    raw_train_tensors = train_dataset.get_all_raw_tensors()
    normalizer = VideoFeatureNormalizer()

    # 1. Fit strictly on train
    normalizer.fit(raw_train_tensors, participant_splits=["train"] * len(raw_train_tensors))
    assert normalizer.is_fitted
    assert normalizer.fitted_participant_count_ == 640

    # 2. Verify leakage guard: passing test participant split raises ValueError
    with pytest.raises(ValueError, match="Data leakage violation"):
        normalizer.fit(
            raw_train_tensors[:10],
            participant_splits=["train"] * 9 + ["test"],
        )

    # 3. Verify continuous channels are scaled while tracking channels remain unscaled
    assert normalizer.mean_ is not None
    assert normalizer.scale_ is not None

    for ch in CONTINUOUS_FEATURE_INDICES:
        assert normalizer.scale_[ch] > 0.0

    for ch in TRACKING_FEATURE_INDICES:
        assert normalizer.mean_[ch] == 0.0
        assert normalizer.scale_[ch] == 1.0

    # 4. Transform dataset using fitted normalizer
    norm_train_ds = PPDVideoDataset(partition="train", normalizer=normalizer)
    sample_norm = norm_train_ds[0]["features"]
    assert sample_norm.shape == (norm_train_ds[0]["sequence_length"], FEATURE_DIM)
    assert sample_norm.dtype == torch.float32

    # Tracking channels 22 and 23 must stay identical to raw
    raw_sample = train_dataset[0]["features"]
    assert torch.allclose(sample_norm[:, 22], raw_sample[:, 22])
    assert torch.allclose(sample_norm[:, 23], raw_sample[:, 23])


# ==============================================================================
# 8. Normalizer Serialization
# ==============================================================================
def test_8_normalizer_serialization(tmp_path: Path, train_dataset: PPDVideoDataset) -> None:
    """Requirement 8: Normalizer can be saved and loaded identically via JSON."""
    raw_tensors = train_dataset.get_all_raw_tensors()[:20]
    norm1 = VideoFeatureNormalizer()
    norm1.fit(raw_tensors)

    save_path = tmp_path / "normalizer.json"
    norm1.save(save_path)
    assert save_path.exists()

    norm2 = VideoFeatureNormalizer.load(save_path)
    assert norm2.is_fitted
    np.testing.assert_array_equal(norm1.mean_, norm2.mean_)
    np.testing.assert_array_equal(norm1.scale_, norm2.scale_)
    assert norm1.fitted_participant_count_ == norm2.fitted_participant_count_


# ==============================================================================
# 9. Invalid Tensor Handling
# ==============================================================================
def test_9_invalid_tensor_handling(tmp_path: Path) -> None:
    """Requirement 9: Rejects corrupted tensors (wrong channels, NaNs, Infs)."""
    # Create mock manifest and mock tensor directory
    features_dir = tmp_path / "features"
    features_dir.mkdir(parents=True)

    # 1. Tensor with wrong channels (20 instead of 24)
    np.save(features_dir / "BGD_901.npy", np.zeros((50, 20), dtype=np.float32))

    # 2. Tensor with NaN
    nan_tensor = np.zeros((50, 24), dtype=np.float32)
    nan_tensor[10, 5] = np.nan
    np.save(features_dir / "BGD_902.npy", nan_tensor)

    # 3. Tensor with Inf
    inf_tensor = np.zeros((50, 24), dtype=np.float32)
    inf_tensor[10, 5] = np.inf
    np.save(features_dir / "BGD_903.npy", inf_tensor)

    # Mock manifests
    v_df = pd.DataFrame({
        "participant_id": ["BGD_901", "BGD_902", "BGD_903"],
        "split_partition": ["train", "train", "train"],
    })
    s_df = pd.DataFrame({
        "participant_id": ["BGD_901", "BGD_902", "BGD_903"],
        "split_partition": ["train", "train", "train"],
        "target_canonical_epds_ge_13": [0, 1, 0],
    })

    v_path = tmp_path / "v_manifest.csv"
    s_path = tmp_path / "s_manifest.csv"
    v_df.to_csv(v_path, index=False)
    s_df.to_csv(s_path, index=False)

    ds = PPDVideoDataset(
        features_dir=features_dir,
        video_manifest_path=v_path,
        split_manifest_path=s_path,
        partition="train",
    )

    # Channel mismatch error
    with pytest.raises(ValueError, match="Expected 24 channels"):
        _ = ds[0]

    # NaN detection error
    with pytest.raises(ValueError, match="NaN value detected"):
        _ = ds[1]

    # Inf detection error
    with pytest.raises(ValueError, match="Infinite value detected"):
        _ = ds[2]


# ==============================================================================
# 10. Missing Participant File Handling
# ==============================================================================
def test_10_missing_participant_file_handling(tmp_path: Path) -> None:
    """Requirement 10: Missing feature tensor files raise FileNotFoundError."""
    features_dir = tmp_path / "empty_features"
    features_dir.mkdir(parents=True)

    v_df = pd.DataFrame({
        "participant_id": ["BGD_999"],
        "split_partition": ["train"],
    })
    s_df = pd.DataFrame({
        "participant_id": ["BGD_999"],
        "split_partition": ["train"],
        "target_canonical_epds_ge_13": [1],
    })
    v_path = tmp_path / "v.csv"
    s_path = tmp_path / "s.csv"
    v_df.to_csv(v_path, index=False)
    s_df.to_csv(s_path, index=False)

    with pytest.raises(FileNotFoundError, match="Feature tensor file missing"):
        _ = PPDVideoDataset(
            features_dir=features_dir,
            video_manifest_path=v_path,
            split_manifest_path=s_path,
            partition="train",
            validate_on_init=True,
        )


# ==============================================================================
# 11. Label Validation & Duplicate ID Rejection
# ==============================================================================
def test_11_label_validation_and_duplicate_id_rejection(tmp_path: Path) -> None:
    """Requirement 11: Rejects duplicate participant IDs, invalid targets, and partition mismatches."""
    # 1. Duplicate IDs
    dup_df = pd.DataFrame({
        "participant_id": ["BGD_001", "BGD_001"],
        "split_partition": ["train", "train"],
        "target_canonical_epds_ge_13": [0, 1],
    })
    d_v = tmp_path / "dup_v.csv"
    d_s = tmp_path / "dup_s.csv"
    dup_df.to_csv(d_v, index=False)
    dup_df.to_csv(d_s, index=False)

    with pytest.raises(ValueError, match="Duplicate participant IDs"):
        _ = PPDVideoDataset(
            features_dir=V2_FEATURE_DIR,
            video_manifest_path=d_v,
            split_manifest_path=d_s,
            partition="train",
        )

    # 2. Invalid target labels (e.g. 2 or -1)
    inv_df = pd.DataFrame({
        "participant_id": ["BGD_001"],
        "split_partition": ["train"],
        "target_canonical_epds_ge_13": [5],  # Invalid
    })
    inv_v = tmp_path / "inv_v.csv"
    inv_s = tmp_path / "inv_s.csv"
    inv_df[["participant_id", "split_partition"]].to_csv(inv_v, index=False)
    inv_df.to_csv(inv_s, index=False)

    with pytest.raises(ValueError, match="Invalid target labels detected"):
        _ = PPDVideoDataset(
            features_dir=V2_FEATURE_DIR,
            video_manifest_path=inv_v,
            split_manifest_path=inv_s,
            partition="train",
        )

    # 3. Split partition mismatch
    mismatch_v = pd.DataFrame({"participant_id": ["BGD_001"], "split_partition": ["train"]})
    mismatch_s = pd.DataFrame({
        "participant_id": ["BGD_001"],
        "split_partition": ["test"],  # Mismatch!
        "target_canonical_epds_ge_13": [0],
    })
    mv_path = tmp_path / "mv.csv"
    ms_path = tmp_path / "ms.csv"
    mismatch_v.to_csv(mv_path, index=False)
    mismatch_s.to_csv(ms_path, index=False)

    with pytest.raises(ValueError, match="Split partition mismatch"):
        _ = PPDVideoDataset(
            features_dir=V2_FEATURE_DIR,
            video_manifest_path=mv_path,
            split_manifest_path=ms_path,
            partition="all",
        )


# ==============================================================================
# 12. Stratified Cross-Validation Generation
# ==============================================================================
def test_12_stratified_cv_splits_support(
    train_dataset: PPDVideoDataset, test_dataset: PPDVideoDataset
) -> None:
    """Requirement 12: Generates leak-free 5-fold stratified splits on training partition."""
    splits = get_stratified_cv_splits(train_dataset, n_splits=CV_FOLDS, seed=42)
    assert len(splits) == 5

    total_val_samples = 0
    all_val_indices = []

    for fold_idx, (tr_idx, val_idx) in enumerate(splits):
        assert len(tr_idx) == 512
        assert len(val_idx) == 128
        assert len(set(tr_idx).intersection(set(val_idx))) == 0
        total_val_samples += len(val_idx)
        all_val_indices.extend(val_idx)

        # Check positive ratio in val fold
        y_val = train_dataset.get_targets()[val_idx]
        pos_ratio = (y_val == 1).sum() / len(y_val)
        # Prevalence is ~43.9%, so each fold should have 56 or 57 positives (out of 128)
        assert 0.40 <= pos_ratio <= 0.48

    # All 640 training samples appear in validation exactly once
    assert total_val_samples == 640
    assert len(set(all_val_indices)) == 640

    # Cross-validation on test partition is forbidden
    with pytest.raises(ValueError, match="permitted only on 'train' partition"):
        _ = get_stratified_cv_splits(test_dataset, n_splits=5)


# ==============================================================================
# 13. Masked Temporal Pooling
# ==============================================================================
def test_13_masked_temporal_pooling() -> None:
    """Requirement 13: Confidence-masked temporal pooling properly excludes untracked frames."""
    # B=2, T=3, D=2
    features = torch.tensor([
        [[1.0, 2.0], [3.0, 4.0], [100.0, 200.0]],  # Frame 2 is an untracked outlier
        [[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]],
    ], dtype=torch.float32)

    # Frame 2 of sequence 0 is masked out (False)
    mask = torch.tensor([
        [True, True, False],
        [True, True, True],
    ], dtype=torch.bool)

    # Mean pooling
    pooled_mean = masked_temporal_pooling(features, mask, method="mean")
    assert pooled_mean.shape == (2, 2)
    # Sequence 0 mean should be mean of frames 0 and 1: [(1+3)/2, (2+4)/2] = [2.0, 3.0]
    assert torch.allclose(pooled_mean[0], torch.tensor([2.0, 3.0]))
    # Sequence 1 mean should be [(10+30+50)/3, (20+40+60)/3] = [30.0, 40.0]
    assert torch.allclose(pooled_mean[1], torch.tensor([30.0, 40.0]))

    # Max pooling
    pooled_max = masked_temporal_pooling(features, mask, method="max")
    assert pooled_max.shape == (2, 2)
    # Sequence 0 max should ignore frame 2 (100.0, 200.0) and pick frame 1: [3.0, 4.0]
    assert torch.allclose(pooled_max[0], torch.tensor([3.0, 4.0]))

    # Combined mean_max
    pooled_mm = masked_temporal_pooling(features, mask, method="mean_max")
    assert pooled_mm.shape == (2, 4)
