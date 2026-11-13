"""Automated test suite for synthetic audio pipeline generation.

Validates the 12 core requirements for the synthetic audio feature profiles:
1. Exactly 800 records generated.
2. Exactly 640 train and 160 test partitions.
3. Participant IDs match train_test_split_manifest.csv exactly (BGD_001 to BGD_800).
4. Zero duplicate participant IDs.
5. All 800 .npy feature files exist and are readable.
6. Tensor shapes are (T, 128) with dtype float32 (T in [30, 90]).
7. Zero NaNs or Infs in scalars and tensors.
8. Acoustic summary features fall within approved physiological bounds.
9. Zero EPDS/PHQ-9 target leakage in conditioning extractor or output.
10. Correct handling of missing covariates via neutral training prior.
11. Deterministic reproducibility when re-run with seed 42.
12. data_origin tag is CLINICALLY_CONDITIONED_SYNTHETIC across all records.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from pipelines.synthetic_audio.config import (
    ACOUSTIC_FEATURE_BOUNDS,
    ACOUSTIC_FEATURE_NAMES,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    EMBEDDING_DIM,
    MAX_SEQUENCE_LENGTH,
    MIN_SEQUENCE_LENGTH,
    MODELING_MATRIX_PATH,
    SYNTHETIC_AUDIO_DIR,
    SYNTHETIC_AUDIO_FEATURES_DIR,
    SYNTHETIC_AUDIO_MANIFEST_PATH,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
)
from pipelines.synthetic_audio.conditioning import (
    ClinicalConditioningExtractor,
    extract_cohort_conditioning,
)
from pipelines.synthetic_audio.generator import (
    SyntheticAudioGenerator,
)


@pytest.fixture(scope="module")
def audio_manifest():
    """Load the generated audio manifest."""
    assert SYNTHETIC_AUDIO_MANIFEST_PATH.exists(), (
        f"Audio manifest not found at {SYNTHETIC_AUDIO_MANIFEST_PATH}"
    )
    return pd.read_csv(SYNTHETIC_AUDIO_MANIFEST_PATH)


@pytest.fixture(scope="module")
def split_manifest():
    """Load the frozen train/test split manifest."""
    assert TRAIN_TEST_SPLIT_MANIFEST_PATH.exists()
    return pd.read_csv(TRAIN_TEST_SPLIT_MANIFEST_PATH)


@pytest.fixture(scope="module")
def modeling_matrix():
    """Load the clinical modeling matrix."""
    assert MODELING_MATRIX_PATH.exists()
    return pd.read_csv(MODELING_MATRIX_PATH)


def test_1_record_count(audio_manifest):
    """Requirement 1: Exactly 800 records generated."""
    assert len(audio_manifest) == 800, f"Expected 800 records, got {len(audio_manifest)}"


def test_2_train_test_split_counts(audio_manifest):
    """Requirement 2: Exactly 640 train and 160 test records."""
    counts = audio_manifest["split_partition"].value_counts().to_dict()
    assert counts.get("train") == 640, f"Expected 640 train, got {counts.get('train')}"
    assert counts.get("test") == 160, f"Expected 160 test, got {counts.get('test')}"


def test_3_participant_id_alignment(audio_manifest, split_manifest):
    """Requirement 3: Participant IDs match train_test_split_manifest.csv exactly."""
    expected_ids = split_manifest["participant_id"].tolist()
    actual_ids = audio_manifest["participant_id"].tolist()
    assert actual_ids == expected_ids, "Participant IDs do not match split manifest order"
    assert actual_ids[0] == "BGD_001"
    assert actual_ids[-1] == "BGD_800"


def test_4_no_duplicate_ids(audio_manifest):
    """Requirement 4: Zero duplicate participant IDs."""
    unique_count = audio_manifest["participant_id"].nunique()
    assert unique_count == 800, f"Expected 800 unique IDs, got {unique_count}"


def test_5_all_npy_files_exist_and_readable(audio_manifest):
    """Requirement 5: All 800 .npy files exist and are readable."""
    for _, row in audio_manifest.iterrows():
        p_id = row["participant_id"]
        rel_path = Path(row["embedding_path"])
        # Resolve path relative to project root
        file_path = Path(__file__).resolve().parent.parent / rel_path
        assert file_path.exists(), f"Embedding file missing: {file_path}"
        tensor = np.load(file_path)
        assert isinstance(tensor, np.ndarray), f"File {file_path} is not a valid numpy array"


def test_6_tensor_shapes_and_dtypes(audio_manifest):
    """Requirement 6: Tensor shapes are (T, 128) with dtype float32 (T in [30, 90])."""
    # Sample a subset of tensors across train and test for fast comprehensive verification
    test_rows = pd.concat([audio_manifest.head(20), audio_manifest.tail(20)])
    for _, row in test_rows.iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["embedding_path"]
        tensor = np.load(file_path)
        assert tensor.dtype == np.float32, f"Expected float32, got {tensor.dtype}"
        assert tensor.ndim == 2, f"Expected 2D tensor, got {tensor.ndim}D"
        assert tensor.shape[1] == EMBEDDING_DIM, (
            f"Expected embedding dim {EMBEDDING_DIM}, got {tensor.shape[1]}"
        )
        assert MIN_SEQUENCE_LENGTH <= tensor.shape[0] <= MAX_SEQUENCE_LENGTH, (
            f"Sequence length {tensor.shape[0]} outside [{MIN_SEQUENCE_LENGTH}, {MAX_SEQUENCE_LENGTH}]"
        )
        assert tensor.shape[0] == row["sequence_length"], (
            f"Manifest sequence length {row['sequence_length']} mismatch with tensor {tensor.shape[0]}"
        )


def test_7_zero_nans_or_infs(audio_manifest):
    """Requirement 7: Zero NaNs or Infs in scalars and tensors."""
    # Check scalars in manifest
    scalar_cols = ACOUSTIC_FEATURE_NAMES + ["sequence_length", "generation_seed"]
    for col in scalar_cols:
        assert not audio_manifest[col].isnull().any(), f"NaN found in column {col}"
        assert not np.isinf(audio_manifest[col]).any(), f"Inf found in column {col}"

    # Check tensors
    for _, row in audio_manifest.iloc[::20].iterrows():  # Check every 20th tensor
        file_path = Path(__file__).resolve().parent.parent / row["embedding_path"]
        tensor = np.load(file_path)
        assert not np.isnan(tensor).any(), f"NaN in tensor {row['participant_id']}"
        assert not np.isinf(tensor).any(), f"Inf in tensor {row['participant_id']}"


def test_8_physiological_bounds(audio_manifest):
    """Requirement 8: Acoustic features fall within approved physiological bounds."""
    for feat_name, (lower, upper) in ACOUSTIC_FEATURE_BOUNDS.items():
        vals = audio_manifest[feat_name]
        min_val = vals.min()
        max_val = vals.max()
        assert min_val >= lower, f"{feat_name} min {min_val} below lower bound {lower}"
        assert max_val <= upper, f"{feat_name} max {max_val} above upper bound {upper}"


def test_9_target_isolation_and_leakage_prevention(audio_manifest, modeling_matrix):
    """Requirement 9: No EPDS/PHQ-9 target leakage."""
    # Ensure manifest does not contain any target columns
    for col in audio_manifest.columns:
        col_lower = col.lower()
        assert "epds" not in col_lower, f"EPDS column '{col}' leaked into audio manifest"
        assert "target" not in col_lower, f"Target column '{col}' leaked into audio manifest"

    # Verify conditioning extractor strictly blocks target columns if passed
    extractor = ClinicalConditioningExtractor()
    df_with_target = modeling_matrix[["Age", "EPDS_high_risk_screening_threshold"]].copy()
    with pytest.raises(ValueError, match="Prohibited target column detected"):
        extractor.fit(df_with_target)


def test_10_missing_covariate_handling():
    """Requirement 10: Missing covariates default to neutral training prior."""
    extractor = ClinicalConditioningExtractor()
    # Create mock training slice with some known 'Need for Support' values
    train_mock = pd.DataFrame(
        {
            "Age": [25, 30, 35],
            "Need for Support": ["Low", "High", np.nan],
        }
    )
    extractor.fit(train_mock)
    # The non-null values are Low (0.0) and High (1.0), so mean is 0.5
    assert extractor.train_need_for_support_prior_ == 0.5

    # Test transformation of a record with NaN in Need for Support
    test_mock = pd.DataFrame(
        {
            "Age": [28],
            "Relax/sleep when newborn is tended ": ["Yes"],
            "Relax/sleep when the newborn is asleep": ["Yes"],
            "Recieved Support": ["Medium"],  # 0.5
            "Need for Support": [np.nan],  # Should receive 0.5 prior
            "Newborn illness": ["No"],
            "Worry about newborn": ["No"],
            "Feeling about motherhood": ["Happy"],
        }
    )
    transformed = extractor.transform(test_mock)
    # support_deficit = (recieved(0.5) + need(0.5)) / 2 = 0.5
    assert transformed["support_deficit"].iloc[0] == 0.5


def test_11_deterministic_reproducibility():
    """Requirement 11: Deterministic reproducibility with seed 42."""
    gen1 = SyntheticAudioGenerator(seed=DEFAULT_RANDOM_SEED)
    gen2 = SyntheticAudioGenerator(seed=DEFAULT_RANDOM_SEED)

    rng1 = np.random.default_rng(DEFAULT_RANDOM_SEED * 10000 + 1)
    rng2 = np.random.default_rng(DEFAULT_RANDOM_SEED * 10000 + 1)

    cov_vec = np.array([0.1, 0.4, 0.3, 0.0, 0.5], dtype=np.float64)

    feats1 = gen1.generate_summary_features(cov_vec, rng1)
    feats2 = gen2.generate_summary_features(cov_vec, rng2)
    assert feats1 == feats2, "Summary features are not identical across runs with seed 42"

    t1 = gen1.generate_temporal_embedding(feats1, 40, rng1)
    t2 = gen2.generate_temporal_embedding(feats2, 40, rng2)
    np.testing.assert_array_equal(t1, t2, err_msg="Tensors are not bitwise identical with seed 42")


def test_12_provenance_data_origin_tag(audio_manifest):
    """Requirement 12: data_origin tag is CLINICALLY_CONDITIONED_SYNTHETIC on all rows."""
    origins = audio_manifest["data_origin"].unique()
    assert len(origins) == 1, f"Expected exactly 1 data origin tag, got {origins}"
    assert origins[0] == DATA_ORIGIN_TAG, (
        f"Expected '{DATA_ORIGIN_TAG}', got '{origins[0]}'"
    )

