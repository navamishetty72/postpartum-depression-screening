"""Configuration parameters for the clinical numerical pipeline.

Postpartum Depression (PPD) Multimodal Recognition Research Prototype.
"""

from pathlib import Path
from typing import List, Dict, Any

# Reproducibility
RANDOM_SEED: int = 42

# Directory and Data Paths
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
RAW_DATA_PATH: Path = PROJECT_ROOT / "data" / "raw" / "Numerical" / "PPD_dataset_v3.csv"
MODELING_MATRIX_PATH: Path = PROJECT_ROOT / "data" / "processed" / "Numerical" / "ppd_modeling_matrix.csv"
SPLIT_MANIFEST_PATH: Path = PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"
ARTIFACTS_DIR: Path = PROJECT_ROOT / "models" / "clinical_numerical"

# Canonical Target Definition
TARGET_COLUMN: str = "target_canonical_epds_ge_13"
RAW_TARGET_COLUMN: str = "EPDS_high_risk_screening_threshold"

# Features to Strictly Exclude from Inputs (Target Leakage Safeguard)
EXCLUDED_COLUMNS: List[str] = [
    # Primary ground truth and intermediate score targets
    "EPDS_high_risk_screening_threshold",
    "target_canonical_epds_ge_13",
    "EPDS Score",
    "EPDS Result",
    "PHQ9 Score",
    "PHQ9 Result",
    # EPDS 10 individual symptom items
    "You have been able to laugh and see the funny side of things",
    "You have looked forward with enjoyment to things",
    "You have blamed myself unnecessarily when things went wrong",
    "You have been anxious or worried for no good reason",
    "You have felt scared or panicky for no good reason",
    "Things have been getting to you",
    "You have been so unhappy that you have had difficulty sleeping",
    "You have felt sad or miserable",
    "You have been so unhappy that you have been crying",
    "The thought of harming yourself has occurred ",
    # PHQ-9 9 individual symptom items
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself or that you are a failure or have let yourself or your family down",
    "rouble concentrating on things",
    "Moving or speaking or restlessness",
    "Thoughts that you would be better off dead, or of hurting yourself",
    # Tracking columns
    "sr",
    "participant_id",
    "matrix_index",
    "split_partition",
]

# Numerical Predictors (2 continuous / discrete counts)
NUMERICAL_FEATURES: List[str] = [
    "Age",
    "Number of the latest pregnancy",
]

# Categorical Predictors (44 features)
CATEGORICAL_FEATURES: List[str] = [
    "Residence",
    "Education Level",
    "Marital status",
    "Occupation before latest pregnancy",
    "Monthly income before latest pregnancy",
    "Occupation After Your Latest Childbirth",
    "Current monthly income",
    "Husband's education level",
    "Husband’s monthly income",
    "Addiction",
    "Total children",
    "Disease before pregnancy",
    "History of pregnancy loss",
    "Family type",
    "Number of household members",
    "Relationship with the in-laws",
    "Relationship with husband",
    "Relationship with the newborn",
    "Relationship between father and newborn",
    "Feeling about motherhood",
    "Recieved Support",
    "Need for Support",
    "Major changes or losses during pregnancy",
    "Abuse",
    "Trust and share feelings",
    "Pregnancy length",
    "Pregnancy plan",
    "Regular checkups",
    "Fear of pregnancy",
    "Diseases during pregnancy",
    "Age of newborn",
    "Age of immediate older children",
    "Mode of delivery",
    "Gender of newborn",
    "Birth compliancy",
    "Breastfeed",
    "Newborn illness",
    "Worry about newborn",
    "Relax/sleep when newborn is tended ",
    "Relax/sleep when the newborn is asleep",
    "Angry after latest child birth",
    "Feeling for regular activities",
    "Depression before pregnancy (PHQ2)",
    "Depression during pregnancy (PHQ2)",
]

# Total Non-Target Predictor Count Check
TOTAL_PREDICTOR_COUNT: int = len(NUMERICAL_FEATURES) + len(CATEGORICAL_FEATURES)
assert TOTAL_PREDICTOR_COUNT == 46, f"Expected 46 predictors, got {TOTAL_PREDICTOR_COUNT}"

# Cross-Validation & Modeling Configuration
CV_FOLDS: int = 5
DECISION_THRESHOLD: float = 0.5

MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "logistic_regression": {
        "C": 0.1,
        "penalty": "l2",
        "solver": "lbfgs",
        "class_weight": "balanced",
        "max_iter": 1000,
        "random_state": RANDOM_SEED,
    },
    "random_forest": {
        "n_estimators": 100,
        "max_depth": 5,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "class_weight": "balanced",
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
    },
    "hist_gradient_boosting": {
        "max_iter": 100,
        "max_depth": 4,
        "learning_rate": 0.05,
        "class_weight": "balanced",
        "random_state": RANDOM_SEED,
    },
}

