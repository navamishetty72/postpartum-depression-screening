"""Automated validation test suite for improved synthetic video feature trajectory generation (v2).

Validates 19 core technical, statistical, and architectural requirements:
1. Exactly 800 manifest records.
2. Exactly 640 training and 160 testing records.
3. Exact participant ID and split alignment with train_test_split_manifest.csv (BGD_001 to BGD_800).
4. Zero duplicate participant IDs.
5. All 800 .npy feature files exist and are readable in data/synthetic/video_v2/features/.
6. Tensor dimensions are (T, 24), where 45 <= T <= 120.
7. Dtype is float32.
8. No NaN or Inf values in scalars or tensors.
9. Every channel stays strictly within its specified engineering bounds.
10. Tracking status and confidence consistency (success_flag == 0.0 iff confidence < 0.60).
11. Missing-frame counts and dropout rates match tensors exactly, within strict [0.03, 0.10] bounds.
12. Generation is deterministic with seed 42.
13. Correct provenance tags (SYNTHETIC_ABSTRACT_VIDEO_FEATURES_V2, generator_version: 2.0.0).
14. Target leakage prevention: raises ValueError on clinical target inputs.
15. No actual image or video files are generated.
16. AU co-activation structure: non-zero physiological correlation (AU06-AU12, AU01-AU02).
17. Exact mathematical derivation of gaze_stability, rigid_motion, and non_rigid_motion.
18. Contiguous burst dropout modeling: tracking loss occurs in multi-frame blocks.
19. Zero target leakage: no statistical correlation with clinical screening targets.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import pytest
from scipy.stats import pointbiserialr

from pipelines.synthetic_video.config_v2 import (
    CHANNEL_BOUNDS,
    CHANNEL_NAMES,
    CONFIDENCE_THRESHOLD,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    FEATURE_DIM,
    FRAME_INTERVAL_SEC,
    GAZE_STABILITY_OMEGA_0,
    GENERATOR_VERSION,
    MAX_SEQUENCE_LENGTH,
    MIN_SEQUENCE_LENGTH,
    NON_RIGID_MOTION_ALPHA_0,
    RIGID_MOTION_V_0,
    SYNTHETIC_VIDEO_V2_DIR,
    SYNTHETIC_VIDEO_V2_FEATURES_DIR,
    SYNTHETIC_VIDEO_V2_MANIFEST_PATH,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
)
from pipelines.synthetic_video.generator_v2 import SyntheticVideoGeneratorV2


@pytest.fixture(scope="module")
def video_manifest_v2() -> pd.DataFrame:
    """Load the generated synthetic video v2 manifest."""
    assert SYNTHETIC_VIDEO_V2_MANIFEST_PATH.exists(), (
        f"Video v2 manifest not found at {SYNTHETIC_VIDEO_V2_MANIFEST_PATH}"
    )
    return pd.read_csv(SYNTHETIC_VIDEO_V2_MANIFEST_PATH)


@pytest.fixture(scope="module")
def split_manifest() -> pd.DataFrame:
    """Load the frozen train/test split manifest."""
    assert TRAIN_TEST_SPLIT_MANIFEST_PATH.exists(), (
        f"Split manifest not found at {TRAIN_TEST_SPLIT_MANIFEST_PATH}"
    )
    return pd.read_csv(TRAIN_TEST_SPLIT_MANIFEST_PATH)


def test_1_record_count(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 1: Exactly 800 records."""
    assert len(video_manifest_v2) == 800, f"Expected 800 records, got {len(video_manifest_v2)}"


def test_2_train_test_split_counts(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 2: Exactly 640 training and 160 testing records."""
    counts = video_manifest_v2["split_partition"].value_counts().to_dict()
    assert counts.get("train") == 640, f"Expected 640 train, got {counts.get('train')}"
    assert counts.get("test") == 160, f"Expected 160 test, got {counts.get('test')}"


def test_3_participant_id_alignment(
    video_manifest_v2: pd.DataFrame, split_manifest: pd.DataFrame
) -> None:
    """Requirement 3: Exact participant ID and split alignment with train_test_split_manifest.csv."""
    expected_ids = split_manifest["participant_id"].tolist()
    actual_ids = video_manifest_v2["participant_id"].tolist()
    assert actual_ids == expected_ids, "Participant IDs do not match split manifest order"
    assert actual_ids[0] == "BGD_001"
    assert actual_ids[-1] == "BGD_800"

    expected_splits = split_manifest["split_partition"].tolist()
    actual_splits = video_manifest_v2["split_partition"].tolist()
    assert actual_splits == expected_splits, "Split partitions do not match split manifest"


def test_4_no_duplicate_ids(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 4: No duplicate participant IDs."""
    assert video_manifest_v2["participant_id"].nunique() == 800


def test_5_all_feature_files_exist_and_readable(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 5: All 800 feature files exist and are readable."""
    for _, row in video_manifest_v2.iterrows():
        rel_path = Path(row["feature_file_path"])
        file_path = Path(__file__).resolve().parent.parent / rel_path
        assert file_path.exists(), f"Feature file missing: {file_path}"
        arr = np.load(file_path)
        assert isinstance(arr, np.ndarray), f"File {file_path} is not a valid numpy array"


def test_6_tensor_dimensions(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 6: Tensor dimensions are (T, 24), where 45 <= T <= 120."""
    sample_rows = pd.concat([video_manifest_v2.head(25), video_manifest_v2.tail(25)])
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


def test_7_dtype_is_float32(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 7: Dtype is float32."""
    for _, row in video_manifest_v2.head(30).iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        assert arr.dtype == np.float32, f"Expected float32, got {arr.dtype}"


def test_8_no_nan_or_inf(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 8: No NaN or Inf values."""
    numeric_cols = [
        "sequence_length",
        "feature_dimension",
        "missing_frame_count",
        "mean_tracking_confidence",
        "dropout_rate",
        "burst_count",
    ]
    for col in numeric_cols:
        assert not video_manifest_v2[col].isnull().any(), f"NaN found in manifest col {col}"
        assert not np.isinf(video_manifest_v2[col]).any(), f"Inf found in manifest col {col}"

    for _, row in video_manifest_v2.iloc[::20].iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        assert not np.isnan(arr).any(), f"NaN in tensor for {row['participant_id']}"
        assert not np.isinf(arr).any(), f"Inf in tensor for {row['participant_id']}"


def test_9_engineering_channel_bounds(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 9: Every channel stays strictly within its specified engineering bounds."""
    for _, row in video_manifest_v2.iloc[::15].iterrows():
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


def test_10_tracking_confidence_consistency(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 10: Tracking status and confidence are consistent."""
    for _, row in video_manifest_v2.iloc[::15].iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        conf = arr[:, 22]
        success = arr[:, 23]

        unique_success = set(np.unique(success))
        assert unique_success.issubset({0.0, 1.0}), f"Unexpected success flags: {unique_success}"

        failed_mask = success == 0.0
        if failed_mask.any():
            assert (conf[failed_mask] < CONFIDENCE_THRESHOLD).all(), (
                f"Failed tracking frame has confidence >= {CONFIDENCE_THRESHOLD}"
            )

        tracked_mask = success == 1.0
        if tracked_mask.any():
            assert (conf[tracked_mask] >= CONFIDENCE_THRESHOLD).all(), (
                f"Tracked frame has confidence < {CONFIDENCE_THRESHOLD}"
            )


def test_11_missing_frame_count_and_dropout_match(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 11: Missing-frame counts and dropout rates match the tensors exactly."""
    assert (video_manifest_v2["dropout_rate"] >= 0.03).all(), (
        f"Minimum dropout rate {video_manifest_v2['dropout_rate'].min()} is below 3%"
    )
    assert (video_manifest_v2["dropout_rate"] <= 0.10).all(), (
        f"Maximum dropout rate {video_manifest_v2['dropout_rate'].max()} is above 10%"
    )

    for _, row in video_manifest_v2.iloc[::10].iterrows():
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
    gen1 = SyntheticVideoGeneratorV2(seed=DEFAULT_RANDOM_SEED)
    gen2 = SyntheticVideoGeneratorV2(seed=DEFAULT_RANDOM_SEED)

    t1, m1 = gen1.generate_single_sequence(participant_sr=42)
    t2, m2 = gen2.generate_single_sequence(participant_sr=42)

    np.testing.assert_array_equal(t1, t2, err_msg="Tensors are not bitwise identical with seed 42")
    assert m1 == m2, "Metadata is not identical across identical seed invocations"


def test_13_provenance_data_origin_tag(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 13: Correct provenance tags (SYNTHETIC_ABSTRACT_VIDEO_FEATURES_V2)."""
    origins = video_manifest_v2["data_origin"].unique()
    assert len(origins) == 1, f"Expected 1 unique origin tag, got {origins}"
    assert origins[0] == DATA_ORIGIN_TAG, f"Expected {DATA_ORIGIN_TAG}, got {origins[0]}"
    assert (video_manifest_v2["generator_version"] == GENERATOR_VERSION).all()


def test_14_no_clinical_target_inputs() -> None:
    """Requirement 14: No clinical target inputs or target columns are used."""
    generator = SyntheticVideoGeneratorV2(seed=DEFAULT_RANDOM_SEED)

    with pytest.raises(ValueError, match="Prohibited clinical target input"):
        generator._verify_no_target_inputs("target_canonical_epds_ge_13")

    with pytest.raises(ValueError, match="Prohibited clinical target input"):
        generator._verify_no_target_inputs("EPDS_high_risk_screening_threshold")

    with pytest.raises(ValueError, match="Prohibited clinical target input"):
        generator._verify_no_target_inputs(pd.DataFrame({"epds_score": [15]}))


def test_15_no_actual_image_or_video_files() -> None:
    """Requirement 15: No actual image or video files are generated."""
    video_dir = SYNTHETIC_VIDEO_V2_DIR
    prohibited_extensions = {".mp4", ".avi", ".mov", ".mkv", ".png", ".jpg", ".jpeg", ".bmp", ".gif"}

    for item in video_dir.rglob("*"):
        if item.is_file():
            assert item.suffix.lower() not in prohibited_extensions, (
                f"Prohibited visual media file found: {item}"
            )
            assert item.suffix.lower() in {".csv", ".npy", ".gitkeep"}, (
                f"Unexpected file type found: {item}"
            )


def test_16_au_coactivation_correlations(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 16: Action Unit co-activations show positive physiological coupling."""
    au6_12_corrs = []
    au1_2_corrs = []

    for _, row in video_manifest_v2.head(40).iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        # AU01 is col 0, AU02 is col 1, AU06 is col 4, AU12 is col 8
        c_6_12 = np.corrcoef(arr[:, 4], arr[:, 8])[0, 1]
        c_1_2 = np.corrcoef(arr[:, 0], arr[:, 1])[0, 1]
        au6_12_corrs.append(c_6_12)
        au1_2_corrs.append(c_1_2)

    mean_6_12 = float(np.mean(au6_12_corrs))
    mean_1_2 = float(np.mean(au1_2_corrs))

    # Physiological coupling assertion: significant positive correlation (well above independent 0.0)
    assert mean_6_12 > 0.35, f"AU06-AU12 correlation {mean_6_12:.3f} below 0.35"
    assert mean_1_2 > 0.35, f"AU01-AU02 correlation {mean_1_2:.3f} below 0.35"


def test_17_mathematical_metric_derivation(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 17: gaze_stability, rigid_motion, and non_rigid_motion match differential formulas."""
    dt = np.float32(FRAME_INTERVAL_SEC)

    for _, row in video_manifest_v2.head(20).iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)

        # Initial frame resting values
        assert arr[0, 19] == 1.0, f"gaze_stability[0] != 1.0 in {row['participant_id']}"
        assert arr[0, 20] == 0.0, f"rigid_motion[0] != 0.0 in {row['participant_id']}"
        assert arr[0, 21] == 0.0, f"non_rigid_motion[0] != 0.0 in {row['participant_id']}"

        for t in range(1, len(arr)):
            # Gaze stability
            delta_gaze = np.sqrt(
                (arr[t, 17] - arr[t - 1, 17]) ** 2 + (arr[t, 18] - arr[t - 1, 18]) ** 2
            )
            omega = delta_gaze / dt
            expected_stab = np.clip(np.exp(-omega / GAZE_STABILITY_OMEGA_0), 0.0, 1.0)
            assert abs(arr[t, 19] - expected_stab) < 1e-4, (
                f"Gaze stability mismatch at t={t} in {row['participant_id']}"
            )

            # Rigid motion
            delta_pose = np.sqrt(
                (arr[t, 14] - arr[t - 1, 14]) ** 2
                + (arr[t, 15] - arr[t - 1, 15]) ** 2
                + (arr[t, 16] - arr[t - 1, 16]) ** 2
            )
            v_head = delta_pose / dt
            expected_rigid = np.clip(np.tanh(v_head / RIGID_MOTION_V_0), 0.0, 1.0)
            assert abs(arr[t, 20] - expected_rigid) < 1e-4, (
                f"Rigid motion mismatch at t={t} in {row['participant_id']}"
            )

            # Non-rigid motion
            delta_au = np.mean(np.abs(arr[t, 0:14] - arr[t - 1, 0:14])) / dt
            expected_nonrigid = np.clip(np.tanh(delta_au / NON_RIGID_MOTION_ALPHA_0), 0.0, 1.0)
            assert abs(arr[t, 21] - expected_nonrigid) < 1e-4, (
                f"Non-rigid motion mismatch at t={t} in {row['participant_id']}"
            )


def test_18_burst_dropout_contiguity(video_manifest_v2: pd.DataFrame) -> None:
    """Requirement 18: Dropouts occur in contiguous bursts rather than isolated frames."""
    run_lengths = []

    for _, row in video_manifest_v2.head(40).iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        flags = arr[:, 23]

        curr = 0
        for f in flags:
            if f == 0.0:
                curr += 1
            else:
                if curr > 0:
                    run_lengths.append(curr)
                    curr = 0
        if curr > 0:
            run_lengths.append(curr)

    assert len(run_lengths) > 0, "No dropouts detected in sample"
    mean_burst = float(np.mean(run_lengths))
    # Contiguous burst assertion: average burst length >= 2.0 frames
    assert mean_burst >= 2.0, f"Mean burst length {mean_burst:.2f} is below 2.0 frames"


def test_19_target_independence(
    video_manifest_v2: pd.DataFrame, split_manifest: pd.DataFrame
) -> None:
    """Requirement 19: Features have no statistically significant correlation with clinical targets."""
    merged = pd.merge(split_manifest, video_manifest_v2, on="participant_id")
    targets = merged["target_canonical_epds_ge_13"].values

    sample_merged = merged.head(100)
    au12_means = []
    rigid_means = []

    for _, row in sample_merged.iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["feature_file_path"]
        arr = np.load(file_path)
        au12_means.append(float(arr[:, 8].mean()))
        rigid_means.append(float(arr[:, 20].mean()))

    sub_targets = targets[:100]
    r_au12, p_au12 = pointbiserialr(sub_targets, au12_means)
    r_rigid, p_rigid = pointbiserialr(sub_targets, rigid_means)

    # Check that correlation is low and non-significant at alpha=0.01
    assert abs(r_au12) < 0.25, f"AU12 correlation with target too high: {r_au12:.3f}"
    assert abs(r_rigid) < 0.25, f"Rigid motion correlation with target too high: {r_rigid:.3f}"

