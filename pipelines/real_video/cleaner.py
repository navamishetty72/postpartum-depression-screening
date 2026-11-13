"""Feature cleaning, transformation, and validation module.

Implements rigorous preprocessing on raw OpenFace outputs:
- Preserves exact frame presentation timestamps and sequence indices.
- Separates tracking failure (success=0) from genuine zero-valued facial activations.
- Detects invalid numerical ranges, NaNs, and Infs.
- Computes mathematically documented derived gaze stability and motion metrics.
- Enforces strict target isolation against clinical questionnaire and target leakage.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from .config import (
    EXCLUDED_TARGET_KEYWORDS,
    FEATURE_BOUNDS,
    MIN_CONFIDENCE_TRACKED,
    OPENFACE_ACTION_UNITS,
    OPENFACE_GAZE,
    OPENFACE_HEAD_POSE,
    OPENFACE_METADATA_COLS,
    OPENFACE_TRACKING,
    REAL_VIDEO_CHANNEL_NAMES,
)


@dataclass
class CleaningTransformationReport:
    """Audit report documenting feature transformations applied during cleaning."""

    total_frames_input: int
    total_frames_output: int
    tracked_frames_count: int
    untracked_frames_count: int
    tracking_success_rate: float
    mean_confidence: float
    out_of_bounds_clipped_count: int
    nans_detected_in_raw: int
    infs_detected_in_raw: int
    derived_metrics_computed: List[str]
    transformations_applied: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return asdict(self)


class FeatureCleaner:
    """Preprocesses and validates raw OpenFace facial feature extractions."""

    def __init__(
        self,
        min_confidence: float = MIN_CONFIDENCE_TRACKED,
        clip_bounds: bool = True,
    ) -> None:
        self.min_confidence = min_confidence
        self.clip_bounds = clip_bounds

    def _verify_no_target_leakage(self, df: pd.DataFrame) -> None:
        """Assert that zero clinical survey targets or questionnaire items exist in input."""
        cols = [str(c).lower() for c in df.columns]
        for c in cols:
            for kw in EXCLUDED_TARGET_KEYWORDS:
                if kw in c:
                    raise ValueError(
                        f"CRITICAL TARGET LEAKAGE: Prohibited keyword '{kw}' found in column '{c}'."
                    )

    def clean_features(
        self,
        raw_df: pd.DataFrame,
        recording_fps: Optional[float] = None,
    ) -> Tuple[pd.DataFrame, CleaningTransformationReport]:
        """Clean raw OpenFace DataFrame and compute derived motion/gaze stability features.

        Args:
            raw_df: Parsed DataFrame from OpenFace FeatureExtraction CSV.
            recording_fps: Optional nominal FPS from video inspection for timing validation.

        Returns:
            Tuple[pd.DataFrame, CleaningTransformationReport]: Cleaned frame-level DataFrame and report.
        """
        # 1. Strict Target Isolation Check
        self._verify_no_target_leakage(raw_df)

        df = raw_df.copy()
        df.columns = df.columns.astype(str).str.strip()

        transformations_applied: List[str] = [
            "whitespace_stripped_from_column_headers",
            "target_leakage_safeguard_verified",
        ]

        total_frames = len(df)
        if total_frames == 0:
            raise ValueError("Input OpenFace DataFrame contains 0 frames.")

        # 2. Preserve Frame Timestamps and Indices
        if "frame" not in df.columns:
            df["frame"] = np.arange(1, total_frames + 1, dtype=int)
            transformations_applied.append("frame_indices_synthesized_from_row_numbers")

        if "timestamp" not in df.columns:
            fps_val = recording_fps if (recording_fps and recording_fps > 0) else 30.0
            df["timestamp"] = np.arange(total_frames, dtype=float) / fps_val
            transformations_applied.append(f"timestamps_synthesized_using_fps_{fps_val:.2f}")

        # Ensure monotonic timestamps
        ts = df["timestamp"].values.astype(float)
        dt = np.diff(ts, prepend=ts[0] - (1.0 / (recording_fps or 30.0)))
        # Replace zero or negative dt with minimum delta to prevent division by zero
        dt = np.where(dt <= 0.0, 1.0 / (recording_fps or 30.0), dt)

        # 3. Detect NaNs and Infs in Raw Data
        raw_feature_cols = [
            c for c in (OPENFACE_ACTION_UNITS + OPENFACE_HEAD_POSE + OPENFACE_GAZE + OPENFACE_TRACKING)
            if c in df.columns
        ]
        nans_count = int(df[raw_feature_cols].isna().sum().sum())
        infs_count = int(np.isinf(df[raw_feature_cols].select_dtypes(include=[np.number])).sum().sum())

        # 4. Handle Tracking Failures
        # SCIENTIFIC PRINCIPLE: In FACS, AU = 0.0 means 'muscle relaxed', NOT 'tracking failed'.
        # We preserve success and confidence, and flag untracked frames explicitly.
        success_raw = df["success"].values.astype(int)
        conf_raw = df["confidence"].values.astype(float)

        # Valid face tracking mask: OpenFace reported success == 1 AND confidence >= threshold
        is_tracked_mask = (success_raw == 1) & (conf_raw >= self.min_confidence)
        tracked_count = int(is_tracked_mask.sum())
        untracked_count = total_frames - tracked_count
        tracking_rate = float(tracked_count / total_frames)
        mean_conf = float(conf_raw.mean())

        # Add explicit tracking quality flag
        df["is_valid_face"] = is_tracked_mask
        transformations_applied.append(
            f"tracking_status_evaluated_with_min_confidence_{self.min_confidence:.2f}"
        )

        # 5. Out-of-bounds Clipping (if enabled)
        clipped_count = 0
        if self.clip_bounds:
            for ch in raw_feature_cols:
                if ch in FEATURE_BOUNDS and ch in df.columns:
                    lower, upper = FEATURE_BOUNDS[ch]
                    val_series = df[ch].astype(float)
                    out_mask = (val_series < lower) | (val_series > upper)
                    clipped_count += int(out_mask.sum())
                    df[ch] = np.clip(val_series, lower, upper)
            if clipped_count > 0:
                transformations_applied.append(f"clipped_{clipped_count}_out_of_bound_values")

        # 6. Calculate Custom Derived Dynamic Metrics
        # Derived Metric 1: Gaze Stability
        # Definition: Omega_t = sqrt((d_gaze_x)^2 + (d_gaze_y)^2) / dt  (angular velocity in rad/s)
        #             gaze_stability_t = exp(-Omega_t / 1.0)
        #             When untracked (success == 0), gaze_stability is set to 0.0
        if "gaze_angle_x" in df.columns and "gaze_angle_y" in df.columns:
            gx = df["gaze_angle_x"].values.astype(float)
            gy = df["gaze_angle_y"].values.astype(float)
            d_gx = np.diff(gx, prepend=gx[0])
            d_gy = np.diff(gy, prepend=gy[0])
            ang_disp = np.sqrt(d_gx**2 + d_gy**2)
            ang_vel = ang_disp / dt
            gaze_stability = np.exp(-ang_vel / 1.0)  # Scaling constant omega_0 = 1.0 rad/s
            # Set untracked frames to 0.0 stability (distinguishable via is_valid_face)
            gaze_stability = np.where(is_tracked_mask, gaze_stability, 0.0)
            df["gaze_stability"] = np.clip(gaze_stability, 0.0, 1.0).astype(np.float32)
            transformations_applied.append("computed_derived_gaze_stability_exponential_decay")

        # Derived Metric 2: Rigid Motion (Head Pose Velocity)
        # Definition: V_rigid_t = sqrt((d_Rx)^2 + (d_Ry)^2 + (d_Rz)^2) / dt
        #             rigid_motion_t = tanh(V_rigid_t / 1.0) in [0.0, 1.0)
        if all(p in df.columns for p in OPENFACE_HEAD_POSE):
            rx = df["pose_Rx"].values.astype(float)
            ry = df["pose_Ry"].values.astype(float)
            rz = df["pose_Rz"].values.astype(float)
            d_rx = np.diff(rx, prepend=rx[0])
            d_ry = np.diff(ry, prepend=ry[0])
            d_rz = np.diff(rz, prepend=rz[0])
            pose_disp = np.sqrt(d_rx**2 + d_ry**2 + d_rz**2)
            pose_vel = pose_disp / dt
            rigid_motion = np.tanh(pose_vel / 1.0)  # Scaling constant v_0 = 1.0 rad/s
            rigid_motion = np.where(is_tracked_mask, rigid_motion, 0.0)
            df["rigid_motion"] = np.clip(rigid_motion, 0.0, 1.0).astype(np.float32)
            transformations_applied.append("computed_derived_rigid_motion_tanh_velocity")

        # Derived Metric 3: Non-Rigid Motion (Facial Expression Dynamics)
        # Definition: Mean absolute difference across available Action Units per second
        #             non_rigid_motion_t = tanh(mean_dAU / dt / 1.0) in [0.0, 1.0)
        available_aus = [au for au in OPENFACE_ACTION_UNITS if au in df.columns]
        if available_aus:
            au_matrix = df[available_aus].values.astype(float)  # (T, num_aus)
            d_au = np.diff(au_matrix, axis=0, prepend=au_matrix[:1])
            mean_d_au = np.mean(np.abs(d_au), axis=1)  # (T,)
            au_rate = mean_d_au / dt
            non_rigid_motion = np.tanh(au_rate / 1.0)
            non_rigid_motion = np.where(is_tracked_mask, non_rigid_motion, 0.0)
            df["non_rigid_motion"] = np.clip(non_rigid_motion, 0.0, 1.0).astype(np.float32)
            transformations_applied.append("computed_derived_non_rigid_motion_tanh_rate")

        # 7. Channel Selection and Reordering
        output_cols = OPENFACE_METADATA_COLS + ["is_valid_face"] + REAL_VIDEO_CHANNEL_NAMES
        available_output_cols = [c for c in output_cols if c in df.columns]
        cleaned_df = df[available_output_cols].copy()

        # Build diagnostic report
        report = CleaningTransformationReport(
            total_frames_input=total_frames,
            total_frames_output=len(cleaned_df),
            tracked_frames_count=tracked_count,
            untracked_frames_count=untracked_count,
            tracking_success_rate=round(tracking_rate, 4),
            mean_confidence=round(mean_conf, 4),
            out_of_bounds_clipped_count=clipped_count,
            nans_detected_in_raw=nans_count,
            infs_detected_in_raw=infs_count,
            derived_metrics_computed=["gaze_stability", "rigid_motion", "non_rigid_motion"],
            transformations_applied=transformations_applied,
        )

        return cleaned_df, report

