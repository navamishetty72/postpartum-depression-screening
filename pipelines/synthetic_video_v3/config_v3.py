"""Configuration for isolated experimental Video V3 simulation.

Defines channel definitions, base paths, clinical conditioning weights,
covariance structures, and metadata tags for generating participant-aligned
synthetic video feature tensors conditioned on non-target clinical covariates.

SCIENTIFIC INTEGRITY NOTICE:
This is an experimental synthetic simulation fixture for the Moment AI hackathon.
The Bangladeshi clinical cohort contains ZERO video recordings or facial imagery.
Synthetic video features are abstract numerical simulations conditioned on non-target
clinical survey variables. They do NOT represent genuine optical observations of
maternal facial kinematics and cannot establish real-world clinical diagnostic accuracy.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

# -----------------------------------------------------------------------------
# Base Paths
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELING_MATRIX_PATH = PROJECT_ROOT / "data" / "processed" / "Numerical" / "ppd_modeling_matrix.csv"
TRAIN_TEST_SPLIT_MANIFEST_PATH = (
    PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"
)

# Output directory for Video V3 artifacts (strictly isolated from V1 and V2)
SYNTHETIC_VIDEO_V3_DIR = PROJECT_ROOT / "data" / "synthetic" / "video_v3"
SYNTHETIC_VIDEO_V3_FEATURES_DIR = SYNTHETIC_VIDEO_V3_DIR / "features"
SYNTHETIC_VIDEO_V3_MANIFEST_PATH = SYNTHETIC_VIDEO_V3_DIR / "video_manifest.csv"

# Experiments output directory
VIDEO_V3_EXPERIMENTS_DIR = PROJECT_ROOT / "artifacts" / "video_experiments" / "video_v3"

# -----------------------------------------------------------------------------
# Provenance & Audit Tags
# -----------------------------------------------------------------------------
DATA_ORIGIN_TAG = "CLINICALLY_CONDITIONED_SYNTHETIC"
GENERATOR_VERSION = "3.0.0"
DEFAULT_RANDOM_SEED = 42

# -----------------------------------------------------------------------------
# Sequence Dynamics & Dimensions
# -----------------------------------------------------------------------------
FEATURE_DIM: int = 24
MIN_SEQUENCE_LENGTH: int = 45
MAX_SEQUENCE_LENGTH: int = 120
AR1_ALPHA: float = 0.88
FPS: float = 30.0
FRAME_INTERVAL_SEC: float = 1.0 / FPS

# Tracking dropout engineering parameters
MIN_DROPOUT_RATE: float = 0.03
MAX_DROPOUT_RATE: float = 0.10
CONFIDENCE_THRESHOLD: float = 0.60

# -----------------------------------------------------------------------------
# Channel Nomenclature (Preserves exact 24-channel schema)
# -----------------------------------------------------------------------------
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
    "pose_pitch",  # 14: Head pitch angle (nodding up/down; negative = down)
    "pose_yaw",    # 15: Head yaw angle (turning left/right)
    "pose_roll",   # 16: Head roll angle (tilting sideways)
    # Gaze Features (OpenFace-style angles + derived stability)
    "gaze_angle_x",    # 17: Horizontal gaze angle (radians)
    "gaze_angle_y",    # 18: Vertical gaze angle (radians; negative = down)
    "gaze_stability",  # 19: Mathematically derived gaze fixation stability [0, 1]
    # Mathematically Derived Motion Summaries
    "rigid_motion",      # 20: Head rotational velocity magnitude [0, 1]
    "non_rigid_motion",  # 21: Facial Action Unit deformation velocity [0, 1]
    # Tracking Quality & Frame Status (Strictly unconditioned to prevent leakage)
    "tracking_confidence",  # 22: Frame-level face tracker confidence
    "success_flag",         # 23: Binary tracking success indicator (1.0 or 0.0)
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

# -----------------------------------------------------------------------------
# Base Facial Priors (Identical to V2 baseline)
# -----------------------------------------------------------------------------
AU_MEANS: np.ndarray = np.array(
    [0.22, 0.18, 0.28, 0.12, 0.32, 0.25, 0.15, 0.20, 0.38, 0.22, 0.18, 0.20, 0.15, 0.45],
    dtype=np.float32,
)
AU_STDS: np.ndarray = np.array(
    [0.25, 0.22, 0.28, 0.15, 0.32, 0.26, 0.18, 0.22, 0.38, 0.24, 0.20, 0.22, 0.18, 0.40],
    dtype=np.float32,
)
AU_PARTICIPANT_STD: float = 0.08

POSE_MEANS: np.ndarray = np.array([0.00, 0.00, 0.00], dtype=np.float32)
POSE_STDS: np.ndarray = np.array([0.08, 0.12, 0.05], dtype=np.float32)
POSE_PARTICIPANT_STD: float = 0.04
POSE_CORR_YAW_ROLL: float = 0.25

GAZE_MEANS: np.ndarray = np.array([0.00, 0.00], dtype=np.float32)
GAZE_STDS: np.ndarray = np.array([0.10, 0.08], dtype=np.float32)
GAZE_PARTICIPANT_STD: float = 0.03
GAZE_STABILITY_OMEGA_0: float = 1.0
RIGID_MOTION_V_0: float = 2.0
NON_RIGID_MOTION_ALPHA_0: float = 1.5

# -----------------------------------------------------------------------------
# Clinical Conditioning Covariates Specification (Approved Non-Target Only)
# -----------------------------------------------------------------------------
CONDITIONING_COVARIATE_NAMES: List[str] = [
    "norm_age",
    "sleep_disruption",
    "support_deficit",
    "infant_distress",
    "maternal_affect",
]

# Clinical shift weights W_video (shape: [num_covariates=5, num_channels=24])
# Rows: norm_age, sleep_disruption, support_deficit, infant_distress, maternal_affect
# Cols: 0..13 (AUs), 14..16 (Pose), 17..18 (Gaze), 19 (Gaze stab), 20..21 (Motion), 22..23 (Tracking)
CLINICAL_SHIFT_WEIGHTS_VIDEO: np.ndarray = np.zeros((5, 24), dtype=np.float32)

# Row 0: norm_age -> subtle age-related kinematic slowing
CLINICAL_SHIFT_WEIGHTS_VIDEO[0, 14] = -0.01  # pose_pitch slight forward tilt
CLINICAL_SHIFT_WEIGHTS_VIDEO[0, 21] = -0.01  # non_rigid_motion slight reduction

# Row 1: sleep_disruption (fatigue proxy: drooping head, downward gaze, smile reduction)
CLINICAL_SHIFT_WEIGHTS_VIDEO[1, 4]  = -0.04  # AU06 cheek raiser reduction
CLINICAL_SHIFT_WEIGHTS_VIDEO[1, 8]  = -0.05  # AU12 zygomaticus reduction
CLINICAL_SHIFT_WEIGHTS_VIDEO[1, 14] = -0.06  # pose_pitch downward head tilt (~ -3.4 deg)
CLINICAL_SHIFT_WEIGHTS_VIDEO[1, 18] = -0.05  # gaze_angle_y downward gaze (~ -2.9 deg)
CLINICAL_SHIFT_WEIGHTS_VIDEO[1, 19] = -0.03  # gaze_stability reduction

# Row 2: support_deficit (chronic psychosocial strain: brow tension)
CLINICAL_SHIFT_WEIGHTS_VIDEO[2, 2]  = +0.04  # AU04 brow lowerer
CLINICAL_SHIFT_WEIGHTS_VIDEO[2, 10] = +0.03  # AU15 lip corner depressor
CLINICAL_SHIFT_WEIGHTS_VIDEO[2, 15] = +0.02  # pose_yaw slight gaze/head avoidance

# Row 3: infant_distress (acute maternal worry/stress: upper facial tension)
CLINICAL_SHIFT_WEIGHTS_VIDEO[3, 0]  = +0.03  # AU01 inner brow raiser
CLINICAL_SHIFT_WEIGHTS_VIDEO[3, 2]  = +0.06  # AU04 brow lowerer
CLINICAL_SHIFT_WEIGHTS_VIDEO[3, 7]  = +0.02  # AU10 upper lip raiser

# Row 4: maternal_affect (affective blunting: suppressed smiles, increased brow/mouth sadness)
CLINICAL_SHIFT_WEIGHTS_VIDEO[4, 2]  = +0.08  # AU04 brow furrowing
CLINICAL_SHIFT_WEIGHTS_VIDEO[4, 4]  = -0.10  # AU06 Duchenne cheek raiser damping
CLINICAL_SHIFT_WEIGHTS_VIDEO[4, 8]  = -0.12  # AU12 zygomaticus major smile damping
CLINICAL_SHIFT_WEIGHTS_VIDEO[4, 10] = +0.06  # AU15 lip corner depressor
CLINICAL_SHIFT_WEIGHTS_VIDEO[4, 14] = -0.04  # pose_pitch downward tilt
CLINICAL_SHIFT_WEIGHTS_VIDEO[4, 18] = -0.04  # gaze_angle_y downward gaze

# Strict assertion: Tracking quality channels (22, 23) MUST have exactly 0 shift
assert np.all(CLINICAL_SHIFT_WEIGHTS_VIDEO[:, 22:24] == 0.0), "Tracking quality must never be conditioned!"


def get_au_correlation_matrix() -> np.ndarray:
    """Build the empirical 14x14 AU correlation matrix matching OpenFace physiological synergies."""
    R = np.eye(14, dtype=np.float32)

    def set_sym(i: int, j: int, val: float) -> None:
        R[i, j] = R[j, i] = np.float32(val)

    # 1. Duchenne Smile Synergy (AU06 + AU12)
    set_sym(4, 8, 0.72)

    # 2. Eyebrow Coordination: AU01 + AU02, AU01 + AU04
    set_sym(0, 1, 0.65)
    set_sym(0, 2, 0.35)

    # 3. Brow Lowerer + Eye Squint Tension: AU04 + AU07
    set_sym(2, 5, 0.45)

    # 4. Upper Lip / Nasolabial: AU09 + AU10
    set_sym(6, 7, 0.58)

    # 5. Lower Face Sadness / Tension: AU15 + AU17
    set_sym(10, 11, 0.40)

    # 6. Mouth Opening: AU25 + AU12
    set_sym(13, 8, 0.30)

    # Regularize for positive definiteness
    eigenvals = np.linalg.eigvalsh(R)
    if np.min(eigenvals) < 1e-4:
        R += np.eye(14, dtype=np.float32) * (abs(float(np.min(eigenvals))) + 1e-3)
        d = np.sqrt(np.diag(R))
        R = R / np.outer(d, d)

    return R

