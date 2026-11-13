"""Configuration parameters for real video feature extraction.

Defines directories, OpenFace 2.x feature schemas, physical units,
channel ordering, and quality-control thresholds for real video processing.

SCIENTIFIC INTEGRITY NOTICE:
This module processes authentic video recordings. Extracted Action Units,
head pose rotations, and eye gaze vectors represent objective physical
and computational measurements from OpenFace 2.x and OpenCV.
They are NOT clinical diagnoses or verified PPD biomarkers.
Zero EPDS/PHQ survey targets or items are permitted to enter this pipeline.
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple
import numpy as np

# -----------------------------------------------------------------------------
# Base Directories and Paths
# -----------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

DEFAULT_RAW_VIDEO_DIR: Path = PROJECT_ROOT / "data" / "raw" / "video"
PROCESSED_VIDEO_DIR: Path = PROJECT_ROOT / "data" / "processed" / "video"

RAW_OPENFACE_DIR: Path = PROCESSED_VIDEO_DIR / "raw_openface"
CLEANED_DIR: Path = PROCESSED_VIDEO_DIR / "cleaned"
FEATURES_DIR: Path = PROCESSED_VIDEO_DIR / "features"
SUMMARIES_DIR: Path = PROCESSED_VIDEO_DIR / "summaries"
QUALITY_REPORTS_DIR: Path = PROCESSED_VIDEO_DIR / "quality_reports"
VIDEO_MANIFEST_PATH: Path = PROCESSED_VIDEO_DIR / "video_manifest.csv"

# -----------------------------------------------------------------------------
# Supported Codecs and Extensions
# -----------------------------------------------------------------------------
SUPPORTED_VIDEO_EXTENSIONS: Set[str] = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
    ".m4v",
}

# -----------------------------------------------------------------------------
# Provenance & Audit Metadata
# -----------------------------------------------------------------------------
DATA_ORIGIN_REAL_VIDEO: str = "REAL_VIDEO_OPENFACE"
PIPELINE_VERSION: str = "1.0.0"
OPENFACE_MIN_VERSION: str = "2.2.0"

# -----------------------------------------------------------------------------
# Quality Control & Tracking Thresholds
# -----------------------------------------------------------------------------
MIN_CONFIDENCE_TRACKED: float = 0.60
MIN_TRACKING_SUCCESS_RATE: float = 0.20
MAX_MISSING_FRAME_PERCENT: float = 0.15

# -----------------------------------------------------------------------------
# OpenFace 2.x Direct Feature Definitions
# -----------------------------------------------------------------------------
# 14 continuous Facial Action Unit intensities in [0.0, 5.0]
OPENFACE_ACTION_UNITS: List[str] = [
    "AU01_r",  # Inner brow raiser
    "AU02_r",  # Outer brow raiser
    "AU04_r",  # Brow lowerer
    "AU05_r",  # Upper lid raiser
    "AU06_r",  # Cheek raiser
    "AU07_r",  # Lid tightener
    "AU09_r",  # Nose wrinkler
    "AU10_r",  # Upper lip raiser
    "AU12_r",  # Lip corner puller
    "AU14_r",  # Dimpler
    "AU15_r",  # Lip corner depressor
    "AU17_r",  # Chin raiser
    "AU20_r",  # Lip stretcher
    "AU25_r",  # Lips part
]

# 3D Head Pose rotation angles in radians around X, Y, Z axes
OPENFACE_HEAD_POSE: List[str] = [
    "pose_Rx",  # Pitch rotation in radians
    "pose_Ry",  # Yaw rotation in radians
    "pose_Rz",  # Roll rotation in radians
]

# 2D Eye Gaze angles in radians
OPENFACE_GAZE: List[str] = [
    "gaze_angle_x",  # Horizontal eye gaze direction in radians
    "gaze_angle_y",  # Vertical eye gaze direction in radians
]

# Tracking quality indicators
OPENFACE_TRACKING: List[str] = [
    "confidence",  # Landmark tracking confidence in [0.0, 1.0]
    "success",     # Binary face detection and tracking flag {0, 1}
]

# Frame timing and index columns
OPENFACE_METADATA_COLS: List[str] = [
    "frame",       # 1-based frame sequence number
    "timestamp",   # Frame presentation timestamp in seconds
]

# -----------------------------------------------------------------------------
# Custom Derived Dynamic Metrics
# -----------------------------------------------------------------------------
# These metrics are mathematically derived from OpenFace outputs during cleaning.
# They are explicitly labeled as DERIVED and are NOT direct OpenFace columns.
DERIVED_METRIC_NAMES: List[str] = [
    "gaze_stability",   # Derived gaze fixation stability in [0.0, 1.0]
    "rigid_motion",     # Derived head rotational velocity summary in [0.0, 1.0]
    "non_rigid_motion", # Derived facial AU expression dynamic rate in [0.0, 1.0]
]

# -----------------------------------------------------------------------------
# Unified 24-Channel Feature Tensor Ordering
# -----------------------------------------------------------------------------
# Follows consistent channel indexing compatible with multimodal fusion layers:
# Channels  0-13: OpenFace Action Units (14 continuous intensities)
# Channels 14-16: OpenFace Head Pose (3 continuous rotation angles)
# Channels 17-18: OpenFace Eye Gaze (2 continuous gaze angles)
# Channel     19: Derived Gaze Stability (1 continuous scalar)
# Channels 20-21: Derived Motion Summaries (2 continuous scalars)
# Channels 22-23: Tracking Status (confidence in [0.0, 1.0], success in {0.0, 1.0})
FEATURE_DIM: int = 24

REAL_VIDEO_CHANNEL_NAMES: List[str] = (
    OPENFACE_ACTION_UNITS           # 0..13
    + OPENFACE_HEAD_POSE            # 14..16
    + OPENFACE_GAZE                 # 17..18
    + ["gaze_stability"]            # 19
    + ["rigid_motion", "non_rigid_motion"]  # 20..21
    + OPENFACE_TRACKING             # 22..23 ("confidence", "success")
)

# -----------------------------------------------------------------------------
# Feature Bounds and Physical Validity Ranges
# -----------------------------------------------------------------------------
FEATURE_BOUNDS: Dict[str, Tuple[float, float]] = {
    # Action Units: [0.0, 5.0]
    "AU01_r": (0.0, 5.0),
    "AU02_r": (0.0, 5.0),
    "AU04_r": (0.0, 5.0),
    "AU05_r": (0.0, 5.0),
    "AU06_r": (0.0, 5.0),
    "AU07_r": (0.0, 5.0),
    "AU09_r": (0.0, 5.0),
    "AU10_r": (0.0, 5.0),
    "AU12_r": (0.0, 5.0),
    "AU14_r": (0.0, 5.0),
    "AU15_r": (0.0, 5.0),
    "AU17_r": (0.0, 5.0),
    "AU20_r": (0.0, 5.0),
    "AU25_r": (0.0, 5.0),
    # Head Pose: [-pi, pi] radians
    "pose_Rx": (-float(np.pi), float(np.pi)),
    "pose_Ry": (-float(np.pi), float(np.pi)),
    "pose_Rz": (-float(np.pi), float(np.pi)),
    # Gaze: [-pi/2, pi/2] radians
    "gaze_angle_x": (-float(np.pi / 2.0), float(np.pi / 2.0)),
    "gaze_angle_y": (-float(np.pi / 2.0), float(np.pi / 2.0)),
    # Derived Metrics: [0.0, 1.0]
    "gaze_stability": (0.0, 1.0),
    "rigid_motion": (0.0, 1.0),
    "non_rigid_motion": (0.0, 1.0),
    # Tracking Quality: [0.0, 1.0]
    "confidence": (0.0, 1.0),
    "success": (0.0, 1.0),
}

# -----------------------------------------------------------------------------
# Target Leakage Safeguards
# -----------------------------------------------------------------------------
EXCLUDED_TARGET_KEYWORDS: List[str] = [
    "epds",
    "phq",
    "target",
    "depression",
    "screening_threshold",
    "score",
]

