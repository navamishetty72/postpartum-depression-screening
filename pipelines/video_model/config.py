"""Configuration parameters for the video modeling pipeline.

Defines directory paths, tensor schemas, channel indices, and preprocessing contracts
for training video models on synthetic (and real) video feature sequences.

SCIENTIFIC INTEGRITY NOTICE:
Synthetic Video V2 features are abstract numerical simulations generated as engineering fixtures
for multimodal architecture verification. They do NOT represent authentic maternal facial recordings
or clinically validated psychiatric biomarkers.
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple
import numpy as np

# -----------------------------------------------------------------------------
# Base Directories and Manifest Paths
# -----------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

# Primary Video Modality (Synthetic Video V2)
V2_VIDEO_DIR: Path = PROJECT_ROOT / "data" / "synthetic" / "video_v2"
V2_FEATURE_DIR: Path = V2_VIDEO_DIR / "features"
V2_MANIFEST_PATH: Path = V2_VIDEO_DIR / "video_manifest.csv"

# Legacy Synthetic Video V1 (Preserved for comparison)
V1_VIDEO_DIR: Path = PROJECT_ROOT / "data" / "synthetic" / "video"
V1_FEATURE_DIR: Path = V1_VIDEO_DIR / "features"
V1_MANIFEST_PATH: Path = V1_VIDEO_DIR / "video_manifest.csv"

# Frozen Split Manifest (Canonical Ground Truth & Partition Assignment)
SPLIT_MANIFEST_PATH: Path = (
    PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"
)

# Output directory for video model artifacts
MODEL_ARTIFACTS_DIR: Path = PROJECT_ROOT / "models" / "video_model"
BASELINE_ARTIFACTS_DIR: Path = PROJECT_ROOT / "artifacts" / "video_model" / "baselines"
RECURRENT_ARTIFACTS_DIR: Path = PROJECT_ROOT / "artifacts" / "video_model" / "recurrent"
EMBEDDINGS_ARTIFACTS_DIR: Path = PROJECT_ROOT / "artifacts" / "video_model" / "embeddings"
UNIFIED_EMBEDDINGS_ARTIFACTS_DIR: Path = (
    PROJECT_ROOT / "artifacts" / "video_model" / "embeddings_unified"
)

# -----------------------------------------------------------------------------
# Tensor & Feature Specifications
# -----------------------------------------------------------------------------
FEATURE_DIM: int = 24
MIN_SEQUENCE_LENGTH: int = 45
MAX_SEQUENCE_LENGTH: int = 120
EXPECTED_DTYPE: np.dtype = np.dtype("float32")

# Tracking quality threshold
CONFIDENCE_THRESHOLD: float = 0.60

# -----------------------------------------------------------------------------
# Channel Nomenclature & Groups
# -----------------------------------------------------------------------------
# Channels 0-13: Facial Action Unit continuous intensities [0.0, 5.0]
# Channels 14-16: 3D Head Pose angles in radians [-pi/3, pi/3]
# Channels 17-18: Eye Gaze angles in radians [-0.60, 0.60]
# Channel 19: Analytically derived Gaze Stability [0.0, 1.0]
# Channels 20-21: Analytically derived Rigid & Non-Rigid Motion [0.0, 1.0]
# Channels 22-23: Tracking Confidence [0.0, 1.0] and Success Flag {0.0, 1.0}

CHANNEL_NAMES: List[str] = [
    "AU01_r", "AU02_r", "AU04_r", "AU05_r", "AU06_r", "AU07_r", "AU09_r",
    "AU10_r", "AU12_r", "AU14_r", "AU15_r", "AU17_r", "AU20_r", "AU25_r",
    "pose_pitch", "pose_yaw", "pose_roll",
    "gaze_angle_x", "gaze_angle_y",
    "gaze_stability",
    "rigid_motion", "non_rigid_motion",
    "tracking_confidence",
    "success_flag",
]

# Physical and engineering interval boundaries
CHANNEL_BOUNDS: Dict[str, Tuple[float, float]] = {
    "AU01_r": (0.0, 5.0), "AU02_r": (0.0, 5.0), "AU04_r": (0.0, 5.0), "AU05_r": (0.0, 5.0),
    "AU06_r": (0.0, 5.0), "AU07_r": (0.0, 5.0), "AU09_r": (0.0, 5.0), "AU10_r": (0.0, 5.0),
    "AU12_r": (0.0, 5.0), "AU14_r": (0.0, 5.0), "AU15_r": (0.0, 5.0), "AU17_r": (0.0, 5.0),
    "AU20_r": (0.0, 5.0), "AU25_r": (0.0, 5.0),
    "pose_pitch": (-float(np.pi / 3.0), float(np.pi / 3.0)),
    "pose_yaw": (-float(np.pi / 3.0), float(np.pi / 3.0)),
    "pose_roll": (-float(np.pi / 3.0), float(np.pi / 3.0)),
    "gaze_angle_x": (-0.60, 0.60), "gaze_angle_y": (-0.60, 0.60),
    "gaze_stability": (0.0, 1.0),
    "rigid_motion": (0.0, 1.0), "non_rigid_motion": (0.0, 1.0),
    "tracking_confidence": (0.0, 1.0),
    "success_flag": (0.0, 1.0),
}

# Channel subsets for normalization and masking
AU_CHANNEL_INDICES: List[int] = list(range(0, 14))
POSE_CHANNEL_INDICES: List[int] = [14, 15, 16]
GAZE_CHANNEL_INDICES: List[int] = [17, 18]
MOTION_CHANNEL_INDICES: List[int] = [19, 20, 21]
CONTINUOUS_FEATURE_INDICES: List[int] = list(range(0, 22))  # Channels to normalize
TRACKING_FEATURE_INDICES: List[int] = [22, 23]             # Kept unnormalized [0, 1]

# -----------------------------------------------------------------------------
# Manifest & Partition Contracts
# -----------------------------------------------------------------------------
PARTICIPANT_ID_COLUMN: str = "participant_id"
SPLIT_COLUMN: str = "split_partition"
TARGET_COLUMN: str = "target_canonical_epds_ge_13"

EXPECTED_TOTAL_PARTICIPANTS: int = 800
EXPECTED_TRAIN_PARTICIPANTS: int = 640
EXPECTED_TEST_PARTICIPANTS: int = 160

VALID_SPLIT_PARTITIONS: Set[str] = {"train", "test", "all"}
DEFAULT_RANDOM_SEED: int = 42
CV_FOLDS: int = 5

