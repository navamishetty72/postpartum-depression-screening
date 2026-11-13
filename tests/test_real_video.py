"""Automated test suite for real-video facial feature extraction and validation.

Validates all 15 core requirements for real video processing:
1. Video readability (OpenCV).
2. Correct FPS and frame count extraction.
3. Correct participant ID and recording ID mapping.
4. OpenFace output availability and dependency handling.
5. Correct feature column mapping (Action Units, Pose, Gaze, Tracking).
6. Correct physical feature units and intervals.
7. Missing-value and frame gap detection.
8. Tracking success and confidence consistency (no zero-imputation of lost faces).
9. NaN and infinity detection across outputs.
10. Correct timestamp alignment and monotonicity.
11. Correct tensor dimensions (T, 24) and float32 dtype.
12. Correct tensor-to-CSV numerical correspondence.
13. Deterministic preprocessing across repeated runs.
14. Correct provenance tags (REAL_VIDEO_OPENFACE).
15. Zero EPDS/PHQ questionnaire or clinical target leakage.
"""

import json
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import pandas as pd
import pytest

cv2 = pytest.importorskip("cv2", reason="opencv-python is required for real video tests")

from pipelines.real_video.config import (
    DATA_ORIGIN_REAL_VIDEO,
    FEATURE_BOUNDS,
    FEATURE_DIM,
    OPENFACE_ACTION_UNITS,
    OPENFACE_GAZE,
    OPENFACE_HEAD_POSE,
    OPENFACE_TRACKING,
    REAL_VIDEO_CHANNEL_NAMES,
)
from pipelines.real_video.cleaner import FeatureCleaner
from pipelines.real_video.openface_runner import OpenFaceNotFoundError, OpenFaceRunner
from pipelines.real_video.pipeline import RealVideoPipeline
from pipelines.real_video.tensor_builder import TensorBuilder
from pipelines.real_video.video_reader import VideoInspectionReport, VideoReader


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def synthetic_openface_csv_data() -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Generate realistic OpenFace 2.0 output DataFrame matching exact OpenFace schema.

    Contains 60 frames:
    - Frames 1-45: Tracked face (success=1, confidence >= 0.85, positive AU activations).
    - Frames 46-55: Tracking failure (success=0, confidence < 0.40, face occluded/turned).
    - Frames 56-60: Re-acquired face (success=1, confidence >= 0.90).
    """
    total_frames = 60
    fps = 30.0
    rng = np.random.default_rng(42)

    records = []
    for i in range(total_frames):
        frame_idx = i + 1
        ts = i / fps

        if 45 <= i < 55:
            # Tracking loss
            success = 0
            conf = float(rng.uniform(0.10, 0.45))
            # OpenFace leaves previous or noisy estimates during loss
            aus = {au: float(rng.uniform(0.0, 1.0)) for au in OPENFACE_ACTION_UNITS}
            pose = {"pose_Rx": 0.5, "pose_Ry": -0.8, "pose_Rz": 0.1}
            gaze = {"gaze_angle_x": 0.4, "gaze_angle_y": -0.3}
        else:
            # Normal tracking
            success = 1
            conf = float(rng.uniform(0.85, 0.98))
            # Meaningful AU activations
            aus = {
                "AU01_r": float(0.5 + 0.3 * np.sin(i * 0.2)),
                "AU02_r": float(0.4 + 0.2 * np.sin(i * 0.2)),
                "AU04_r": float(0.8 + 0.4 * np.cos(i * 0.15)),
                "AU05_r": float(0.1 + 0.1 * rng.uniform(0, 1)),
                "AU06_r": float(1.2 + 0.5 * np.sin(i * 0.1)),
                "AU07_r": float(0.6 + 0.2 * rng.uniform(0, 1)),
                "AU09_r": float(0.1),
                "AU10_r": float(0.3),
                "AU12_r": float(1.5 + 0.6 * np.sin(i * 0.1)),  # Zygomaticus
                "AU14_r": float(0.2),
                "AU15_r": float(0.7 + 0.3 * np.cos(i * 0.1)),
                "AU17_r": float(0.3),
                "AU20_r": float(0.2),
                "AU25_r": float(0.8 + 0.4 * np.sin(i * 0.2)),
            }
            pose = {
                "pose_Rx": float(0.05 * np.sin(i * 0.1)),
                "pose_Ry": float(0.10 * np.cos(i * 0.08)),
                "pose_Rz": float(0.02 * np.sin(i * 0.05)),
            }
            gaze = {
                "gaze_angle_x": float(0.08 * np.sin(i * 0.2)),
                "gaze_angle_y": float(0.05 * np.cos(i * 0.2)),
            }

        rec = {
            "frame": frame_idx,
            "timestamp": ts,
            "confidence": conf,
            "success": success,
        }
        rec.update(aus)
        rec.update(pose)
        rec.update(gaze)
        records.append(rec)

    df = pd.DataFrame(records)
    meta = {"total_frames": total_frames, "fps": fps, "tracked_frames": 50, "untracked_frames": 10}
    return df, meta


@pytest.fixture(scope="module")
def test_video_and_csv_file(tmp_path_factory, synthetic_openface_csv_data) -> Dict[str, Path]:
    """Create actual video file on disk via OpenCV and corresponding OpenFace CSV."""
    tmp_dir = tmp_path_factory.mktemp("real_video_test_env")
    raw_df, _ = synthetic_openface_csv_data

    # 1. Create real video file using OpenCV
    video_path = tmp_dir / "BGD_001_session1.mp4"
    VideoReader.create_synthetic_test_video(
        output_path=video_path,
        num_frames=60,
        fps=30.0,
        width=320,
        height=240,
    )

    # 2. Save matching OpenFace CSV
    csv_path = tmp_dir / "BGD_001_session1.csv"
    raw_df.to_csv(csv_path, index=False)

    return {"video_path": video_path, "csv_path": csv_path, "dir": tmp_dir}


# -----------------------------------------------------------------------------
# 15 Core Automated Tests
# -----------------------------------------------------------------------------

def test_1_video_readability(test_video_and_csv_file: Dict[str, Path]) -> None:
    """Requirement 1: OpenCV video readability and corruption detection."""
    reader = VideoReader()
    video_path = test_video_and_csv_file["video_path"]

    # Test valid video file
    report = reader.inspect_video(video_path, exhaustive_frame_check=True)
    assert report.is_readable is True
    assert report.error_message is None
    assert report.width == 320
    assert report.height == 240
    assert report.decoded_frame_count == 60
    assert report.corrupted_frame_count == 0

    # Test non-existent file
    bad_report = reader.inspect_video(Path("non_existent_file.mp4"))
    assert bad_report.is_readable is False
    assert "does not exist" in bad_report.error_message


def test_2_correct_fps_and_frame_count(test_video_and_csv_file: Dict[str, Path]) -> None:
    """Requirement 2: Accurate extraction of FPS, frame count, duration, and resolution."""
    reader = VideoReader()
    report = reader.inspect_video(test_video_and_csv_file["video_path"])

    assert abs(report.fps - 30.0) < 0.1
    assert report.frame_count == 60
    assert abs(report.duration_sec - 2.0) < 0.1
    assert report.width > 0 and report.height > 0
    assert len(report.frame_timestamps) == 60


def test_3_correct_participant_id_mapping(test_video_and_csv_file: Dict[str, Path]) -> None:
    """Requirement 3: Accurate participant ID and recording ID mapping."""
    pipeline = RealVideoPipeline(output_dir=test_video_and_csv_file["dir"] / "output")
    res = pipeline.process_single_video(
        video_path=test_video_and_csv_file["video_path"],
        participant_id="BGD_042",
        recording_id="session1",
        precomputed_openface_csv=test_video_and_csv_file["csv_path"],
    )

    assert res["participant_id"] == "BGD_042"
    assert res["recording_id"] == "session1"

    # Verify summary JSON reflects ID
    summary_path = pipeline.summaries_dir / "BGD_042_summary.json"
    assert summary_path.is_file()
    with open(summary_path, "r", encoding="utf-8") as f:
        summary_data = json.load(f)
    assert summary_data["participant_id"] == "BGD_042"


def test_4_openface_output_availability() -> None:
    """Requirement 4: OpenFace availability check and graceful missing-dependency reporting."""
    runner = OpenFaceRunner(binary_path=Path("non_existent_openface_binary.exe"))
    status = runner.check_availability()

    assert status["available"] is False
    assert status["status"] == "NOT_FOUND"
    assert runner.binary_path is None

    # Verify runner raises OpenFaceNotFoundError with clear instructions
    with pytest.raises(OpenFaceNotFoundError) as exc_info:
        runner.run_extraction(Path("video.mp4"), Path("output"))
    assert "https://github.com/TadasBaltrusaitis/OpenFace" in str(exc_info.value)


def test_4_explicit_invalid_path_no_fallback(monkeypatch, tmp_path: Path) -> None:
    """Verify that an explicit invalid binary path NEVER falls back to env or host binaries."""
    # Point OPENFACE_BIN_PATH to a valid system executable
    valid_mock = Path("C:/Windows/System32/cmd.exe") if Path("C:/Windows/System32/cmd.exe").is_file() else None
    if valid_mock:
        monkeypatch.setenv("OPENFACE_BIN_PATH", str(valid_mock))

    # 1. Non-existent explicit path must not fall back to OPENFACE_BIN_PATH
    non_existent = tmp_path / "non_existent_custom_openface.exe"
    runner_bad = OpenFaceRunner(binary_path=non_existent)
    assert runner_bad.binary_path is None
    status_bad = runner_bad.check_availability()
    assert status_bad["available"] is False
    assert status_bad["status"] == "NOT_FOUND"
    assert "Fallback to automatic discovery is disabled" in status_bad["message"]

    # 2. Existing non-executable file (e.g. text file) must not be accepted or fall back
    txt_file = tmp_path / "not_an_executable.txt"
    txt_file.write_text("dummy", encoding="utf-8")
    runner_txt = OpenFaceRunner(binary_path=txt_file)
    assert runner_txt.binary_path is None
    status_txt = runner_txt.check_availability()
    assert status_txt["available"] is False
    assert status_txt["status"] == "NOT_FOUND"


def test_4_automatic_discovery_when_no_explicit_path(monkeypatch) -> None:
    """Verify automatic discovery preserves environment and system path lookup when binary_path=None."""
    valid_mock = Path("C:/Windows/System32/cmd.exe") if Path("C:/Windows/System32/cmd.exe").is_file() else None
    if valid_mock:
        monkeypatch.setenv("OPENFACE_BIN_PATH", str(valid_mock))
        runner_auto = OpenFaceRunner(binary_path=None)
        assert runner_auto.binary_path == valid_mock.resolve()
        status_auto = runner_auto.check_availability()
        assert status_auto["available"] is True
        assert status_auto["status"] == "READY"
        assert status_auto["binary_path"] == str(valid_mock.resolve())


def test_4_automatic_discovery_not_found(monkeypatch) -> None:
    """Verify that when no binary exists anywhere, automatic discovery reports NOT_FOUND."""
    monkeypatch.delenv("OPENFACE_BIN_PATH", raising=False)
    monkeypatch.delenv("OPENFACE_EXE", raising=False)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("USERPROFILE", "C:/non_existent_user_dir_xyz")

    runner = OpenFaceRunner(binary_path=None)
    if runner.binary_path is None:
        status = runner.check_availability()
        assert status["available"] is False
        assert status["status"] == "NOT_FOUND"
        assert "is not installed or not on PATH" in status["message"]


def test_5_correct_feature_column_mapping(synthetic_openface_csv_data) -> None:
    """Requirement 5: Correct feature column mapping for AUs, Pose, Gaze, and Tracking."""
    raw_df, _ = synthetic_openface_csv_data
    cleaner = FeatureCleaner()
    cleaned_df, report = cleaner.clean_features(raw_df)

    # 14 Action Units
    for au in OPENFACE_ACTION_UNITS:
        assert au in cleaned_df.columns, f"Action unit {au} missing from cleaned columns"

    # 3 Head Pose
    for pose in OPENFACE_HEAD_POSE:
        assert pose in cleaned_df.columns, f"Head pose {pose} missing from cleaned columns"

    # 2 Gaze
    for gaze in OPENFACE_GAZE:
        assert gaze in cleaned_df.columns, f"Gaze {gaze} missing from cleaned columns"

    # 2 Tracking
    for trk in OPENFACE_TRACKING:
        assert trk in cleaned_df.columns, f"Tracking {trk} missing from cleaned columns"

    # Derived metrics
    assert "gaze_stability" in cleaned_df.columns
    assert "rigid_motion" in cleaned_df.columns
    assert "non_rigid_motion" in cleaned_df.columns


def test_6_correct_feature_units(synthetic_openface_csv_data) -> None:
    """Requirement 6: Features fall strictly within physical units and theoretical intervals."""
    raw_df, _ = synthetic_openface_csv_data
    cleaner = FeatureCleaner()
    cleaned_df, _ = cleaner.clean_features(raw_df)

    for ch_name, (lower, upper) in FEATURE_BOUNDS.items():
        if ch_name in cleaned_df.columns:
            vals = cleaned_df[ch_name].values.astype(float)
            assert vals.min() >= lower - 1e-4, f"{ch_name} min {vals.min()} < {lower}"
            assert vals.max() <= upper + 1e-4, f"{ch_name} max {vals.max()} > {upper}"


def test_7_missing_value_detection(synthetic_openface_csv_data) -> None:
    """Requirement 7: Detection and documentation of tracking failures and missing values."""
    raw_df, meta = synthetic_openface_csv_data
    cleaner = FeatureCleaner()
    cleaned_df, report = cleaner.clean_features(raw_df)

    assert report.total_frames_input == 60
    assert report.tracked_frames_count == meta["tracked_frames"]
    assert report.untracked_frames_count == meta["untracked_frames"]
    assert abs(report.tracking_success_rate - (50 / 60)) < 1e-3


def test_8_tracking_success_and_confidence_consistency(synthetic_openface_csv_data) -> None:
    """Requirement 8: Tracking failure handling separates lost tracking from genuine zero AU values."""
    raw_df, _ = synthetic_openface_csv_data
    cleaner = FeatureCleaner()
    cleaned_df, _ = cleaner.clean_features(raw_df)

    # In frames 45-54, tracking failed (success == 0)
    failed_frames = cleaned_df[cleaned_df["success"] == 0]
    assert len(failed_frames) == 10
    assert (failed_frames["is_valid_face"] == False).all()

    # Tracked frames (success == 1)
    tracked_frames = cleaned_df[cleaned_df["success"] == 1]
    assert len(tracked_frames) == 50
    assert (tracked_frames["is_valid_face"] == True).all()

    # CRITICAL: Verify tracked AU12_r is NOT silently zeroed out in valid frames
    assert tracked_frames["AU12_r"].mean() > 1.0


def test_9_nan_and_infinity_detection(synthetic_openface_csv_data) -> None:
    """Requirement 9: Detection of NaNs and Infinities across outputs."""
    raw_df, _ = synthetic_openface_csv_data
    cleaner = FeatureCleaner()
    cleaned_df, report = cleaner.clean_features(raw_df)

    builder = TensorBuilder()
    tensor = builder.build_temporal_tensor(cleaned_df)

    assert not np.isnan(tensor).any(), "NaN found in assembled temporal tensor"
    assert not np.isinf(tensor).any(), "Inf found in assembled temporal tensor"


def test_10_correct_timestamp_alignment(synthetic_openface_csv_data) -> None:
    """Requirement 10: Monotonicity and timestamp alignment."""
    raw_df, _ = synthetic_openface_csv_data
    cleaner = FeatureCleaner()
    cleaned_df, _ = cleaner.clean_features(raw_df)

    ts = cleaned_df["timestamp"].values
    assert (np.diff(ts) > 0).all(), "Timestamps are not strictly monotonically increasing"
    assert ts[0] == 0.0
    assert abs(ts[-1] - (59 / 30.0)) < 1e-4


def test_11_correct_tensor_dimensions(synthetic_openface_csv_data) -> None:
    """Requirement 11: Tensor dimensions are (T, 24) and dtype is float32."""
    raw_df, _ = synthetic_openface_csv_data
    cleaner = FeatureCleaner()
    cleaned_df, _ = cleaner.clean_features(raw_df)

    builder = TensorBuilder()
    tensor = builder.build_temporal_tensor(cleaned_df)

    assert tensor.ndim == 2
    assert tensor.shape == (60, FEATURE_DIM)
    assert tensor.shape[1] == 24
    assert tensor.dtype == np.float32


def test_12_correct_tensor_to_csv_correspondence(synthetic_openface_csv_data) -> None:
    """Requirement 12: Tensor values match cleaned CSV values exactly for tracked frames."""
    raw_df, _ = synthetic_openface_csv_data
    cleaner = FeatureCleaner()
    cleaned_df, _ = cleaner.clean_features(raw_df)

    builder = TensorBuilder()
    tensor = builder.build_temporal_tensor(cleaned_df)

    # Check frame 10 (tracked frame)
    row_10 = cleaned_df.iloc[10]
    for ch_idx, ch_name in enumerate(REAL_VIDEO_CHANNEL_NAMES):
        expected_val = float(row_10[ch_name])
        tensor_val = float(tensor[10, ch_idx])
        assert abs(tensor_val - expected_val) < 1e-4, (
            f"Discrepancy at ch {ch_name}: tensor={tensor_val}, csv={expected_val}"
        )


def test_13_deterministic_preprocessing(synthetic_openface_csv_data) -> None:
    """Requirement 13: Preprocessing is strictly deterministic."""
    raw_df, _ = synthetic_openface_csv_data
    cleaner = FeatureCleaner()

    df1, _ = cleaner.clean_features(raw_df)
    df2, _ = cleaner.clean_features(raw_df)

    pd.testing.assert_frame_equal(df1, df2)

    builder = TensorBuilder()
    t1 = builder.build_temporal_tensor(df1)
    t2 = builder.build_temporal_tensor(df2)
    np.testing.assert_array_equal(t1, t2)


def test_14_correct_provenance_labels(test_video_and_csv_file: Dict[str, Path]) -> None:
    """Requirement 14: Output metadata contains correct provenance tag REAL_VIDEO_OPENFACE."""
    pipeline = RealVideoPipeline(output_dir=test_video_and_csv_file["dir"] / "output")
    res = pipeline.process_single_video(
        video_path=test_video_and_csv_file["video_path"],
        participant_id="BGD_001",
        precomputed_openface_csv=test_video_and_csv_file["csv_path"],
    )

    summary_path = pipeline.summaries_dir / "BGD_001_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    assert summary["data_origin"] == DATA_ORIGIN_REAL_VIDEO
    assert summary["pipeline_version"] == "1.0.0"


def test_15_no_epds_phq_target_leakage(synthetic_openface_csv_data) -> None:
    """Requirement 15: Zero EPDS, PHQ, or canonical targets permitted in inputs."""
    raw_df, _ = synthetic_openface_csv_data
    cleaner = FeatureCleaner()

    # Injected EPDS item
    leaky_df_1 = raw_df.copy()
    leaky_df_1["epds_score"] = 14
    with pytest.raises(ValueError, match="CRITICAL TARGET LEAKAGE"):
        cleaner.clean_features(leaky_df_1)

    # Injected PHQ-9 item
    leaky_df_2 = raw_df.copy()
    leaky_df_2["phq9_item_1"] = 2
    with pytest.raises(ValueError, match="CRITICAL TARGET LEAKAGE"):
        cleaner.clean_features(leaky_df_2)

    # Injected canonical target
    leaky_df_3 = raw_df.copy()
    leaky_df_3["target_canonical_epds_ge_13"] = 1
    with pytest.raises(ValueError, match="CRITICAL TARGET LEAKAGE"):
        cleaner.clean_features(leaky_df_3)


def test_cohort_processing_summary(test_video_and_csv_file: Dict[str, Path]) -> None:
    """Verify that cohort summary computes all 8 required metrics."""
    out_dir = test_video_and_csv_file["dir"] / "cohort_out"
    pipeline = RealVideoPipeline(output_dir=out_dir)

    # Process video into this pipeline
    pipeline.process_single_video(
        video_path=test_video_and_csv_file["video_path"],
        participant_id="BGD_001",
        precomputed_openface_csv=test_video_and_csv_file["csv_path"],
    )

    # Fake a second video that failed extraction to verify failure counting
    manifest_rows = [
        {
            "participant_id": "BGD_001",
            "recording_id": "session1",
            "split_partition": "train",
            "data_origin": DATA_ORIGIN_REAL_VIDEO,
            "pipeline_version": "1.0.0",
            "video_path": str(test_video_and_csv_file["video_path"]),
            "fps": 30.0,
            "frame_count": 60,
            "duration_sec": 2.0,
            "width": 320,
            "height": 240,
            "corrupted_frame_count": 0,
            "corrupted_frame_percentage": 0.0,
            "tracked_frames_count": 50,
            "tracking_success_rate": 0.8333,
            "mean_tracking_confidence": 0.91,
            "qc_status": "PASS",
            "processing_status": "SUCCESS",
            "error_message": None,
        },
        {
            "participant_id": "BGD_002",
            "recording_id": "session2",
            "split_partition": "test",
            "data_origin": DATA_ORIGIN_REAL_VIDEO,
            "pipeline_version": "1.0.0",
            "video_path": "fake_path.mp4",
            "fps": 0.0,
            "frame_count": 0,
            "duration_sec": 0.0,
            "width": 0,
            "height": 0,
            "corrupted_frame_count": 0,
            "corrupted_frame_percentage": 0.0,
            "tracked_frames_count": 0,
            "tracking_success_rate": 0.0,
            "mean_tracking_confidence": 0.0,
            "qc_status": "FAIL",
            "processing_status": "FAILED_OPENFACE_UNAVAILABLE",
            "error_message": "OpenFace binary not found",
        },
    ]
    manifest_df = pd.DataFrame(manifest_rows)
    summary = pipeline.generate_processing_summary(manifest_df)

    assert summary["total_videos_discovered"] == 2
    assert summary["successfully_processed"] == 1
    assert summary["failed_videos"] == 1
    assert summary["feature_extraction_errors"] == 1
    assert summary["average_tracking_success_rate"] == 0.8333
    assert "output_files_generated" in summary

