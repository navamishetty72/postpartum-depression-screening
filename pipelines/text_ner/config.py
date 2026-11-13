"""Configuration parameters for the Text Named Entity Recognition (NER) pipeline.

Provides paths, reproducible seeds, split ratios, and annotation schemas.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Tuple

# Base Directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw" / "ppd-named-entity-dataset" / "PPD-NER-Corpus-1.0"
DATA_PROCESSED_DIR = DATA_DIR / "processed" / "text_ner"
MODELS_DIR = PROJECT_ROOT / "models" / "text_ner"
ANNOTATION_CONF_PATH = Path(__file__).resolve().parent / "annotation.conf"

# Ensure runtime directories exist
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Default Seed
RANDOM_SEED: int = 42

# Permitted Entity Types from annotation.conf
ALLOWED_ENTITY_LABELS: Tuple[str, ...] = ("MMLite",)


@dataclass(frozen=True)
class SplitConfig:
    """Document-isolated train/val/test splitting configuration."""

    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    seed: int = RANDOM_SEED

    def __post_init__(self) -> None:
        total = round(self.train_ratio + self.val_ratio + self.test_ratio, 6)
        if total != 1.0:
            raise ValueError(f"Split ratios must sum to 1.0, got {total}")


@dataclass(frozen=True)
class PreprocessingConfig:
    """Configuration for dataset validation, offset alignment, and overlap handling."""

    allowed_labels: Tuple[str, ...] = ALLOWED_ENTITY_LABELS
    overlap_strategy: Literal["longest", "first", "drop"] = "longest"
    reconcile_window: int = 15
    validation_report_path: Path = DATA_PROCESSED_DIR / "validation_report.json"
    splits_manifest_path: Path = DATA_PROCESSED_DIR / "dataset_splits.json"


@dataclass
class TrainingConfig:
    """Hyperparameters and settings for NER sequence classifier training."""

    seed: int = RANDOM_SEED
    c_param: float = 1.0
    max_iter: int = 500
    class_weight: str = "balanced"
    model_output_path: Path = MODELS_DIR / "text_ner_model.joblib"
    metrics_output_path: Path = DATA_PROCESSED_DIR / "evaluation_metrics.json"
    feature_window: int = 2
    max_train_samples: int = 1500  # For scalable CPU training on forum corpus

