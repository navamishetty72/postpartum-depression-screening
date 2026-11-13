"""Configuration parameters for the four-modality late fusion pipeline."""

from pathlib import Path
from typing import Dict, List

# -----------------------------------------------------------------------------
# Base Directories and Manifest Paths
# -----------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

SPLIT_MANIFEST_PATH: Path = (
    PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"
)

# Modality Artifact Paths
CLINICAL_OOF_PATH: Path = (
    PROJECT_ROOT / "models" / "clinical_numerical" / "oof_predictions.csv"
)
CLINICAL_HOLDOUT_PATH: Path = (
    PROJECT_ROOT / "models" / "clinical_numerical" / "test_predictions.csv"
)

AUDIO_OOF_PATH: Path = (
    PROJECT_ROOT / "models" / "audio_model" / "oof_predictions.csv"
)
AUDIO_HOLDOUT_PATH: Path = (
    PROJECT_ROOT / "models" / "audio_model" / "test_predictions.csv"
)

TEXT_OOF_PATH: Path = (
    PROJECT_ROOT / "models" / "text_model" / "oof_predictions.csv"
)
TEXT_HOLDOUT_PATH: Path = (
    PROJECT_ROOT / "models" / "text_model" / "test_predictions.csv"
)

VIDEO_OOF_PATH: Path = (
    PROJECT_ROOT / "artifacts" / "video_model" / "canonical_aligned" / "oof_predictions_bilstm.csv"
)
VIDEO_HOLDOUT_PATH: Path = (
    PROJECT_ROOT / "artifacts" / "video_model" / "canonical_aligned" / "holdout_predictions_bilstm.csv"
)

# Target directory for all fusion artifacts
FUSION_ARTIFACTS_DIR: Path = PROJECT_ROOT / "models" / "fusion"

# -----------------------------------------------------------------------------
# Cohort & Target Specifications
# -----------------------------------------------------------------------------
EXPECTED_TRAIN_PARTICIPANTS: int = 640
EXPECTED_TEST_PARTICIPANTS: int = 160
EXPECTED_TOTAL_PARTICIPANTS: int = 800

TARGET_COLUMN: str = "target_canonical_epds_ge_13"
PARTICIPANT_ID_COLUMN: str = "participant_id"

# -----------------------------------------------------------------------------
# Feature Mappings (Default Linear-Baseline Configuration)
# -----------------------------------------------------------------------------
FEATURE_COLUMNS: List[str] = [
    "clinical_prob",
    "audio_prob",
    "text_prob",
    "video_prob",
]

DEFAULT_PROB_MAPPINGS: Dict[str, str] = {
    "clinical": "logistic_regression_prob",
    "audio": "logistic_regression_prob",
    "text": "predicted_probability",
    "video": "predicted_probability",
}

# -----------------------------------------------------------------------------
# Hyperparameters & Reproducibility
# -----------------------------------------------------------------------------
RANDOM_SEED: int = 42
CV_FOLDS: int = 5
DECISION_THRESHOLD: float = 0.5
N_BOOTSTRAPS: int = 1000
CONFIDENCE_LEVEL: float = 0.95
META_CLASSIFIER_C: float = 1.0

