"""Configuration for synthetic video feature generation.

Defines channel definitions, engineering boundaries, sequence parameters, and paths
for generating abstract 24-channel temporal video feature tensors.

SCIENTIFIC INTEGRITY NOTICE:
This is an architectural integration benchmark. The Bangladeshi clinical cohort
contains ZERO video recordings, camera footage, or facial imagery. Synthetic video
feature trajectories are abstract numerical engineering fixtures (numpy arrays)
generated independently of clinical survey targets. They do NOT represent observed
facial behaviour and cannot validate real-world clinical diagnostic efficacy.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

# -----------------------------------------------------------------------------
# Base Paths
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRAIN_TEST_SPLIT_MANIFEST_PATH = (
    PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"
)

SYNTHETIC_VIDEO_DIR = PROJECT_ROOT / "data" / "synthetic" / "video"
SYNTHETIC_VIDEO_FEATURES_DIR = SYNTHETIC_VIDEO_DIR / "features"
SYNTHETIC_VIDEO_MANIFEST_PATH = SYNTHETIC_VIDEO_DIR / "video_manifest.csv"

# -----------------------------------------------------------------------------
# Provenance & Audit Tags
# -----------------------------------------------------------------------------
DATA_ORIGIN_TAG = "SYNTHETIC_ABSTRACT_VIDEO_FEATURES"
GENERATOR_VERSION = "1.0.0"
DEFAULT_RANDOM_SEED = 42

# -----------------------------------------------------------------------------
# Sequence Dynamics & Dimensions (Engineering Assumptions)
# -----------------------------------------------------------------------------
FEATURE_DIM: int = 24
MIN_SEQUENCE_LENGTH: int = 45
MAX_SEQUENCE_LENGTH: int = 120
AR1_ALPHA: float = 0.88

# Tracking dropout engineering parameters
MIN_DROPOUT_RATE: float = 0.03
MAX_DROPOUT_RATE: float = 0.10
CONFIDENCE_THRESHOLD: float = 0.60

# -----------------------------------------------------------------------------
# Channel Nomenclature & Provenance Classification
# -----------------------------------------------------------------------------
# Channels 0-13: OpenFace 2.0-style continuous Action Unit intensities [0.0, 5.0]
# Channels 14-16: OpenFace 2.0-style 3D head pose angles in radians [-pi/3, pi/3]
# Channels 17-18: OpenFace 2.0-style eye gaze angles in radians [-0.6, 0.6]
# Channel 19: Custom engineered gaze stability metric [0.0, 1.0]
# Channels 20-21: Custom engineered facial motion summaries [0.0, 1.0]
# Channels 22-23: Custom engineered tracking quality and status indicators [0.0, 1.0]

CHANNEL_NAMES: List[str] = [
    # OpenFace-style Facial Action Units (continuous intensities)
    "AU01_r",  # 0: Inner brow raiser
    "AU02_r",  # 1: Outer brow raiser
    "AU04_r",  # 2: Brow lowerer
    "AU05_r",  # 3: Upper lid raiser
    "AU06_r",  # 4: Cheek raiser
    "AU07_r",  # 5: Lid tightener
    "AU09_r",  # 6: Nose wrinkler
    "AU10_r",  # 7: Upper lip raiser
    "AU12_r",  # 8: Lip corner puller (zygomaticus)
    "AU14_r",  # 9: Dimpler
    "AU15_r",  # 10: Lip corner depressor
    "AU17_r",  # 11: Chin raiser
    "AU20_r",  # 12: Lip stretcher
    "AU25_r",  # 13: Lips part
    # OpenFace-style Head Pose (radians)
    "pose_pitch",  # 14: Head pitch angle (nodding)
    "pose_yaw",    # 15: Head yaw angle (turning)
    "pose_roll",   # 16: Head roll angle (tilting)
    # Gaze Features (OpenFace-style angles + custom stability)
    "gaze_angle_x",    # 17: Horizontal gaze angle (radians)
    "gaze_angle_y",    # 18: Vertical gaze angle (radians)
    "gaze_stability",  # 19: Custom gaze fixation stability
    # Custom Engineered Motion Summaries
    "rigid_motion",      # 20: Head movement velocity magnitude
    "non_rigid_motion",  # 21: Facial landmark deformation dispersion
    # Tracking Quality & Frame Status
    "tracking_confidence",  # 22: Frame-level face tracker confidence
    "success_flag",         # 23: Binary tracking success indicator (1.0 or 0.0)
]

# Strict physical / engineering interval boundaries per channel
CHANNEL_BOUNDS: Dict[str, Tuple[float, float]] = {
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
    # Head Pose: [-pi/3, pi/3] radians
    "pose_pitch": (-float(np.pi / 3.0), float(np.pi / 3.0)),
    "pose_yaw": (-float(np.pi / 3.0), float(np.pi / 3.0)),
    "pose_roll": (-float(np.pi / 3.0), float(np.pi / 3.0)),
    # Gaze: [-0.6, 0.6] radians and [0.0, 1.0] stability
    "gaze_angle_x": (-0.60, 0.60),
    "gaze_angle_y": (-0.60, 0.60),
    "gaze_stability": (0.0, 1.0),
    # Motion summaries: [0.0, 1.0]
    "rigid_motion": (0.0, 1.0),
    "non_rigid_motion": (0.0, 1.0),
    # Tracking quality: [0.0, 1.0] and {0.0, 1.0}
    "tracking_confidence": (0.0, 1.0),
    "success_flag": (0.0, 1.0),
}

