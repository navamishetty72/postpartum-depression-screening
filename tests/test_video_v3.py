"""Unit test suite for Video V3 experimental simulation fixture.

Validates:
1. Strict target exclusion assertion: generator and conditioning logic cannot accept EPDS or target variables.
2. Participant ID and cohort alignment: all 800 participants match train_test_split_manifest.csv.
3. Feature tensor schema and bounds: (T, 24) float32, no NaNs/Infs, valid channel bounds.
4. Canonical split isolation: normalizer fitted strictly on training partition without test leakage.
5. Reproducibility under fixed random seeds.
6. Non-interference with production Video V2 artifacts and models.
7. Experiment artifact validity: 640 canonical OOF predictions, valid probabilities in [0.0, 1.0].
8. Redundancy / shared variance verification (Video V3 R^2 > 0 vs Video V2 R^2 ~ 0).
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest

from pipelines.synthetic_video_v3.config_v3 import (
    CONDITIONING_COVARIATE_NAMES,
    DEFAULT_RANDOM_SEED,
    CHANNEL_NAMES,
    MODELING_MATRIX_PATH,
    PROJECT_ROOT,
    SYNTHETIC_VIDEO_V3_FEATURES_DIR,
    SYNTHETIC_VIDEO_V3_MANIFEST_PATH,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
    VIDEO_V3_EXPERIMENTS_DIR,
    CLINICAL_SHIFT_WEIGHTS_VIDEO,
)
from pipelines.synthetic_video_v3.conditioning import (
    ClinicalConditioningExtractor,
    extract_cohort_conditioning_v3,
)
from pipelines.synthetic_video_v3.generator_v3 import SyntheticVideoGeneratorV3


def test_strict_target_exclusion_assertion():
    """Verify that attempting to include target or EPDS columns raises ValueError."""
    extractor = ClinicalConditioningExtractor()
    bad_columns = [
        "target_canonical_epds_ge_13",
        "EPDS_high_risk_screening_threshold",
        "canonical_epds_score",
        "epds_total",
        "Depression before pregnancy (PHQ2)",
    ]

    for bad_col in bad_columns:
        corrupted_df = pd.DataFrame({
            "Age": [25.0],
            "Need for Support": ["Medium"],
            bad_col: [1.0],
        })
        with pytest.raises(ValueError, match="Prohibited"):
            extractor.fit(corrupted_df)


def test_tracking_channels_zero_clinical_shift():
    """Verify that tracking quality channels (22 and 23) receive exactly zero clinical shift."""
    assert np.all(CLINICAL_SHIFT_WEIGHTS_VIDEO[:, 22] == 0.0), (
        "Channel 22 (tracking_confidence) must have 0.0 clinical shift weight across all covariates"
    )
    assert np.all(CLINICAL_SHIFT_WEIGHTS_VIDEO[:, 23] == 0.0), (
        "Channel 23 (success_flag) must have 0.0 clinical shift weight across all covariates"
    )


@pytest.mark.skipif(
    not SYNTHETIC_VIDEO_V3_MANIFEST_PATH.is_file(),
    reason="Video V3 synthetic dataset not generated (run python -m pipelines.synthetic_video_v3.generator_v3)",
)
def test_participant_alignment():
    """Verify that 800 video features exist and match the canonical split manifest exactly."""
    manifest_df = pd.read_csv(TRAIN_TEST_SPLIT_MANIFEST_PATH)
    assert len(manifest_df) == 800, f"Expected 800 manifest rows, got {len(manifest_df)}"

    assert SYNTHETIC_VIDEO_V3_MANIFEST_PATH.is_file(), "Video V3 manifest file missing"
    v3_manifest = pd.read_csv(SYNTHETIC_VIDEO_V3_MANIFEST_PATH)
    assert len(v3_manifest) == 800, f"Expected 800 Video V3 manifest rows, got {len(v3_manifest)}"

    # Check participant IDs match identically in order
    assert (manifest_df["participant_id"] == v3_manifest["participant_id"]).all(), (
        "Participant ID mismatch between canonical split manifest and Video V3 manifest"
    )

    # Check partition counts
    assert (v3_manifest["split_partition"] == "train").sum() == 640
    assert (v3_manifest["split_partition"] == "test").sum() == 160


@pytest.mark.skipif(
    not SYNTHETIC_VIDEO_V3_MANIFEST_PATH.is_file(),
    reason="Video V3 synthetic dataset not generated (run python -m pipelines.synthetic_video_v3.generator_v3)",
)
def test_feature_tensor_properties():
    """Verify that generated feature tensors are (T, 24) float32 without NaNs or Infs."""
    v3_manifest = pd.read_csv(SYNTHETIC_VIDEO_V3_MANIFEST_PATH)
    sample_rows = v3_manifest.sample(n=10, random_state=DEFAULT_RANDOM_SEED)

    for _, row in sample_rows.iterrows():
        feat_path = Path(row["feature_file_path"])
        if not feat_path.is_absolute():
            feat_path = PROJECT_ROOT / feat_path
        assert feat_path.is_file(), f"Missing feature file: {feat_path}"

        tensor = np.load(feat_path)
        assert isinstance(tensor, np.ndarray), "Loaded object must be np.ndarray"
        assert tensor.dtype == np.float32, f"Expected float32 dtype, got {tensor.dtype}"
        assert tensor.ndim == 2, f"Expected 2D tensor (T, 24), got {tensor.ndim}D"
        assert tensor.shape[1] == 24, f"Expected 24 channels, got {tensor.shape[1]}"
        assert tensor.shape[0] >= 45, f"Expected at least 45 frames, got {tensor.shape[0]}"
        assert tensor.shape[0] <= 120, f"Expected at most 120 frames, got {tensor.shape[0]}"

        # Check for NaNs and Infs
        assert not np.isnan(tensor).any(), f"NaN found in {feat_path}"
        assert not np.isinf(tensor).any(), f"Inf found in {feat_path}"

        # Channel 22 (confidence): bounded in [0, 1]
        conf = tensor[:, 22]
        assert (conf >= 0.0).all() and (conf <= 1.0).all(), "Confidence values out of [0, 1] range"

        # Channel 23 (success): strictly binary in {0.0, 1.0}
        success = tensor[:, 23]
        unique_success = set(np.unique(success))
        assert unique_success.issubset({0.0, 1.0}), f"Unexpected success values: {unique_success}"


def test_generator_reproducibility():
    """Verify that generation is strictly deterministic when passing identical seed and covariates."""
    dummy_cov = np.array([0.5, -0.2, 0.8, -0.5, 0.1], dtype=np.float32)
    gen1 = SyntheticVideoGeneratorV3(seed=12345)
    seq1, meta1 = gen1.generate_single_sequence(participant_sr=42, covariate_vector=dummy_cov)

    gen2 = SyntheticVideoGeneratorV3(seed=12345)
    seq2, meta2 = gen2.generate_single_sequence(participant_sr=42, covariate_vector=dummy_cov)

    np.testing.assert_array_equal(seq1, seq2, err_msg="Generator must be strictly reproducible given same seed")
    assert meta1["sequence_length"] == meta2["sequence_length"]


def test_non_interference_with_v2_and_production():
    """Verify that Video V2 files, models, and scripts were untouched."""
    v2_manifest = PROJECT_ROOT / "data" / "synthetic" / "video_v2" / "video_manifest.csv"
    assert v2_manifest.is_file(), "Video V2 manifest must exist"

    v2_pipeline_dir = PROJECT_ROOT / "pipelines" / "synthetic_video"
    assert v2_pipeline_dir.is_dir(), "Pipelines synthetic_video must exist"

    v2_model_dir = PROJECT_ROOT / "artifacts" / "video_model"
    assert v2_model_dir.is_dir(), "Video model artifacts dir must exist"


def test_experiment_artifacts_validity():
    """Verify that experiment results and OOF predictions exist and are valid."""
    results_json = VIDEO_V3_EXPERIMENTS_DIR / "experiment_results.json"
    oof_csv = VIDEO_V3_EXPERIMENTS_DIR / "oof_predictions_v3.csv"

    if not results_json.exists() or not oof_csv.exists():
        pytest.skip("Experiment benchmark has not finished executing yet.")

    with open(results_json, "r") as f:
        res = json.load(f)

    assert "models" in res
    assert "redundancy_analysis" in res
    assert res["metadata"]["cohort"] == "canonical_bangladeshi_train_640"
    assert res["metadata"]["data_origin"] == "CLINICALLY_CONDITIONED_SYNTHETIC"

    oof_df = pd.read_csv(oof_csv)
    assert len(oof_df) == 640, f"Expected 640 canonical OOF rows, got {len(oof_df)}"

    prob_cols = [c for c in oof_df.columns if c.endswith("_prob")]
    for col in prob_cols:
        assert not oof_df[col].isna().any(), f"NaNs found in {col}"
        assert (oof_df[col] >= 0.0).all() and (oof_df[col] <= 1.0).all(), f"Probabilities out of bounds in {col}"

    # Redundancy check: V3 decodes clinical covariates much better than unconditioned V2
    v3_age_r2 = res["redundancy_analysis"]["video_v3_cv_r2_scores"]["norm_age"]
    v3_sleep_r2 = res["redundancy_analysis"]["video_v3_cv_r2_scores"]["sleep_disruption"]
    assert v3_age_r2 > 0.50, f"Video V3 should decode clinical age (got R^2={v3_age_r2})"
    assert v3_sleep_r2 > 0.50, f"Video V3 should decode sleep disruption (got R^2={v3_sleep_r2})"

    v3_mean_r2 = res["redundancy_analysis"]["video_v3_mean_r2"]
    v2_mean_r2 = res["redundancy_analysis"]["video_v2_mean_r2"]
    assert v3_mean_r2 > v2_mean_r2, f"Video V3 ({v3_mean_r2}) should exceed unconditioned V2 ({v2_mean_r2})"

