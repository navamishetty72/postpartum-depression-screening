"""Tensor assembly, participant-level aggregation, and quality report generation.

Constructs consistent (T, 24) float32 temporal tensors with documented channel schemas,
aggregates participant-level facial summary metrics over valid tracked frames,
and writes comprehensive quality-control reports.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from .config import (
    DATA_ORIGIN_REAL_VIDEO,
    FEATURE_BOUNDS,
    FEATURE_DIM,
    MIN_TRACKING_SUCCESS_RATE,
    OPENFACE_ACTION_UNITS,
    OPENFACE_GAZE,
    OPENFACE_HEAD_POSE,
    PIPELINE_VERSION,
    REAL_VIDEO_CHANNEL_NAMES,
)


class TensorBuilder:
    """Assembles (T, 24) temporal feature tensors and participant-level summaries."""

    def __init__(self, channel_names: Optional[List[str]] = None) -> None:
        self.channel_names = channel_names or REAL_VIDEO_CHANNEL_NAMES
        assert len(self.channel_names) == FEATURE_DIM, (
            f"Expected {FEATURE_DIM} channels, got {len(self.channel_names)}"
        )

    def build_temporal_tensor(
        self,
        cleaned_df: pd.DataFrame,
    ) -> np.ndarray:
        """Assemble a (T, 24) float32 temporal feature tensor.

        Untracked Frame Policy:
        - When tracking fails (success == 0), the face is occluded or not detected.
        - To prevent artificial zero-valued facial muscle artifacts while providing
          a contiguous numerical tensor for recurrent/pooling layers, continuous
          channels (0-21) are forward-filled from the last valid tracked state.
        - Channels 22 (confidence) and 23 (success = 0.0) preserve the exact tracking
          loss status, allowing downstream attention or mask layers to discount untracked frames.

        Args:
            cleaned_df: Preprocessed frame-level DataFrame.

        Returns:
            np.ndarray: (T, 24) float32 NumPy tensor.
        """
        t_len = len(cleaned_df)
        if t_len == 0:
            raise ValueError("Cannot build tensor from empty cleaned DataFrame.")

        # Extract channels in exact documented order
        tensor_df = pd.DataFrame(index=cleaned_df.index)

        is_tracked = cleaned_df["is_valid_face"].values if "is_valid_face" in cleaned_df.columns else (cleaned_df["success"] == 1).values

        for ch in self.channel_names:
            if ch in cleaned_df.columns:
                tensor_df[ch] = cleaned_df[ch].astype(np.float32)
            else:
                # Missing channel: initialize with lower bound or 0.0
                tensor_df[ch] = np.float32(FEATURE_BOUNDS.get(ch, (0.0, 1.0))[0])

        # Forward-fill continuous channels (0 to 21) across untracked gaps
        # Channels 22 ('confidence') and 23 ('success') retain their exact values!
        continuous_channels = self.channel_names[:22]
        for ch in continuous_channels:
            series = tensor_df[ch].copy()
            # Where not tracked, set to NaN temporarily to forward-fill
            series[~is_tracked] = np.nan
            series = series.ffill().bfill().fillna(0.0)
            tensor_df[ch] = series.astype(np.float32)

        tensor = tensor_df[self.channel_names].values.astype(np.float32)

        if np.isnan(tensor).any() or np.isinf(tensor).any():
            raise ValueError("Tensor contains NaN or Inf values after assembly.")

        return tensor

    def compute_participant_summary(
        self,
        cleaned_df: pd.DataFrame,
        participant_id: str,
        recording_id: str,
    ) -> Dict[str, Any]:
        """Compute aggregated summary statistics over valid tracked frames only.

        Args:
            cleaned_df: Cleaned frame-level DataFrame.
            participant_id: Unique participant identifier.
            recording_id: Recording identifier.

        Returns:
            Dict[str, Any]: Summary dictionary with AU, pose, and gaze statistics.
        """
        total_frames = len(cleaned_df)
        is_tracked = (
            cleaned_df["is_valid_face"].values
            if "is_valid_face" in cleaned_df.columns
            else (cleaned_df["success"] == 1).values
        )
        tracked_frames = int(is_tracked.sum())
        tracking_rate = float(tracked_frames / total_frames) if total_frames > 0 else 0.0
        mean_conf = float(cleaned_df["confidence"].mean()) if "confidence" in cleaned_df.columns else 0.0

        summary: Dict[str, Any] = {
            "participant_id": participant_id,
            "recording_id": recording_id,
            "data_origin": DATA_ORIGIN_REAL_VIDEO,
            "pipeline_version": PIPELINE_VERSION,
            "total_frames": total_frames,
            "tracked_frames": tracked_frames,
            "tracking_success_rate": round(tracking_rate, 4),
            "mean_tracking_confidence": round(mean_conf, 4),
            "action_units": {},
            "head_pose": {},
            "gaze": {},
            "dynamics": {},
        }

        # If zero tracked frames, return null statistics
        if tracked_frames == 0:
            summary["warning"] = "No valid tracked faces detected in recording."
            return summary

        tracked_df = cleaned_df[is_tracked]

        # Action Units summary (mean, std, 90th percentile)
        for au in OPENFACE_ACTION_UNITS:
            if au in tracked_df.columns:
                vals = tracked_df[au].values.astype(float)
                summary["action_units"][au] = {
                    "mean_intensity": round(float(np.mean(vals)), 4),
                    "std_intensity": round(float(np.std(vals)), 4),
                    "p90_intensity": round(float(np.percentile(vals, 90)), 4),
                }

        # Head Pose summary
        for pose_ch in OPENFACE_HEAD_POSE:
            if pose_ch in tracked_df.columns:
                vals = tracked_df[pose_ch].values.astype(float)
                summary["head_pose"][pose_ch] = {
                    "mean_rad": round(float(np.mean(vals)), 4),
                    "std_rad": round(float(np.std(vals)), 4),
                    "range_rad": round(float(np.ptp(vals)), 4),
                }

        # Gaze summary
        for gaze_ch in OPENFACE_GAZE:
            if gaze_ch in tracked_df.columns:
                vals = tracked_df[gaze_ch].values.astype(float)
                summary["gaze"][gaze_ch] = {
                    "mean_rad": round(float(np.mean(vals)), 4),
                    "std_rad": round(float(np.std(vals)), 4),
                }

        # Derived dynamic summaries
        for dyn_ch in ("gaze_stability", "rigid_motion", "non_rigid_motion"):
            if dyn_ch in tracked_df.columns:
                vals = tracked_df[dyn_ch].values.astype(float)
                summary["dynamics"][dyn_ch] = {
                    "mean": round(float(np.mean(vals)), 4),
                    "std": round(float(np.std(vals)), 4),
                }

        return summary

    def build_quality_report(
        self,
        participant_id: str,
        recording_id: str,
        video_inspection: Dict[str, Any],
        cleaning_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate comprehensive quality-control (QC) report for a processed recording.

        Args:
            participant_id: Unique participant identifier.
            recording_id: Recording identifier.
            video_inspection: Dict from VideoInspectionReport.
            cleaning_report: Dict from CleaningTransformationReport.

        Returns:
            Dict[str, Any]: Complete QC report with status PASS, WARNING, or FAIL.
        """
        tracking_rate = cleaning_report.get("tracking_success_rate", 0.0)
        corrupted_pct = video_inspection.get("corrupted_frame_percentage", 0.0)

        # QC Status Logic
        if tracking_rate < MIN_TRACKING_SUCCESS_RATE:
            qc_status = "FAIL"
            qc_reason = f"Tracking success rate ({tracking_rate:.1%}) below threshold ({MIN_TRACKING_SUCCESS_RATE:.1%})."
        elif corrupted_pct > 10.0:
            qc_status = "FAIL"
            qc_reason = f"Corrupted frames percentage ({corrupted_pct:.1f}%) exceeds 10% tolerance."
        elif tracking_rate < 0.60 or corrupted_pct > 0.0:
            qc_status = "WARNING"
            qc_reason = f"Suboptimal tracking ({tracking_rate:.1%}) or corrupted frames ({corrupted_pct:.1f}%)."
        else:
            qc_status = "PASS"
            qc_reason = "Video fully readable and tracking success rate is optimal."

        return {
            "participant_id": participant_id,
            "recording_id": recording_id,
            "qc_status": qc_status,
            "qc_reason": qc_reason,
            "video_inspection": video_inspection,
            "cleaning_summary": cleaning_report,
            "provenance": {
                "data_origin": DATA_ORIGIN_REAL_VIDEO,
                "pipeline_version": PIPELINE_VERSION,
            },
        }

