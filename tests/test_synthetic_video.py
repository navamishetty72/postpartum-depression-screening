"""Automated validation test suite for synthetic video feature trajectory generation.

Validates the 15 core requirements for synthetic video feature tensors:
1. Exactly 800 manifest records.
2. Exactly 640 training and 160 testing records.
3. Exact participant ID and split alignment with train_test_split_manifest.csv.
4. No duplicate participant IDs.
5. All 800 feature files exist and are readable.
6. Tensor dimensions are (T, 24), where 45 <= T <= 120.
7. Dtype is float32.
8. No NaN or Inf values in scalars or tensors.
9. Every channel stays within its specified engineering bounds.
10. Tracking status and confidence are consistent (success_flag == 0.0 iff confidence < 0.60).
11. Missing-frame counts and dropout rates match the tensors exactly.
12. Generation is deterministic with seed 42.
13. Correct provenance tags (SYNTHETIC_ABSTRACT_VIDEO_FEATURES).
14. No clinical target inputs or target columns are used.
15. No actual image or video files are generated.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import pytest

from pipelines.synthetic_video.config import (
    CHANNEL_BOUNDS,
    CHANNEL_NAMES,
    CONFIDENCE_THRESHOLD,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    FEATURE_DIM,
    MAX_SEQUENCE_LENGTH,
    MIN_SEQUENCE_LENGTH,
    SYNTHETIC_VIDEO_DIR,
    SYNTHETIC_VIDEO_FEATURES_DIR,
    SYNTHETIC_VIDEO_MANIFEST_PATH,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
)
from pipelines.synthetic_video.generator import SyntheticVideoGenerator


@pytest.fixture(scope="module")
def video_manifest() -> pd.DataFrame:
    """Load the generated synthetic video manifest."""
    assert SYNTHETIC_VIDEO_MANIFEST_PATH.exists(), (
        f"Video manifest not found at {SYNTHETIC_VIDEO_MANIFEST_PATH}"
    )
    return pd.read_csv(SYNTHETIC_VIDEO_MANIFEST_PATH)


@pytest.fixture(scope="module")
def split_manifest() -> pd.DataFrame:
    """Load the frozen train/test split manifest."""
    assert TRAIN_TEST_SPLIT_MANIFEST_PATH.exists()
    return pd.read_csv(TRAIN_TEST_SPLIT_MANIFEST_PATH)


def test_1_record_count(video_manifest: pd.DataFrame) -> None:
    """Requirement 1: Exactly 800 records."""
    assert len(video_manifest) == 800, f"Expected 800 records, got {len(video_manifest)}"


def test_2_train_test_split_counts(video_manifest: pd.DataFrame) -> None:
    """Requirement 2: Exactly 640 training and 160 testing records."""
    counts = video_manifest["split_partition"].value_counts().to_dict()
    assert counts.get("train") == 640, f"Expected 640 train, got {counts.get('train')}"
    assert counts.get("test") == 160, f"Expected 160 test, got {counts.get('test')}"


def test_3_participant_id_alignment(
    video_manifest: pd.DataFrame, split_manifest: pd.DataFrame
) -> None:
    """Requirement 3: Exact participant ID and split alignment with train_test_split_manifest.csv."""
    expected_ids = split_manifest["participant_id"].tolist()
    actual_ids = video_manifest["participant_id"].tolist()
    assert actual_ids == expected_ids, "Participant IDs do not match split manifest order"
    assert actual_ids[0] == "BGD_001"
    assert actual_ids[-1] == "BGD_800"

    expected_splits = split_manifest["split_partition"].tolist()
    actual_splits = video_manifest["split_partition"].tolist()
    assert actual_splits == expected_splits, "Split partitions do not match split manifest"


def test_4_no_duplicate_ids(video_manifest: pd.DataFrame) -> None:
    """Requirement 4: No duplicate participant IDs."""
    assert video_manifest["participant_id"].nunique() == 800


def test_5_all_feature_files_exist_and_readable(video_manifest: pd.DataFrame) -> None:
    """Requirement 5: All 800 feature files exist and are readable."""
    for _, row in video_manifest.iterrows():
        rel_path = Path(row["feature_file_path"])
        file_path = Path(__file__).resolve().parent.parent / rel_path
        assert file_path.exists(), f"Feature file missing: {file_path}"
        arr = np.load(file_path)
        assert isinstance(arr, np.ndarray), f"File {file_path} is not a valid numpy array"


def test_6_tensor_dimensions(video_manifest: pd.DataFrame) -> None:
    """Requirement 6: Tensor dimensions are (T, 24), where 45 <= T <= 120."""
    sample_rows = pd.concat([video_manifest.head(25), video_manifest.tail(25)])
    for _, row in sample_rows.iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        assert arr.ndim == 2, f"Expected 2D tensor, got {arr.ndim}D"
        assert arr.shape[1] == FEATURE_DIM, f"Expected 24 channels, got {arr.shape[1]}"
        t_len = arr.shape[0]
        assert MIN_SEQUENCE_LENGTH <= t_len <= MAX_SEQUENCE_LENGTH, (
            f"Sequence length {t_len} outside [{MIN_SEQUENCE_LENGTH}, {MAX_SEQUENCE_LENGTH}]"
        )
        assert t_len == row["sequence_length"], (
            f"Manifest sequence length {row['sequence_length']} != tensor shape {t_len}"
        )


def test_7_dtype_is_float32(video_manifest: pd.DataFrame) -> None:
    """Requirement 7: Dtype is float32."""
    for _, row in video_manifest.head(30).iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        assert arr.dtype == np.float32, f"Expected float32, got {arr.dtype}"


def test_8_no_nan_or_inf(video_manifest: pd.DataFrame) -> None:
    """Requirement 8: No NaN or Inf values."""
    # Check manifest columns
    numeric_cols = [
        "sequence_length",
        "feature_dimension",
        "missing_frame_count",
        "mean_tracking_confidence",
        "dropout_rate",
    ]
    for col in numeric_cols:
        assert not video_manifest[col].isnull().any(), f"NaN found in manifest col {col}"
        assert not np.isinf(video_manifest[col]).any(), f"Inf found in manifest col {col}"

    # Check tensors across cohort
    for _, row in video_manifest.iloc[::20].iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        assert not np.isnan(arr).any(), f"NaN in tensor for {row['participant_id']}"
        assert not np.isinf(arr).any(), f"Inf in tensor for {row['participant_id']}"


def test_9_engineering_channel_bounds(video_manifest: pd.DataFrame) -> None:
    """Requirement 9: Every channel stays strictly within its specified engineering bounds."""
    for _, row in video_manifest.iloc[::15].iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        for ch_idx, ch_name in enumerate(CHANNEL_NAMES):
            ch_data = arr[:, ch_idx]
            lower, upper = CHANNEL_BOUNDS[ch_name]
            min_val = float(ch_data.min())
            max_val = float(ch_data.max())
            assert min_val >= lower - 1e-5, (
                f"{ch_name} min {min_val} below lower bound {lower} in {row['participant_id']}"
            )
            assert max_val <= upper + 1e-5, (
                f"{ch_name} max {max_val} above upper bound {upper} in {row['participant_id']}"
            )


def test_10_tracking_confidence_consistency(video_manifest: pd.DataFrame) -> None:
    """Requirement 10: Tracking status and confidence are consistent."""
    for _, row in video_manifest.iloc[::15].iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        conf = arr[:, 22]
        success = arr[:, 23]

        # success_flag must be strictly binary 0.0 or 1.0
        unique_success = set(np.unique(success))
        assert unique_success.issubset({0.0, 1.0}), f"Unexpected success flags: {unique_success}"

        # Failed frames must have confidence < 0.60
        failed_mask = success == 0.0
        if failed_mask.any():
            assert (conf[failed_mask] < CONFIDENCE_THRESHOLD).all(), (
                f"Failed tracking frame has confidence >= {CONFIDENCE_THRESHOLD}"
            )

        # Successful frames must have confidence >= 0.60
        tracked_mask = success == 1.0
        if tracked_mask.any():
            assert (conf[tracked_mask] >= CONFIDENCE_THRESHOLD).all(), (
                f"Tracked frame has confidence < {CONFIDENCE_THRESHOLD}"
            )


def test_11_missing_frame_count_and_dropout_match(video_manifest: pd.DataFrame) -> None:
    """Requirement 11: Missing-frame counts and dropout rates match the tensors exactly."""
    # Verify strict 3% to 10% dropout range across entire manifest
    assert (video_manifest["dropout_rate"] >= 0.03).all(), (
        f"Minimum dropout rate {video_manifest['dropout_rate'].min()} is below 3%"
    )
    assert (video_manifest["dropout_rate"] <= 0.10).all(), (
        f"Maximum dropout rate {video_manifest['dropout_rate'].max()} is above 10%"
    )

    for _, row in video_manifest.iloc[::10].iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        success = arr[:, 23]
        conf = arr[:, 22]

        actual_missing = int((success == 0.0).sum())
        assert actual_missing == row["missing_frame_count"], (
            f"Missing frame mismatch for {row['participant_id']}: {actual_missing} vs {row['missing_frame_count']}"
        )

        expected_dropout = round(actual_missing / len(success), 4)
        assert abs(expected_dropout - row["dropout_rate"]) < 1e-3, (
            f"Dropout rate mismatch for {row['participant_id']}: {expected_dropout} vs {row['dropout_rate']}"
        )

        expected_mean_conf = round(float(conf.mean()), 4)
        assert abs(expected_mean_conf - row["mean_tracking_confidence"]) < 1e-3, (
            f"Mean confidence mismatch for {row['participant_id']}"
        )


def test_12_deterministic_reproducibility() -> None:
    """Requirement 12: Generation is deterministic with seed 42."""
    gen1 = SyntheticVideoGenerator(seed=DEFAULT_RANDOM_SEED)
    gen2 = SyntheticVideoGenerator(seed=DEFAULT_RANDOM_SEED)

    t1, m1 = gen1.generate_single_sequence(participant_sr=42)
    t2, m2 = gen2.generate_single_sequence(participant_sr=42)

    np.testing.assert_array_equal(t1, t2, err_msg="Tensors are not bitwise identical with seed 42")
    assert m1 == m2, "Metadata is not identical across identical seed invocations"


def test_13_provenance_data_origin_tag(video_manifest: pd.DataFrame) -> None:
    """Requirement 13: Correct provenance tags (SYNTHETIC_ABSTRACT_VIDEO_FEATURES)."""
    origins = video_manifest["data_origin"].unique()
    assert len(origins) == 1, f"Expected 1 unique origin tag, got {origins}"
    assert origins[0] == DATA_ORIGIN_TAG, f"Expected {DATA_ORIGIN_TAG}, got {origins[0]}"


def test_14_no_clinical_target_inputs() -> None:
    """Requirement 14: No clinical target inputs or target columns are used."""
    generator = SyntheticVideoGenerator(seed=DEFAULT_RANDOM_SEED)

    # Verify target blocker raises ValueError on prohibited target columns
    with pytest.raises(ValueError, match="Prohibited clinical target input"):
        generator._verify_no_target_inputs("target_canonical_epds_ge_13")

    with pytest.raises(ValueError, match="Prohibited clinical target input"):
        generator._verify_no_target_inputs("EPDS_high_risk_screening_threshold")

    with pytest.raises(ValueError, match="Prohibited clinical target input"):
        generator._verify_no_target_inputs(pd.DataFrame({"epds_score": [15]}))


def test_15_no_actual_image_or_video_files() -> None:
    """Requirement 15: No actual image or video files are generated."""
    video_dir = SYNTHETIC_VIDEO_DIR
    prohibited_extensions = {".mp4", ".avi", ".mov", ".mkv", ".png", ".jpg", ".jpeg", ".bmp", ".gif"}

    for item in video_dir.rglob("*"):
        if item.is_file():
            assert item.suffix.lower() not in prohibited_extensions, (
                f"Prohibited visual media file found: {item}"
            )
            # Allowed files: .csv, .npy, .gitkeep
            assert item.suffix.lower() in {".csv", ".npy", ".gitkeep"}, (
                f"Unexpected file type found: {item}"
            )

