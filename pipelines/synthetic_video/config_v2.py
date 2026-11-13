"""Configuration for improved synthetic video feature generation (v2).

Defines updated channel definitions, covariance matrices, physiological co-activation
structures, derived metric formulations, and paths for generating abstract 24-channel
temporal video feature tensors with realistic facial and kinematic properties.

SCIENTIFIC INTEGRITY NOTICE:
This is an architectural integration benchmark and simulation fixture.
The Bangladeshi clinical cohort contains ZERO video recordings, camera footage,
or facial imagery. Synthetic video feature trajectories are abstract numerical
engineering fixtures (numpy arrays) generated independently of clinical survey targets.
Simulated Action Unit co-activations represent physiological facial mechanics
(e.g., zygomaticus-orbicularis coupling in smiles) but do NOT represent clinically
validated depression biomarkers or diagnostic signatures.
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

# Output directory for version 2 artifacts (strictly separated from v1)
SYNTHETIC_VIDEO_V2_DIR = PROJECT_ROOT / "data" / "synthetic" / "video_v2"
SYNTHETIC_VIDEO_V2_FEATURES_DIR = SYNTHETIC_VIDEO_V2_DIR / "features"
SYNTHETIC_VIDEO_V2_MANIFEST_PATH = SYNTHETIC_VIDEO_V2_DIR / "video_manifest.csv"

# -----------------------------------------------------------------------------
# Provenance & Audit Tags
# -----------------------------------------------------------------------------
DATA_ORIGIN_TAG = "SYNTHETIC_ABSTRACT_VIDEO_FEATURES_V2"
GENERATOR_VERSION = "2.0.0"
DEFAULT_RANDOM_SEED = 42

# -----------------------------------------------------------------------------
# Sequence Dynamics & Dimensions (Engineering Assumptions)
# -----------------------------------------------------------------------------
FEATURE_DIM: int = 24
MIN_SEQUENCE_LENGTH: int = 45
MAX_SEQUENCE_LENGTH: int = 120
AR1_ALPHA: float = 0.88
FPS: float = 30.0
FRAME_INTERVAL_SEC: float = 1.0 / FPS  # 0.03333 seconds

# Tracking dropout engineering parameters
MIN_DROPOUT_RATE: float = 0.03
MAX_DROPOUT_RATE: float = 0.10
CONFIDENCE_THRESHOLD: float = 0.60

# -----------------------------------------------------------------------------
# Channel Nomenclature & Provenance Classification
# -----------------------------------------------------------------------------
# Exact 24-channel schema preserved for multimodal backward compatibility:
# Channels 0-13: OpenFace 2.0-style continuous Action Unit intensities [0.0, 5.0]
# Channels 14-16: OpenFace 2.0-style 3D head pose angles in radians [-pi/3, pi/3]
# Channels 17-18: OpenFace 2.0-style eye gaze angles in radians [-0.60, 0.60]
# Channel 19: Mathematically derived gaze stability metric [0.0, 1.0]
# Channels 20-21: Mathematically derived facial and head motion summaries [0.0, 1.0]
# Channels 22-23: Tracking quality and frame status indicators [0.0, 1.0]

CHANNEL_NAMES: List[str] = [
    # OpenFace-style Facial Action Units (continuous intensities)
    "AU01_r",  # 0: Inner brow raiser (frontalis, pars medialis)
    "AU02_r",  # 1: Outer brow raiser (frontalis, pars lateralis)
    "AU04_r",  # 2: Brow lowerer (corrugator supercilii, depressor supercilii)
    "AU05_r",  # 3: Upper lid raiser (levator palpebrae superioris)
    "AU06_r",  # 4: Cheek raiser (orbicularis oculi, pars orbitalis)
    "AU07_r",  # 5: Lid tightener (orbicularis oculi, pars palpebralis)
    "AU09_r",  # 6: Nose wrinkler (levator labii superioris alaeque nasi)
    "AU10_r",  # 7: Upper lip raiser (levator labii superioris)
    "AU12_r",  # 8: Lip corner puller (zygomaticus major)
    "AU14_r",  # 9: Dimpler (buccinator)
    "AU15_r",  # 10: Lip corner depressor (depressor anguli oris)
    "AU17_r",  # 11: Chin raiser (mentalis)
    "AU20_r",  # 12: Lip stretcher (risorius)
    "AU25_r",  # 13: Lips part (depressor labii inferioris or orbicularis oris relaxation)
    # OpenFace-style Head Pose (radians)
    "pose_pitch",  # 14: Head pitch angle (nodding up/down)
    "pose_yaw",    # 15: Head yaw angle (turning left/right)
    "pose_roll",   # 16: Head roll angle (tilting sideways)
    # Gaze Features (OpenFace-style angles + derived stability)
    "gaze_angle_x",    # 17: Horizontal gaze angle (radians)
    "gaze_angle_y",    # 18: Vertical gaze angle (radians)
    "gaze_stability",  # 19: Mathematically derived gaze fixation stability
    # Mathematically Derived Motion Summaries
    "rigid_motion",      # 20: Head rotational velocity magnitude
    "non_rigid_motion",  # 21: Facial Action Unit deformation velocity
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
    # Gaze: [-0.60, 0.60] radians and [0.0, 1.0] stability
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

# -----------------------------------------------------------------------------
# Differentiated Baseline Means and Standard Deviations (14 AUs)
# -----------------------------------------------------------------------------
# Reflecting real human facial resting muscle baseline distributions:
# Low resting baseline for rarely activated muscles (AU05, AU09, AU20)
# Moderate baseline for conversational/expressive muscles (AU01, AU04, AU06, AU12, AU25)
AU_MEANS: np.ndarray = np.array([
    0.22,  # AU01_r: Inner brow raiser
    0.18,  # AU02_r: Outer brow raiser
    0.28,  # AU04_r: Brow lowerer
    0.12,  # AU05_r: Upper lid raiser
    0.32,  # AU06_r: Cheek raiser
    0.25,  # AU07_r: Lid tightener
    0.15,  # AU09_r: Nose wrinkler
    0.20,  # AU10_r: Upper lip raiser
    0.38,  # AU12_r: Lip corner puller
    0.22,  # AU14_r: Dimpler
    0.18,  # AU15_r: Lip corner depressor
    0.20,  # AU17_r: Chin raiser
    0.15,  # AU20_r: Lip stretcher
    0.45,  # AU25_r: Lips part
], dtype=np.float32)

AU_STDS: np.ndarray = np.array([
    0.25,  # AU01_r
    0.22,  # AU02_r
    0.28,  # AU04_r
    0.15,  # AU05_r
    0.32,  # AU06_r
    0.26,  # AU07_r
    0.18,  # AU09_r
    0.22,  # AU10_r
    0.38,  # AU12_r
    0.24,  # AU14_r
    0.20,  # AU15_r
    0.22,  # AU17_r
    0.18,  # AU20_r
    0.40,  # AU25_r
], dtype=np.float32)

# Inter-participant baseline resting variation standard deviation (anatomical offset)
AU_PARTICIPANT_STD: np.ndarray = np.array([
    0.08, 0.07, 0.09, 0.05, 0.10, 0.08, 0.06, 0.07, 0.12, 0.08, 0.07, 0.07, 0.06, 0.12
], dtype=np.float32)

# -----------------------------------------------------------------------------
# Action Unit Co-activation Correlation Structure (14x14)
# -----------------------------------------------------------------------------
def get_au_correlation_matrix() -> np.ndarray:
    """Build a physiologically motivated 14x14 Action Unit correlation matrix.

    Incorporates established Facial Action Coding System (FACS) co-activations:
    - AU01 + AU02: Eyebrow elevation synergy (frontalis muscle branches)
    - AU06 + AU12: Duchenne smile synergy (orbicularis oculi + zygomaticus major)
    - AU12 + AU25: Parted-lip smile synergy
    - AU06 + AU25: Shared smiling dynamics
    - AU04 + AU07: Brow furrow / concentration cluster
    - AU04 + AU15: Negative valence / grief cluster
    - AU15 + AU17: Lower facial sadness / chin raising cluster
    - AU09 + AU10: Disgust / nasolabial elevation cluster
    - AU14 + AU12: Grin / dimpling synergy
    - AU20 + AU25: Horizontal lip stretch with mouth open
    """
    R = np.eye(14, dtype=np.float32)

    # Eyebrow cluster
    R[0, 1] = R[1, 0] = 0.65  # AU01 - AU02

    # Positive valence / smiling cluster
    R[4, 8] = R[8, 4] = 0.62  # AU06 - AU12
    R[8, 13] = R[13, 8] = 0.48  # AU12 - AU25
    R[4, 13] = R[13, 4] = 0.38  # AU06 - AU25
    R[8, 9] = R[9, 8] = 0.30  # AU12 - AU14

    # Brow furrow / concentration cluster
    R[2, 5] = R[5, 2] = 0.52  # AU04 - AU07

    # Distress / lower face tension cluster
    R[2, 10] = R[10, 2] = 0.42  # AU04 - AU15
    R[10, 11] = R[11, 10] = 0.45  # AU15 - AU17

    # Nasolabial / midface elevation cluster
    R[6, 7] = R[7, 6] = 0.55  # AU09 - AU10

    # Lip stretch / mouth opening
    R[12, 13] = R[13, 12] = 0.38  # AU20 - AU25

    # Small resting baseline correlation across facial expressions
    for i in range(14):
        for j in range(i + 1, 14):
            if R[i, j] == 0.0:
                R[i, j] = R[j, i] = 0.05

    # Ensure positive semi-definiteness via eigenvalue thresholding
    eigenvals, eigenvecs = np.linalg.eigh(R)
    eigenvals = np.maximum(eigenvals, 1e-4)
    R_psd = (eigenvecs @ np.diag(eigenvals) @ eigenvecs.T).astype(np.float32)

    # Normalize diagonals to exactly 1.0
    diag_inv_sqrt = np.diag(1.0 / np.sqrt(np.diag(R_psd)))
    R_norm = (diag_inv_sqrt @ R_psd @ diag_inv_sqrt).astype(np.float32)

    return R_norm


# -----------------------------------------------------------------------------
# Head Pose & Gaze Kinematic Parameters
# -----------------------------------------------------------------------------
POSE_MEANS: np.ndarray = np.array([0.04, 0.00, 0.00], dtype=np.float32)  # Pitch slight downward, yaw/roll 0
POSE_STDS: np.ndarray = np.array([0.10, 0.12, 0.07], dtype=np.float32)   # Radian fluctuations
POSE_PARTICIPANT_STD: np.ndarray = np.array([0.05, 0.06, 0.03], dtype=np.float32)

GAZE_MEANS: np.ndarray = np.array([0.00, 0.03], dtype=np.float32)  # Slight downward gaze
GAZE_STDS: np.ndarray = np.array([0.09, 0.07], dtype=np.float32)
GAZE_PARTICIPANT_STD: np.ndarray = np.array([0.04, 0.03], dtype=np.float32)

# Coupling between yaw and roll (natural cervical kinematic coupling)
POSE_CORR_YAW_ROLL: float = -0.22

# -----------------------------------------------------------------------------
# Mathematical Derived Metric Scaling Constants
# -----------------------------------------------------------------------------
# Gaze stability: exp(-omega / omega_0), where omega_0 = 3.0 rad/s
GAZE_STABILITY_OMEGA_0: float = 3.0  # rad/s

# Rigid motion: tanh(v_head / v_0), where v_0 = 4.0 rad/s
RIGID_MOTION_V_0: float = 4.0  # rad/s

# Non-rigid motion: tanh(mean_au_velocity / alpha_0), where alpha_0 = 4.0 intensity units/s
NON_RIGID_MOTION_ALPHA_0: float = 4.0  # units/s
