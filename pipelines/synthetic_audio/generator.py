"""Synthetic audio generator engine for multimodal PPD screening benchmark.

Generates 800 synthetic audio feature profiles (640 train, 160 test) computationally
linked to clinical participant IDs (BGD_001 to BGD_800).

SCIENTIFIC INTEGRITY NOTICE:
This generator produces synthetic engineering fixtures for architectural integration
benchmarking only. No real acoustic recordings exist for this cohort.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from pipelines.synthetic_audio.config import (
    ACOUSTIC_CORRELATION_MATRIX,
    ACOUSTIC_FEATURE_BOUNDS,
    ACOUSTIC_FEATURE_NAMES,
    ACOUSTIC_FEATURE_STDS,
    AR1_NOISE_SCALE,
    AR1_SMOOTHING_ALPHA,
    BASELINE_ACOUSTIC_MEANS,
    CLINICAL_SHIFT_WEIGHTS,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    EMBEDDING_DIM,
    EMBEDDING_PROJECTION_SCALE,
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


class SyntheticAudioGenerator:
    """Generates correlated acoustic summary scalars and temporal embedding fixtures."""

    def __init__(self, seed: int = DEFAULT_RANDOM_SEED) -> None:
        self.seed = seed

        # Build baseline mean vector mu_0 (shape: [7])
        self.baseline_means = np.array(
            [BASELINE_ACOUSTIC_MEANS[name] for name in ACOUSTIC_FEATURE_NAMES],
            dtype=np.float64,
        )

        # Build standard deviation vector sigma (shape: [7])
        self.feature_stds = np.array(
            [ACOUSTIC_FEATURE_STDS[name] for name in ACOUSTIC_FEATURE_NAMES],
            dtype=np.float64,
        )

        # Build covariance matrix Sigma = D * R * D
        d_mat = np.diag(self.feature_stds)
        self.cov_matrix = d_mat @ ACOUSTIC_CORRELATION_MATRIX @ d_mat

        # Cholesky decomposition L such that L @ L.T = Sigma
        self.cholesky_l = np.linalg.cholesky(self.cov_matrix)

        # Feature bounds as array of (lower, upper)
        self.bounds = [ACOUSTIC_FEATURE_BOUNDS[name] for name in ACOUSTIC_FEATURE_NAMES]

        # Shift weights W (shape: [num_covariates=5, num_features=7])
        self.shift_weights = CLINICAL_SHIFT_WEIGHTS

        # Fixed deterministic projection matrix for 7 acoustic features -> 128 embedding dim
        proj_rng = np.random.default_rng(seed + 9999)
        raw_proj = proj_rng.standard_normal((len(ACOUSTIC_FEATURE_NAMES), EMBEDDING_DIM))
        # Normalize columns so variance is controlled
        self.projection_matrix = (raw_proj / np.sqrt(len(ACOUSTIC_FEATURE_NAMES))).astype(
            np.float32
        )

    def generate_summary_features(
        self,
        covariate_vector: np.ndarray,
        rng: np.random.Generator,
    ) -> Dict[str, float]:
        """Generate 7 physiological acoustic summary features for a single participant.

        Args:
            covariate_vector: Normalized clinical conditioning vector of shape (5,).
            rng: Random generator specific to the participant.

        Returns:
            Dict[str, float]: Clamped acoustic features.
        """
        # Linear conditional mean shift: mu_i = mu_0 + x_i @ W
        conditional_mean = self.baseline_means + (covariate_vector @ self.shift_weights)

        # Correlated residual sample: epsilon = L @ z, z ~ N(0, I)
        z = rng.standard_normal(len(ACOUSTIC_FEATURE_NAMES))
        residual = self.cholesky_l @ z

        unclamped = conditional_mean + residual

        # Apply hard physiological bounds
        clamped_features: Dict[str, float] = {}
        for idx, name in enumerate(ACOUSTIC_FEATURE_NAMES):
            lower, upper = self.bounds[idx]
            val = float(np.clip(unclamped[idx], lower, upper))
            clamped_features[name] = round(val, 4)

        return clamped_features

    def generate_temporal_embedding(
        self,
        summary_features: Dict[str, float],
        sequence_length: int,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """Generate abstract (T, 128) float32 embedding tensor via AR(1) walk.

        Args:
            summary_features: The 7 acoustic summary features.
            sequence_length: Number of time frames T (between MIN and MAX sequence length).
            rng: Random generator specific to the participant.

        Returns:
            np.ndarray: Array of shape (sequence_length, 128) and dtype float32.
        """
        if not (MIN_SEQUENCE_LENGTH <= sequence_length <= MAX_SEQUENCE_LENGTH):
            raise ValueError(
                f"sequence_length {sequence_length} outside range "
                f"[{MIN_SEQUENCE_LENGTH}, {MAX_SEQUENCE_LENGTH}]"
            )

        # 1. Standardize summary features relative to baseline prior
        feature_vals = np.array(
            [summary_features[name] for name in ACOUSTIC_FEATURE_NAMES],
            dtype=np.float32,
        )
        norm_summary = (feature_vals - self.baseline_means.astype(np.float32)) / (
            self.feature_stds.astype(np.float32)
        )

        # 2. Project into 128-dimensional latent space
        base_h = (norm_summary @ self.projection_matrix) * EMBEDDING_PROJECTION_SCALE

        # 3. Simulate AR(1) temporal walk across sequence frames
        noise_innovations = rng.standard_normal((sequence_length, EMBEDDING_DIM)).astype(
            np.float32
        )
        embeddings = np.zeros((sequence_length, EMBEDDING_DIM), dtype=np.float32)

        ar_state = noise_innovations[0].copy()
        alpha = AR1_SMOOTHING_ALPHA
        beta = float(np.sqrt(1.0 - alpha**2))

        for t in range(sequence_length):
            if t > 0:
                ar_state = (alpha * ar_state) + (beta * noise_innovations[t])
            # Combine static acoustic projection with dynamic AR(1) state
            frame_vec = base_h + (AR1_NOISE_SCALE * ar_state)
            embeddings[t] = frame_vec

        # Validate tensor integrity
        if np.isnan(embeddings).any() or np.isinf(embeddings).any():
            raise ValueError("NaN or Inf detected in generated temporal embedding tensor.")

        return embeddings

    def generate_cohort(
        self,
        manifest_path: Union[str, Path] = TRAIN_TEST_SPLIT_MANIFEST_PATH,
        modeling_matrix_path: Union[str, Path] = MODELING_MATRIX_PATH,
        output_dir: Union[str, Path] = SYNTHETIC_AUDIO_DIR,
    ) -> pd.DataFrame:
        """Generates all 800 synthetic audio feature profiles and saving artifacts.

        Args:
            manifest_path: Path to train_test_split_manifest.csv.
            modeling_matrix_path: Path to ppd_modeling_matrix.csv.
            output_dir: Path to directory where synthetic audio data will be saved.

        Returns:
            pd.DataFrame: Completed audio manifest with 800 rows.
        """
        out_dir = Path(output_dir)
        features_dir = out_dir / "features"
        features_dir.mkdir(parents=True, exist_ok=True)

        manifest_df = pd.read_csv(manifest_path)
        modeling_matrix_df = pd.read_csv(modeling_matrix_path)

        if len(manifest_df) != 800:
            raise ValueError(f"Expected 800 participants in manifest, got {len(manifest_df)}")

        # Extract normalized conditioning covariates (fitted ONLY on train)
        conditioning_df = extract_cohort_conditioning(manifest_df, modeling_matrix_df)

        manifest_records: List[Dict[str, Union[str, int, float]]] = []

        for idx, row in manifest_df.iterrows():
            participant_id = str(row["participant_id"])
            sr_num = int(row["sr"])
            split_partition = str(row["split_partition"])

            # Participant-specific deterministic RNG derived from base seed and participant sr
            rng_p = np.random.default_rng(self.seed * 10000 + sr_num)

            # Sample sequence length T_i within approved range
            seq_len = int(rng_p.integers(MIN_SEQUENCE_LENGTH, MAX_SEQUENCE_LENGTH + 1))

            # Retrieve conditioning vector (5 covariates)
            cov_vec = conditioning_df.iloc[idx].values.astype(np.float64)

            # Generate 7 acoustic summary scalars
            summary_features = self.generate_summary_features(cov_vec, rng_p)

            # Generate (T, 128) float32 temporal embedding tensor
            embedding_tensor = self.generate_temporal_embedding(
                summary_features, seq_len, rng_p
            )

            # Save tensor as .npy file
            tensor_filename = f"{participant_id}.npy"
            tensor_rel_path = f"data/synthetic/audio/features/{tensor_filename}"
            tensor_abs_path = features_dir / tensor_filename
            np.save(tensor_abs_path, embedding_tensor)

            # Build record dictionary
            record: Dict[str, Union[str, int, float]] = {
                "participant_id": participant_id,
                "split_partition": split_partition,
            }
            # Add all 7 acoustic summary features
            for feat_name in ACOUSTIC_FEATURE_NAMES:
                record[feat_name] = summary_features[feat_name]

            record["sequence_length"] = seq_len
            record["embedding_path"] = tensor_rel_path
            record["data_origin"] = DATA_ORIGIN_TAG
            record["generation_seed"] = self.seed

            manifest_records.append(record)

        audio_manifest_df = pd.DataFrame(manifest_records)
        manifest_save_path = out_dir / "audio_manifest.csv"
        audio_manifest_df.to_csv(manifest_save_path, index=False)

        return audio_manifest_df


def run_generation() -> pd.DataFrame:
    """Main entrypoint for generating the complete synthetic audio dataset."""
    generator = SyntheticAudioGenerator(seed=DEFAULT_RANDOM_SEED)
    manifest = generator.generate_cohort(
        manifest_path=TRAIN_TEST_SPLIT_MANIFEST_PATH,
        modeling_matrix_path=MODELING_MATRIX_PATH,
        output_dir=SYNTHETIC_AUDIO_DIR,
    )
    print(f"Synthetic audio generation complete.")
    print(f"  Total records: {len(manifest)}")
    print(f"  Train: {(manifest['split_partition'] == 'train').sum()}")
    print(f"  Test: {(manifest['split_partition'] == 'test').sum()}")
    print(f"  Saved manifest: {SYNTHETIC_AUDIO_MANIFEST_PATH}")
    print(f"  Saved features: {SYNTHETIC_AUDIO_FEATURES_DIR}")
    return manifest


if __name__ == "__main__":
    run_generation()

