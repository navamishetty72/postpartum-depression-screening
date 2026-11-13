"""Deterministic CI Test Fixture Generator for Canonical-Aligned Video Predictions.

Postpartum Depression (PPD) Multimodal Recognition Research Prototype.

SCIENTIFIC INTEGRITY & PROVENANCE NOTICE:
SYNTHETIC_CI_TEST_FIXTURE:
This module generates deterministic, participant-aligned synthetic video prediction
fixtures (oof_predictions_bilstm.csv and holdout_predictions_bilstm.csv) exclusively
for automated continuous integration (CI) and multimodal fusion architecture testing.

Zero authentic facial video recordings exist in this research cohort. These synthetic
fixtures exist solely to benchmark multimodal fusion engines and verify cross-modal
alignment (participant IDs, cross-validation fold isolation, and target leakage prevention)
without incurring expensive full neural network training overhead in CI environments.
They do NOT validate genuine clinical diagnostic efficacy or recurrent neural network performance.
"""

from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

# Repository Root & Manifest Paths
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
SPLIT_MANIFEST_PATH: Path = (
    PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"
)
CANONICAL_DIR: Path = PROJECT_ROOT / "artifacts" / "video_model" / "canonical_aligned"

TARGET_COLUMN: str = "target_canonical_epds_ge_13"
PARTICIPANT_ID_COLUMN: str = "participant_id"
SPLIT_COLUMN: str = "split_partition"

EXPECTED_TRAIN_PARTICIPANTS: int = 640
EXPECTED_TEST_PARTICIPANTS: int = 160
CV_FOLDS: int = 5
RANDOM_SEED: int = 42
DECISION_THRESHOLD: float = 0.5


def generate_ci_video_fixtures(
    output_dir: Path = CANONICAL_DIR,
    split_manifest_path: Path = SPLIT_MANIFEST_PATH,
    force: bool = False,
) -> None:
    """Generate deterministic participant-aligned video OOF and holdout prediction fixtures.

    Args:
        output_dir: Destination directory for the CSV fixture files.
        split_manifest_path: Authoritative frozen train/test split manifest path.
        force: If True, overwrite existing fixture files. If False, skip generation
               if files are already present on disk.
    """
    oof_path = output_dir / "oof_predictions_bilstm.csv"
    holdout_path = output_dir / "holdout_predictions_bilstm.csv"

    if not force and oof_path.is_file() and holdout_path.is_file():
        return

    if not split_manifest_path.is_file():
        raise FileNotFoundError(
            f"Authoritative split manifest missing at: {split_manifest_path}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(split_manifest_path)
    train_manifest = manifest[manifest[SPLIT_COLUMN] == "train"].reset_index(drop=True)
    test_manifest = manifest[manifest[SPLIT_COLUMN] == "test"].reset_index(drop=True)

    if len(train_manifest) != EXPECTED_TRAIN_PARTICIPANTS:
        raise ValueError(
            f"Expected {EXPECTED_TRAIN_PARTICIPANTS} train participants, got {len(train_manifest)}"
        )
    if len(test_manifest) != EXPECTED_TEST_PARTICIPANTS:
        raise ValueError(
            f"Expected {EXPECTED_TEST_PARTICIPANTS} test participants, got {len(test_manifest)}"
        )

    y_train = train_manifest[TARGET_COLUMN].values.astype(int)
    y_test = test_manifest[TARGET_COLUMN].values.astype(int)

    # 1. 5-Fold Stratified Cross-Validation Partition (0-based: 0..4)
    # Strictly aligned with StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    oof_folds = np.zeros(len(train_manifest), dtype=int)
    oof_probs = np.zeros(len(train_manifest), dtype=float)

    for fold_idx, (tr_idx, val_idx) in enumerate(skf.split(train_manifest, y_train), 0):
        oof_folds[val_idx] = fold_idx

        # Fold-local deterministic generation: validation predictions are conditioned
        # strictly on fold seed and parameters, ensuring zero validation participant leakage.
        fold_rng = np.random.RandomState(RANDOM_SEED + fold_idx * 1000 + 1)
        # Beta distribution with parameters (2.2, 2.8) yields realistic probabilities in [0.05, 0.95]
        val_raw_probs = fold_rng.beta(2.2, 2.8, size=len(val_idx))
        oof_probs[val_idx] = np.clip(val_raw_probs, 0.05, 0.95)

    oof_probs_rounded = np.round(oof_probs, 4)
    oof_labels = (oof_probs_rounded >= DECISION_THRESHOLD).astype(int)

    oof_df = pd.DataFrame({
        "participant_id": train_manifest[PARTICIPANT_ID_COLUMN].values,
        "fold": oof_folds,
        "true_target": y_train,
        "predicted_label": oof_labels,
        "predicted_probability": oof_probs_rounded,
    })

    # 2. Holdout Test Predictions (Single-shot, fixed seed, zero training contamination)
    test_rng = np.random.RandomState(RANDOM_SEED + 9999)
    test_raw_probs = test_rng.beta(2.2, 2.8, size=len(test_manifest))
    test_probs_rounded = np.round(np.clip(test_raw_probs, 0.05, 0.95), 4)
    test_labels = (test_probs_rounded >= DECISION_THRESHOLD).astype(int)

    holdout_df = pd.DataFrame({
        "participant_id": test_manifest[PARTICIPANT_ID_COLUMN].values,
        "true_target": y_test,
        "predicted_label": test_labels,
        "predicted_probability": test_probs_rounded,
    })

    # Save to disk
    oof_df.to_csv(oof_path, index=False)
    holdout_df.to_csv(holdout_path, index=False)


def ensure_ci_video_fixtures(
    output_dir: Path = CANONICAL_DIR,
    split_manifest_path: Path = SPLIT_MANIFEST_PATH,
) -> None:
    """Ensure canonical video test fixtures exist on disk, generating them if missing."""
    oof_path = output_dir / "oof_predictions_bilstm.csv"
    holdout_path = output_dir / "holdout_predictions_bilstm.csv"
    if not oof_path.is_file() or not holdout_path.is_file():
        generate_ci_video_fixtures(
            output_dir=output_dir,
            split_manifest_path=split_manifest_path,
            force=False,
        )


if __name__ == "__main__":
    print("Generating deterministic CI video baseline fixtures...")
    generate_ci_video_fixtures(force=True)
    print(f"Fixtures successfully generated at: {CANONICAL_DIR}")

