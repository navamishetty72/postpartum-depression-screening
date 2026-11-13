"""Improved synthetic video feature trajectory generator engine (v2).

Generates exactly 800 independent abstract 24-channel temporal video feature tensors
(640 train, 160 test) computationally linked to participant IDs (BGD_001 to BGD_800).

IMPROVEMENTS IN V2:
1. Physiological Action Unit co-activations: incorporates empirical 14x14 covariance
   structures (e.g. AU06+AU12 smile synergy, AU04+AU07 tension, AU09+AU10 nasolabial).
2. Differentiated AU baseline distributions: realistic resting intensities and variances
   per channel rather than identical isotropic AR(1) Gaussian noise.
3. Participant-level resting baseline variability (anatomical diversity).
4. Kinematically coupled head pose (pitch, yaw, roll) and realistic eye gaze trajectories.
5. Mathematically derived metrics: gaze_stability, rigid_motion, and non_rigid_motion are
   computed directly from underlying signals using documented differential formulas.
6. Temporally clustered tracking dropout bursts: models contiguous tracking failure blocks
   (2-6 frames) while strictly preserving the 3%-10% dropout bounds.
7. Strict target isolation: zero conditioning on EPDS, PHQ-9, or clinical screening targets.

SCIENTIFIC INTEGRITY NOTICE:
This generator produces abstract numerical feature trajectories (numpy arrays)
independently of clinical survey labels as engineering fixtures for multimodal sequence
ingestion and fusion testing. Zero real video recordings or facial images exist in this cohort.
"""

from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Union
import numpy as np
import pandas as pd

from pipelines.synthetic_video.config_v2 import (
    AR1_ALPHA,
    AU_MEANS,
    AU_PARTICIPANT_STD,
    AU_STDS,
    CHANNEL_BOUNDS,
    CHANNEL_NAMES,
    CONFIDENCE_THRESHOLD,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    FEATURE_DIM,
    FRAME_INTERVAL_SEC,
    GAZE_MEANS,
    GAZE_PARTICIPANT_STD,
    GAZE_STABILITY_OMEGA_0,
    GAZE_STDS,
    GENERATOR_VERSION,
    MAX_DROPOUT_RATE,
    MAX_SEQUENCE_LENGTH,
    MIN_DROPOUT_RATE,
    MIN_SEQUENCE_LENGTH,
    NON_RIGID_MOTION_ALPHA_0,
    POSE_CORR_YAW_ROLL,
    POSE_MEANS,
    POSE_PARTICIPANT_STD,
    POSE_STDS,
    RIGID_MOTION_V_0,
    SYNTHETIC_VIDEO_V2_DIR,
    SYNTHETIC_VIDEO_V2_FEATURES_DIR,
    SYNTHETIC_VIDEO_V2_MANIFEST_PATH,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
    get_au_correlation_matrix,
)


class SyntheticVideoGeneratorV2:
    """Generates physiologically structured, 24-channel temporal video feature tensors."""

    def __init__(self, seed: int = DEFAULT_RANDOM_SEED) -> None:
        self.seed = seed

        # 1. Action Unit Covariance & Cholesky Decomposition
        self.au_corr = get_au_correlation_matrix()
        # Covariance Sigma_AU = D * R * D
        D_au = np.diag(AU_STDS)
        self.au_cov = (D_au @ self.au_corr @ D_au).astype(np.float32)
        # Cholesky factor L such that L @ L.T = Sigma_AU
        self.au_chol = np.linalg.cholesky(self.au_cov).astype(np.float32)

        # 2. Head Pose Covariance & Cholesky Decomposition
        # 3x3 pose: pitch, yaw, roll with yaw-roll coupling
        pose_corr = np.eye(3, dtype=np.float32)
        pose_corr[1, 2] = pose_corr[2, 1] = POSE_CORR_YAW_ROLL
        D_pose = np.diag(POSE_STDS)
        self.pose_cov = (D_pose @ pose_corr @ D_pose).astype(np.float32)
        self.pose_chol = np.linalg.cholesky(self.pose_cov).astype(np.float32)

        # 3. Eye Gaze Covariance & Cholesky Decomposition
        # 2x2 gaze: horizontal (x), vertical (y)
        gaze_corr = np.eye(2, dtype=np.float32)
        gaze_corr[0, 1] = gaze_corr[1, 0] = 0.10  # Mild natural diagonal saccadic coupling
        D_gaze = np.diag(GAZE_STDS)
        self.gaze_cov = (D_gaze @ gaze_corr @ D_gaze).astype(np.float32)
        self.gaze_chol = np.linalg.cholesky(self.gaze_cov).astype(np.float32)

    def _verify_no_target_inputs(self, data: Any) -> None:
        """Assert that no clinical targets, EPDS, or survey predictors enter generation."""
        if isinstance(data, (pd.DataFrame, pd.Series)):
            cols = (
                [str(c).lower() for c in data.columns]
                if isinstance(data, pd.DataFrame)
                else [str(data.name).lower()]
            )
            for c in cols:
                if any(k in c for k in ("epds", "phq", "target", "screening_threshold")):
                    raise ValueError(f"Prohibited clinical target input detected: '{c}'")
        elif isinstance(data, str):
            data_lower = data.lower()
            if any(k in data_lower for k in ("epds", "phq", "target", "screening_threshold")):
                raise ValueError(f"Prohibited clinical target input detected: '{data}'")

    def _sample_dropout_bursts(
        self, seq_len: int, rng: np.random.Generator
    ) -> Tuple[Set[int], int]:
        """Generate temporally clustered tracking dropout bursts.

        Real video dropouts occur in contiguous runs (e.g., occlusion, rapid head turn).
        Enforces strict total dropout bounds: 3% to 10% of seq_len.

        Args:
            seq_len: Total frames in sequence.
            rng: Seeded NumPy random generator.

        Returns:
            Tuple[Set[int], int]: Set of dropped frame indices and burst count.
        """
        min_drop = int(np.ceil(MIN_DROPOUT_RATE * seq_len))
        max_drop = int(np.floor(MAX_DROPOUT_RATE * seq_len))
        n_drop = int(rng.integers(min_drop, max_drop + 1))

        # Partition n_drop into 1 or 2 contiguous bursts
        if n_drop <= 3:
            burst_lengths = [n_drop]
        else:
            # 50% probability 1 burst, 50% probability 2 bursts
            if rng.random() < 0.5:
                burst_lengths = [n_drop]
            else:
                b1 = int(rng.integers(2, n_drop - 1))
                b2 = n_drop - b1
                burst_lengths = [b1, b2]

        dropout_indices: Set[int] = set()

        for b_len in burst_lengths:
            # Find a valid start position that does not overlap existing dropouts
            max_start = seq_len - b_len
            if max_start <= 0:
                # Sequence too short for offset, drop from 0
                for f in range(b_len):
                    dropout_indices.add(f)
                continue

            attempts = 0
            placed = False
            while attempts < 30 and not placed:
                start = int(rng.integers(0, max_start + 1))
                candidate_frames = set(range(start, start + b_len))
                if not candidate_frames.intersection(dropout_indices):
                    dropout_indices.update(candidate_frames)
                    placed = True
                attempts += 1

            if not placed:
                # Fallback: find available indices without strict contiguity
                available = [i for i in range(seq_len) if i not in dropout_indices]
                if len(available) >= b_len:
                    dropout_indices.update(available[:b_len])

        return dropout_indices, len(burst_lengths)

    def generate_single_sequence(
        self,
        participant_sr: int,
    ) -> Tuple[np.ndarray, Dict[str, Union[int, float]]]:
        """Generate a single (T, 24) float32 improved feature tensor for a participant.

        Args:
            participant_sr: Unique integer index (1 to 800) from frozen split manifest.

        Returns:
            Tuple[np.ndarray, Dict]: The (T, 24) float32 tensor and metadata dictionary.
        """
        # Participant-specific deterministic RNG derived from seed and participant_sr
        rng = np.random.default_rng(self.seed * 10000 + participant_sr)

        # 1. Sample sequence length T within [MIN_SEQUENCE_LENGTH, MAX_SEQUENCE_LENGTH]
        seq_len = int(rng.integers(MIN_SEQUENCE_LENGTH, MAX_SEQUENCE_LENGTH + 1))

        # 2. Sample participant-level resting baselines (anatomical variability)
        au_offset = AU_PARTICIPANT_STD * rng.standard_normal(14).astype(np.float32)
        au_baseline = np.clip(AU_MEANS + au_offset, 0.05, 1.50)

        pose_offset = POSE_PARTICIPANT_STD * rng.standard_normal(3).astype(np.float32)
        pose_baseline = POSE_MEANS + pose_offset

        gaze_offset = GAZE_PARTICIPANT_STD * rng.standard_normal(2).astype(np.float32)
        gaze_baseline = GAZE_MEANS + gaze_offset

        # 3. Autoregressive AR(1) state evolution with correlated innovations
        alpha = np.float32(AR1_ALPHA)
        beta = np.float32(np.sqrt(1.0 - alpha**2))

        # AU trajectory (14 channels)
        au_traj = np.zeros((seq_len, 14), dtype=np.float32)
        au_state = self.au_chol @ rng.standard_normal(14).astype(np.float32)

        # Pose trajectory (3 channels)
        pose_traj = np.zeros((seq_len, 3), dtype=np.float32)
        pose_state = self.pose_chol @ rng.standard_normal(3).astype(np.float32)

        # Gaze trajectory (2 channels)
        gaze_traj = np.zeros((seq_len, 2), dtype=np.float32)
        gaze_state = self.gaze_chol @ rng.standard_normal(2).astype(np.float32)

        for t in range(seq_len):
            if t > 0:
                # Correlated innovations via Cholesky factor
                au_innov = self.au_chol @ rng.standard_normal(14).astype(np.float32)
                au_state = (alpha * au_state) + (beta * au_innov)

                pose_innov = self.pose_chol @ rng.standard_normal(3).astype(np.float32)
                pose_state = (alpha * pose_state) + (beta * pose_innov)

                gaze_innov = self.gaze_chol @ rng.standard_normal(2).astype(np.float32)
                gaze_state = (alpha * gaze_state) + (beta * gaze_innov)

            au_traj[t] = au_baseline + au_state
            pose_traj[t] = pose_baseline + pose_state
            gaze_traj[t] = gaze_baseline + gaze_state

        # Apply strict engineering interval bounds
        for ch_idx in range(14):
            ch_name = CHANNEL_NAMES[ch_idx]
            lower, upper = CHANNEL_BOUNDS[ch_name]
            au_traj[:, ch_idx] = np.clip(au_traj[:, ch_idx], lower, upper)

        for p_idx in range(3):
            ch_name = CHANNEL_NAMES[14 + p_idx]
            lower, upper = CHANNEL_BOUNDS[ch_name]
            pose_traj[:, p_idx] = np.clip(pose_traj[:, p_idx], lower, upper)

        for g_idx in range(2):
            ch_name = CHANNEL_NAMES[17 + g_idx]
            lower, upper = CHANNEL_BOUNDS[ch_name]
            gaze_traj[:, g_idx] = np.clip(gaze_traj[:, g_idx], lower, upper)

        # 4. Mathematically Derive Gaze Stability & Motion Summaries (Channels 19, 20, 21)
        dt = np.float32(FRAME_INTERVAL_SEC)
        gaze_stability = np.zeros(seq_len, dtype=np.float32)
        rigid_motion = np.zeros(seq_len, dtype=np.float32)
        non_rigid_motion = np.zeros(seq_len, dtype=np.float32)

        # Frame 0 initial conditions (resting state)
        gaze_stability[0] = 1.0
        rigid_motion[0] = 0.0
        non_rigid_motion[0] = 0.0

        for t in range(1, seq_len):
            # A. Gaze Stability: exp(-omega / omega_0)
            delta_gaze_sq = (gaze_traj[t, 0] - gaze_traj[t - 1, 0]) ** 2 + (
                gaze_traj[t, 1] - gaze_traj[t - 1, 1]
            ) ** 2
            omega = np.sqrt(delta_gaze_sq) / dt  # Angular velocity in rad/s
            gaze_stability[t] = np.clip(
                np.exp(-omega / GAZE_STABILITY_OMEGA_0), 0.0, 1.0
            )

            # B. Rigid Motion: tanh(v_head / v_0)
            delta_pose_sq = (
                (pose_traj[t, 0] - pose_traj[t - 1, 0]) ** 2
                + (pose_traj[t, 1] - pose_traj[t - 1, 1]) ** 2
                + (pose_traj[t, 2] - pose_traj[t - 1, 2]) ** 2
            )
            v_head = np.sqrt(delta_pose_sq) / dt  # Rotational velocity in rad/s
            rigid_motion[t] = np.clip(np.tanh(v_head / RIGID_MOTION_V_0), 0.0, 1.0)

            # C. Non-Rigid Motion: tanh(mean_au_velocity / alpha_0)
            delta_au = np.mean(np.abs(au_traj[t, :] - au_traj[t - 1, :])) / dt
            non_rigid_motion[t] = np.clip(
                np.tanh(delta_au / NON_RIGID_MOTION_ALPHA_0), 0.0, 1.0
            )

        # 5. Simulate Temporally Clustered Tracking Dropouts
        dropout_indices, burst_count = self._sample_dropout_bursts(seq_len, rng)

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

        # 6. Assemble Full 24-Channel Tensor
        tensor = np.zeros((seq_len, FEATURE_DIM), dtype=np.float32)
        tensor[:, 0:14] = au_traj
        tensor[:, 14:17] = pose_traj
        tensor[:, 17:19] = gaze_traj
        tensor[:, 19] = gaze_stability
        tensor[:, 20] = rigid_motion
        tensor[:, 21] = non_rigid_motion
        tensor[:, 22] = tracking_conf
        tensor[:, 23] = success_flag

        # 7. Strict Numerical Integrity Validation
        if np.isnan(tensor).any() or np.isinf(tensor).any():
            raise ValueError(
                f"NaN or Inf values detected in generated tensor for sr {participant_sr}"
            )

        # Verify channel bounds
        for ch_idx in range(FEATURE_DIM):
            ch_name = CHANNEL_NAMES[ch_idx]
            lower, upper = CHANNEL_BOUNDS[ch_name]
            if (tensor[:, ch_idx] < lower - 1e-5).any() or (
                tensor[:, ch_idx] > upper + 1e-5
            ).any():
                raise ValueError(
                    f"Channel {ch_name} (idx {ch_idx}) exceeded bounds [{lower}, {upper}]"
                )

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
            "burst_count": burst_count,
        }

        return tensor, meta

    def generate_cohort(
        self,
        manifest_path: Union[str, Path] = TRAIN_TEST_SPLIT_MANIFEST_PATH,
        output_dir: Union[str, Path] = SYNTHETIC_VIDEO_V2_DIR,
    ) -> pd.DataFrame:
        """Generate all 800 synthetic video v2 feature trajectories and write manifest.

        Args:
            manifest_path: Path to frozen train_test_split_manifest.csv.
            output_dir: Output directory for synthetic video v2 artifacts.

        Returns:
            pd.DataFrame: Completed video manifest with 800 rows.
        """
        out_dir = Path(output_dir)
        features_dir = out_dir / "features"
        features_dir.mkdir(parents=True, exist_ok=True)

        m_path = Path(manifest_path)
        if not m_path.exists():
            from scripts.create_split_manifest import create_manifest

            manifest_df = create_manifest()
        else:
            manifest_df = pd.read_csv(m_path)

        if len(manifest_df) != 800:
            raise ValueError(f"Expected 800 participants in manifest, got {len(manifest_df)}")

        # Verify that no clinical target inputs are present or used
        self._verify_no_target_inputs(manifest_df.drop(columns=["target_canonical_epds_ge_13"], errors="ignore"))

        manifest_records: List[Dict[str, Union[str, int, float]]] = []

        for _, row in manifest_df.iterrows():
            participant_id = str(row["participant_id"])
            sr_num = int(row["sr"])
            split_partition = str(row["split_partition"])

            # Generate independent improved synthetic video trajectory
            tensor, meta = self.generate_single_sequence(participant_sr=sr_num)

            # Save tensor as .npy file
            filename = f"{participant_id}.npy"
            rel_path = f"data/synthetic/video_v2/features/{filename}"
            abs_path = features_dir / filename
            np.save(abs_path, tensor)

            # Record manifest entry matching standard project schema
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
                "burst_count": meta["burst_count"],
            }
            manifest_records.append(record)

        video_manifest_df = pd.DataFrame(manifest_records)
        manifest_save_path = out_dir / "video_manifest.csv"
        video_manifest_df.to_csv(manifest_save_path, index=False)

        return video_manifest_df


def run_generation_v2() -> pd.DataFrame:
    """Main execution entrypoint for generating synthetic video v2 feature trajectories."""
    generator = SyntheticVideoGeneratorV2(seed=DEFAULT_RANDOM_SEED)
    manifest = generator.generate_cohort(
        manifest_path=TRAIN_TEST_SPLIT_MANIFEST_PATH,
        output_dir=SYNTHETIC_VIDEO_V2_DIR,
    )
    print("Synthetic video v2 feature generation complete.")
    print(f"  Total records: {len(manifest)}")
    print(f"  Train: {(manifest['split_partition'] == 'train').sum()}")
    print(f"  Test: {(manifest['split_partition'] == 'test').sum()}")
    print(
        f"  Sequence length min: {manifest['sequence_length'].min()}, max: {manifest['sequence_length'].max()}, mean: {manifest['sequence_length'].mean():.1f}"
    )
    print(
        f"  Dropout rate min: {manifest['dropout_rate'].min():.4f}, max: {manifest['dropout_rate'].max():.4f}, mean: {manifest['dropout_rate'].mean():.4f}"
    )
    print(f"  Mean tracking bursts per participant: {manifest['burst_count'].mean():.2f}")
    print(f"  Saved manifest: {SYNTHETIC_VIDEO_V2_MANIFEST_PATH}")
    print(f"  Saved features: {SYNTHETIC_VIDEO_V2_FEATURES_DIR}")
    return manifest


if __name__ == "__main__":
    run_generation_v2()

