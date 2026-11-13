"""Synthetic video feature trajectory generator engine.

Generates exactly 800 independent abstract 24-channel temporal video feature tensors
(640 train, 160 test) computationally linked to participant IDs (BGD_001 to BGD_800).

SCIENTIFIC INTEGRITY NOTICE:
This generator produces abstract numerical feature trajectories (numpy arrays)
independently of clinical survey labels as engineering fixtures for multimodal sequence
ingestion and fusion testing. Zero real video recordings or facial images exist in this cohort.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple, Union
import numpy as np
import pandas as pd

from pipelines.synthetic_video.config import (
    AR1_ALPHA,
    CHANNEL_BOUNDS,
    CHANNEL_NAMES,
    CONFIDENCE_THRESHOLD,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    FEATURE_DIM,
    GENERATOR_VERSION,
    MAX_DROPOUT_RATE,
    MAX_SEQUENCE_LENGTH,
    MIN_DROPOUT_RATE,
    MIN_SEQUENCE_LENGTH,
    SYNTHETIC_VIDEO_DIR,
    SYNTHETIC_VIDEO_FEATURES_DIR,
    SYNTHETIC_VIDEO_MANIFEST_PATH,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
)


class SyntheticVideoGenerator:
    """Generates independent, abstract 24-channel temporal video feature tensors."""

    def __init__(self, seed: int = DEFAULT_RANDOM_SEED) -> None:
        self.seed = seed

        # Baseline empirical center values for 22 physical channels (engineering priors)
        # Channels 0-13 (AUs): low resting intensity ~0.30-0.45
        # Channels 14-16 (Pose): neutral orientation ~0.0 rad
        # Channels 17-18 (Gaze angles): centered ~0.0 rad
        # Channel 19 (Gaze stability): high stability ~0.88
        # Channels 20-21 (Motion): low-to-moderate motion ~0.22
        self.base_means = np.zeros(22, dtype=np.float32)
        self.base_means[0:14] = 0.35  # AUs
        self.base_means[14:17] = 0.00  # Pose
        self.base_means[17:19] = 0.00  # Gaze angles
        self.base_means[19] = 0.88     # Gaze stability
        self.base_means[20:22] = 0.22  # Motion summaries

        # Standard deviations for residual variation across time
        self.base_stds = np.zeros(22, dtype=np.float32)
        self.base_stds[0:14] = 0.35   # AUs
        self.base_stds[14:17] = 0.15  # Pose
        self.base_stds[17:19] = 0.10  # Gaze angles
        self.base_stds[19] = 0.06     # Gaze stability
        self.base_stds[20:22] = 0.08  # Motion summaries

    def _verify_no_target_inputs(self, data: Any) -> None:
        """Assert that no clinical targets, EPDS, or survey predictors enter generation."""
        if isinstance(data, (pd.DataFrame, pd.Series)):
            cols = [str(c).lower() for c in data.columns] if isinstance(data, pd.DataFrame) else [str(data.name).lower()]
            for c in cols:
                if "epds" in c or "phq" in c or "target" in c:
                    raise ValueError(f"Prohibited clinical target input detected: '{c}'")
        elif isinstance(data, str):
            data_lower = data.lower()
            if "epds" in data_lower or "phq" in data_lower or "target" in data_lower:
                raise ValueError(f"Prohibited clinical target input detected: '{data}'")

    def generate_single_sequence(
        self,
        participant_sr: int,
    ) -> Tuple[np.ndarray, Dict[str, Union[int, float]]]:
        """Generate a single (T, 24) float32 abstract feature tensor for a participant.

        Args:
            participant_sr: Unique integer index (1 to 800) from frozen split manifest.

        Returns:
            Tuple[np.ndarray, Dict]: The (T, 24) float32 tensor and metadata dictionary.
        """
        # Participant-specific deterministic RNG derived from seed and participant_sr
        rng = np.random.default_rng(self.seed * 10000 + participant_sr)

        # 1. Sample sequence length T within [MIN_SEQUENCE_LENGTH, MAX_SEQUENCE_LENGTH]
        seq_len = int(rng.integers(MIN_SEQUENCE_LENGTH, MAX_SEQUENCE_LENGTH + 1))

        # 2. Generate 22 continuous channels via AR(1) process with alpha = 0.88
        alpha = np.float32(AR1_ALPHA)
        beta = np.float32(np.sqrt(1.0 - alpha**2))

        raw_traj = np.zeros((seq_len, 22), dtype=np.float32)
        curr_state = rng.standard_normal(22).astype(np.float32)

        for t in range(seq_len):
            if t > 0:
                innov = rng.standard_normal(22).astype(np.float32)
                curr_state = (alpha * curr_state) + (beta * innov)
            raw_traj[t] = self.base_means + (self.base_stds * curr_state)

        # 3. Apply channel boundaries
        for ch_idx in range(22):
            ch_name = CHANNEL_NAMES[ch_idx]
            lower, upper = CHANNEL_BOUNDS[ch_name]
            raw_traj[:, ch_idx] = np.clip(raw_traj[:, ch_idx], lower, upper)

        # 4. Simulate tracking dropouts (strictly 3% to 10% of frames per participant)
        min_drop = int(np.ceil(MIN_DROPOUT_RATE * seq_len))
        max_drop = int(np.floor(MAX_DROPOUT_RATE * seq_len))
        n_drop = int(rng.integers(min_drop, max_drop + 1))

        dropout_indices = set(rng.choice(seq_len, size=n_drop, replace=False))

        tracking_conf = np.zeros(seq_len, dtype=np.float32)
        success_flag = np.zeros(seq_len, dtype=np.float32)

        for t in range(seq_len):
            if t in dropout_indices:
                # Failed tracking frame: success = 0.0, confidence < 0.60
                success_flag[t] = 0.0
                tracking_conf[t] = float(rng.uniform(0.10, 0.55))
            else:
                # Successful tracking frame: success = 1.0, confidence >= 0.75
                success_flag[t] = 1.0
                tracking_conf[t] = float(rng.uniform(0.75, 0.99))

        # 5. Assemble full 24-channel tensor
        tensor = np.zeros((seq_len, FEATURE_DIM), dtype=np.float32)
        tensor[:, :22] = raw_traj
        tensor[:, 22] = tracking_conf
        tensor[:, 23] = success_flag

        # 6. Strict validation of tensor properties
        if np.isnan(tensor).any() or np.isinf(tensor).any():
            raise ValueError(f"NaN or Inf values detected in generated tensor for sr {participant_sr}")

        # Compute metadata metrics
        actual_missing_frames = int((success_flag == 0.0).sum())
        mean_conf = float(tracking_conf.mean())
        actual_dropout_rate = float(actual_missing_frames / seq_len)

        meta: Dict[str, Union[int, float]] = {
            "sequence_length": seq_len,
            "feature_dimension": FEATURE_DIM,
            "missing_frame_count": actual_missing_frames,
            "mean_tracking_confidence": round(mean_conf, 4),
            "dropout_rate": round(actual_dropout_rate, 4),
        }

        return tensor, meta

    def generate_cohort(
        self,
        manifest_path: Union[str, Path] = TRAIN_TEST_SPLIT_MANIFEST_PATH,
        output_dir: Union[str, Path] = SYNTHETIC_VIDEO_DIR,
    ) -> pd.DataFrame:
        """Generate all 800 synthetic video feature trajectories and write manifest.

        Args:
            manifest_path: Path to frozen train_test_split_manifest.csv.
            output_dir: Output directory for synthetic video artifacts.

        Returns:
            pd.DataFrame: Completed video manifest with 800 rows.
        """
        out_dir = Path(output_dir)
        features_dir = out_dir / "features"
        features_dir.mkdir(parents=True, exist_ok=True)

        manifest_df = pd.read_csv(manifest_path)
        if len(manifest_df) != 800:
            raise ValueError(f"Expected 800 participants in manifest, got {len(manifest_df)}")

        manifest_records: List[Dict[str, Union[str, int, float]]] = []

        for _, row in manifest_df.iterrows():
            participant_id = str(row["participant_id"])
            sr_num = int(row["sr"])
            split_partition = str(row["split_partition"])

            # Generate independent synthetic video trajectory
            tensor, meta = self.generate_single_sequence(participant_sr=sr_num)

            # Save tensor as .npy file
            filename = f"{participant_id}.npy"
            rel_path = f"data/synthetic/video/features/{filename}"
            abs_path = features_dir / filename
            np.save(abs_path, tensor)

            # Record manifest entry
            record: Dict[str, Union[str, int, float]] = {
                "participant_id": participant_id,
                "split_partition": split_partition,
                "data_origin": DATA_ORIGIN_TAG,
                "generator_version": GENERATOR_VERSION,
                "random_seed": self.seed,
                "feature_file_path": rel_path,
                "sequence_length": meta["sequence_length"],
                "feature_dimension": meta["feature_dimension"],
                "dtype": "float32",
                "missing_frame_count": meta["missing_frame_count"],
                "mean_tracking_confidence": meta["mean_tracking_confidence"],
                "dropout_rate": meta["dropout_rate"],
            }
            manifest_records.append(record)

        video_manifest_df = pd.DataFrame(manifest_records)
        manifest_save_path = out_dir / "video_manifest.csv"
        video_manifest_df.to_csv(manifest_save_path, index=False)

        return video_manifest_df


def run_generation() -> pd.DataFrame:
    """Main execution entrypoint for generating synthetic video feature trajectories."""
    generator = SyntheticVideoGenerator(seed=DEFAULT_RANDOM_SEED)
    manifest = generator.generate_cohort(
        manifest_path=TRAIN_TEST_SPLIT_MANIFEST_PATH,
        output_dir=SYNTHETIC_VIDEO_DIR,
    )
    print("Synthetic video feature generation complete.")
    print(f"  Total records: {len(manifest)}")
    print(f"  Train: {(manifest['split_partition'] == 'train').sum()}")
    print(f"  Test: {(manifest['split_partition'] == 'test').sum()}")
    print(f"  Sequence length min: {manifest['sequence_length'].min()}, max: {manifest['sequence_length'].max()}, mean: {manifest['sequence_length'].mean():.1f}")
    print(f"  Dropout rate min: {manifest['dropout_rate'].min():.4f}, max: {manifest['dropout_rate'].max():.4f}, mean: {manifest['dropout_rate'].mean():.4f}")
    print(f"  Saved manifest: {SYNTHETIC_VIDEO_MANIFEST_PATH}")
    print(f"  Saved features: {SYNTHETIC_VIDEO_FEATURES_DIR}")
    return manifest


if __name__ == "__main__":
    run_generation()
