"""Data loader module for the clinical numerical pipeline.

Enforces strict participant isolation, schema validation, and zero target leakage.
"""

from typing import Tuple, Dict, Any
import pandas as pd
import numpy as np

from .config import (
    MODELING_MATRIX_PATH,
    SPLIT_MANIFEST_PATH,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    TOTAL_PREDICTOR_COUNT,
    TARGET_COLUMN,
    RAW_TARGET_COLUMN,
    EXCLUDED_COLUMNS,
)


def load_clinical_data(
    modeling_matrix_path: str = str(MODELING_MATRIX_PATH),
    split_manifest_path: str = str(SPLIT_MANIFEST_PATH),
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]:
    """Load, validate, and partition the clinical numerical dataset.

    Returns:
        Tuple of (X_train, y_train, manifest_train, X_test, y_test, manifest_test)

    Raises:
        ValueError: If row counts, feature counts, class balances, or overlap checks fail.
    """
    df_matrix = pd.read_csv(modeling_matrix_path)
    df_manifest = pd.read_csv(split_manifest_path)

    # 1. Dimensionality Verification
    if len(df_matrix) != 800:
        raise ValueError(f"Expected 800 rows in modeling matrix, found {len(df_matrix)}")
    if len(df_manifest) != 800:
        raise ValueError(f"Expected 800 rows in split manifest, found {len(df_manifest)}")

    # 2. Target Resolution and Isolation
    if TARGET_COLUMN in df_manifest.columns:
        y = df_manifest[TARGET_COLUMN].copy()
    elif RAW_TARGET_COLUMN in df_matrix.columns:
        y = df_matrix[RAW_TARGET_COLUMN].copy()
    else:
        raise ValueError(f"Neither {TARGET_COLUMN} nor {RAW_TARGET_COLUMN} found in inputs.")

    # Validate Canonical Target Distribution (351 positive, 449 negative)
    positives = int((y == 1).sum())
    negatives = int((y == 0).sum())
    if positives != 351 or negatives != 449:
        raise ValueError(
            f"Canonical target distribution mismatch: expected 351 positive, 449 negative; got {positives} pos, {negatives} neg"
        )

    # 3. Extract Predictor Matrix X (Strictly the 46 Non-Target Features)
    expected_features = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
    assert len(expected_features) == TOTAL_PREDICTOR_COUNT == 46

    missing_cols = [c for c in expected_features if c not in df_matrix.columns]
    if missing_cols:
        raise ValueError(f"Missing required predictor columns in modeling matrix: {missing_cols}")

    X = df_matrix[expected_features].copy()

    # 4. Strict Target Leakage Prevention Check
    for leak_candidate in EXCLUDED_COLUMNS:
        if leak_candidate in X.columns:
            raise ValueError(f"Target leakage detected! Excluded column '{leak_candidate}' is present in predictor matrix.")

    # 5. Partition by Frozen Manifest Split
    train_mask = (df_manifest["split_partition"] == "train").values
    test_mask = (df_manifest["split_partition"] == "test").values

    X_train = X.iloc[train_mask].copy().reset_index(drop=True)
    y_train = y.iloc[train_mask].copy().reset_index(drop=True)
    manifest_train = df_manifest.iloc[train_mask].copy().reset_index(drop=True)

    X_test = X.iloc[test_mask].copy().reset_index(drop=True)
    y_test = y.iloc[test_mask].copy().reset_index(drop=True)
    manifest_test = df_manifest.iloc[test_mask].copy().reset_index(drop=True)

    # 6. Verify Partition Sizes and Class Balances
    if len(X_train) != 640:
        raise ValueError(f"Expected 640 training records, got {len(X_train)}")
    if len(X_test) != 160:
        raise ValueError(f"Expected 160 testing records, got {len(X_test)}")

    train_pos = int((y_train == 1).sum())
    train_neg = int((y_train == 0).sum())
    test_pos = int((y_test == 1).sum())
    test_neg = int((y_test == 0).sum())

    if train_pos != 281 or train_neg != 359:
        raise ValueError(f"Train class balance mismatch: expected 281/359, got {train_pos}/{train_neg}")
    if test_pos != 70 or test_neg != 90:
        raise ValueError(f"Test class balance mismatch: expected 70/90, got {test_pos}/{test_neg}")

    # 7. Verify Zero Participant Overlap
    train_pids = set(manifest_train["participant_id"])
    test_pids = set(manifest_test["participant_id"])
    overlap = train_pids.intersection(test_pids)
    if len(overlap) > 0:
        raise ValueError(f"Data leakage detected! Found {len(overlap)} overlapping participants between train and test splits.")

    return X_train, y_train, manifest_train, X_test, y_test, manifest_test

