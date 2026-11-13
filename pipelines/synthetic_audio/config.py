"""Configuration for synthetic audio pipeline data generation.

This module defines the acoustic summary feature bounds, baseline parameters,
correlation structure, linear conditioning coefficients, and temporal embedding
specifications for generating synthetic audio feature profiles.

SCIENTIFIC INTEGRITY NOTICE:
This is an architectural integration benchmark. The Bangladeshi clinical cohort
contains ZERO physical audio recordings. Synthetic profiles are generated using
non-target clinical covariates as engineering fixtures to test downstream multimodal
fusion architectures. These simulated features do NOT represent genuine clinical
observations and cannot demonstrate real-world clinical predictive value.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

# -----------------------------------------------------------------------------
# Base Paths
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_CLINICAL_PATH = PROJECT_ROOT / "data" / "raw" / "Numerical" / "PPD_dataset_v3.csv"
MODELING_MATRIX_PATH = PROJECT_ROOT / "data" / "processed" / "Numerical" / "ppd_modeling_matrix.csv"
TRAIN_TEST_SPLIT_MANIFEST_PATH = (
    PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"
)

SYNTHETIC_AUDIO_DIR = PROJECT_ROOT / "data" / "synthetic" / "audio"
SYNTHETIC_AUDIO_FEATURES_DIR = SYNTHETIC_AUDIO_DIR / "features"
SYNTHETIC_AUDIO_MANIFEST_PATH = SYNTHETIC_AUDIO_DIR / "audio_manifest.csv"

# -----------------------------------------------------------------------------
# Provenance & Audit Tags
# -----------------------------------------------------------------------------
DATA_ORIGIN_TAG = "CLINICALLY_CONDITIONED_SYNTHETIC"
DEFAULT_RANDOM_SEED = 42

# -----------------------------------------------------------------------------
# Acoustic Summary Features Specification
# -----------------------------------------------------------------------------
ACOUSTIC_FEATURE_NAMES: List[str] = [
    "f0_mean_hz",
    "f0_std_hz",
    "jitter_local_percent",
    "shimmer_local_percent",
    "hnr_db",
    "speech_rate_syllables_per_sec",
    "pause_ratio",
]

# Baseline female speaking voice parameters (literature prior centers)
BASELINE_ACOUSTIC_MEANS: Dict[str, float] = {
    "f0_mean_hz": 215.0,
    "f0_std_hz": 28.0,
    "jitter_local_percent": 1.20,
    "shimmer_local_percent": 4.50,
    "hnr_db": 20.0,
    "speech_rate_syllables_per_sec": 3.80,
    "pause_ratio": 0.24,
}

# Empirical residual standard deviations for acoustic parameters
ACOUSTIC_FEATURE_STDS: Dict[str, float] = {
    "f0_mean_hz": 18.0,
    "f0_std_hz": 6.5,
    "jitter_local_percent": 0.45,
    "shimmer_local_percent": 1.50,
    "hnr_db": 3.0,
    "speech_rate_syllables_per_sec": 0.55,
    "pause_ratio": 0.06,
}

# Hard physiological plausibility boundaries (clamping intervals)
ACOUSTIC_FEATURE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "f0_mean_hz": (130.0, 310.0),
    "f0_std_hz": (8.0, 75.0),
    "jitter_local_percent": (0.20, 5.50),
    "shimmer_local_percent": (1.00, 16.00),
    "hnr_db": (8.00, 30.00),
    "speech_rate_syllables_per_sec": (1.80, 6.20),
    "pause_ratio": (0.08, 0.65),
}

# -----------------------------------------------------------------------------
# Empirical Acoustic Correlation Matrix (R)
# Order: [f0_mean, f0_std, jitter, shimmer, hnr, speech_rate, pause_ratio]
# -----------------------------------------------------------------------------
ACOUSTIC_CORRELATION_MATRIX: np.ndarray = np.array(
    [
        [ 1.00,  0.15,  0.05,  0.05, -0.05,  0.10, -0.05],  # f0_mean_hz
        [ 0.15,  1.00, -0.10, -0.10,  0.15,  0.20, -0.25],  # f0_std_hz
        [ 0.05, -0.10,  1.00,  0.65, -0.55, -0.15,  0.20],  # jitter_local_percent
        [ 0.05, -0.10,  0.65,  1.00, -0.50, -0.10,  0.15],  # shimmer_local_percent
        [-0.05,  0.15, -0.55, -0.50,  1.00,  0.15, -0.20],  # hnr_db
        [ 0.10,  0.20, -0.15, -0.10,  0.15,  1.00, -0.60],  # speech_rate_syllables_per_sec
        [-0.05, -0.25,  0.20,  0.15, -0.20, -0.60,  1.00],  # pause_ratio
    ],
    dtype=np.float64,
)

# -----------------------------------------------------------------------------
# Clinical Conditioning Covariates Specification
# -----------------------------------------------------------------------------
CONDITIONING_COVARIATE_NAMES: List[str] = [
    "norm_age",
    "sleep_disruption",
    "support_deficit",
    "infant_distress",
    "maternal_affect",
]

# Linear shift coefficients W_clinical (shape: [num_covariates, num_features])
# Rows: norm_age, sleep_disruption, support_deficit, infant_distress, maternal_affect
# Cols: f0_mean, f0_std, jitter, shimmer, hnr, speech_rate, pause_ratio
# NOTE: These weights represent simulation engineering heuristics, NOT validated biomarkers.
CLINICAL_SHIFT_WEIGHTS: np.ndarray = np.array(
    [
        # norm_age: ~ -0.6 Hz/yr (~ -2.7 Hz/std), slight acoustic aging effects
        [-2.70, -0.50,  0.05,  0.10, -0.20, -0.05,  0.01],
        # sleep_disruption: vocal fatigue, lower pitch, reduced variability, increased perturbations
        [-3.00, -2.00,  0.20,  0.60, -1.20, -0.35,  0.05],
        # support_deficit: chronic psychosocial strain proxy
        [ 0.00, -1.50,  0.10,  0.30, -0.50, -0.15,  0.02],
        # infant_distress: acute stress / arousal, slight pitch elevation, increased shimmer
        [ 4.00,  1.00,  0.15,  0.40, -0.80, -0.10,  0.02],
        # maternal_affect: affective blunting proxy, flatter prosody, lower speech rate, higher pauses
        [-2.00, -3.00,  0.10,  0.30, -0.60, -0.30,  0.04],
    ],
    dtype=np.float64,
)

# -----------------------------------------------------------------------------
# Abstract Temporal Embedding Specification (Engineering Fixture)
# -----------------------------------------------------------------------------
EMBEDDING_DIM: int = 128
MIN_SEQUENCE_LENGTH: int = 30
MAX_SEQUENCE_LENGTH: int = 90
AR1_SMOOTHING_ALPHA: float = 0.85
AR1_NOISE_SCALE: float = 0.50
EMBEDDING_PROJECTION_SCALE: float = 0.50

