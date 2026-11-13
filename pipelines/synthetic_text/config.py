"""Configuration for synthetic text narrative generation.

Defines file paths, approved non-target conditioning columns, target isolation rules,
and text constraints for generating synthetic English postpartum narratives.

SCIENTIFIC INTEGRITY NOTICE:
This is an architectural integration benchmark. The Bangladeshi clinical survey cohort
contains ZERO qualitative patient interview transcripts, audio recordings, or clinical
intake notes. All generated narratives are fictional contextual representations
conditioned on non-target survey covariates to test multimodal NLP ingestion.
They do NOT represent authentic patient statements and cannot validate real-world
clinical diagnostic efficacy.
"""

from pathlib import Path
from typing import List, Set

# -----------------------------------------------------------------------------
# Base Paths
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_CLINICAL_PATH = PROJECT_ROOT / "data" / "raw" / "Numerical" / "PPD_dataset_v3.csv"
MODELING_MATRIX_PATH = PROJECT_ROOT / "data" / "processed" / "Numerical" / "ppd_modeling_matrix.csv"
TRAIN_TEST_SPLIT_MANIFEST_PATH = (
    PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"
)

SYNTHETIC_TEXT_DIR = PROJECT_ROOT / "data" / "synthetic" / "text"
SYNTHETIC_TEXT_NARRATIVES_DIR = SYNTHETIC_TEXT_DIR / "narratives"
SYNTHETIC_TEXT_MANIFEST_PATH = SYNTHETIC_TEXT_DIR / "text_manifest.csv"

# -----------------------------------------------------------------------------
# Provenance & Audit Tags
# -----------------------------------------------------------------------------
DATA_ORIGIN_TAG = "SYNTHETIC_FICTIONAL_NARRATIVE"
GENERATOR_VERSION = "1.0.0"
DEFAULT_RANDOM_SEED = 42
LANGUAGE_CODE = "en"

# -----------------------------------------------------------------------------
# Narrative Length Bounds (Target: 120-220 words)
# -----------------------------------------------------------------------------
MIN_WORD_COUNT = 110
MAX_WORD_COUNT = 230
JACCARD_SIMILARITY_THRESHOLD = 0.70

# -----------------------------------------------------------------------------
# Approved Non-Target Clinical Conditioning Variables (Exact 13 Columns)
# -----------------------------------------------------------------------------
APPROVED_CONDITIONING_COLUMNS: List[str] = [
    "Family type",
    "Number of household members",
    "Total children",
    "Occupation After Your Latest Childbirth",
    "Age of newborn",
    "Breastfeed",
    "Newborn illness",
    "Worry about newborn",
    "Relax/sleep when newborn is tended ",
    "Relax/sleep when the newborn is asleep",
    "Recieved Support",
    "Need for Support",
    "Trust and share feelings",
]

# -----------------------------------------------------------------------------
# Prohibited Variables (Target Leakage & Diagnostic / Sensitive Information)
# -----------------------------------------------------------------------------
PROHIBITED_COLUMNS_EXACT: Set[str] = {
    "target_canonical_epds_ge_13",
    "EPDS_high_risk_screening_threshold",
    "canonical_epds_score",
    "epds_score",
    "Depression before pregnancy (PHQ2)",
    "Depression during pregnancy (PHQ2)",
    "Abuse",
    "History of pregnancy loss",
    "Addiction",
    "Angry after latest child birth",
    "Fear of pregnancy",
}

# Prohibited clinical diagnosis terms in generated narratives
PROHIBITED_NARRATIVE_TERMS: List[str] = [
    "depression",
    "depressed",
    "anhedonia",
    "anxiety",
    "anxious",
    "ppd",
    "postpartum depression",
    "diagnosed",
    "diagnosis",
    "suicide",
    "suicidal",
    "self-harm",
    "mental health",
    "psychosis",
    "bipolar",
    "antidepressant",
    "phq",
    "epds",
]

