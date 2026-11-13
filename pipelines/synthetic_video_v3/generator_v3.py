"""Video V3 synthetic facial feature trajectory generator engine.

Generates 800 participant-aligned 24-channel temporal video feature tensors
(640 train, 160 test) conditioned on non-target clinical covariates from
the canonical Bangladeshi cohort.

SCIENTIFIC INTEGRITY NOTICE:
This generator produces synthetic engineering fixtures for multimodal integration
testing during the Moment AI hackathon. The cohort contains ZERO physical video
recordings. Simulated features are conditioned on non-target survey covariates
(sleep, affect, support, anxiety) and do NOT represent genuine optical observations
or validated depression biomarkers.
"""

from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Union
import numpy as np
import pandas as pd

from pipelines.synthetic_video_v3.config_v3 import (
    AR1_ALPHA,
    AU_MEANS,
    AU_PARTICIPANT_STD,
    AU_STDS,
    CHANNEL_BOUNDS,
    CHANNEL_NAMES,
    CLINICAL_SHIFT_WEIGHTS_VIDEO,
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
    MODELING_MATRIX_PATH,
    NON_RIGID_MOTION_ALPHA_0,
    POSE_CORR_YAW_ROLL,
    POSE_MEANS,
    POSE_PARTICIPANT_STD,
    POSE_STDS,
    RIGID_MOTION_V_0,
    SYNTHETIC_VIDEO_V3_DIR,
    SYNTHETIC_VIDEO_V3_FEATURES_DIR,
    SYNTHETIC_VIDEO_V3_MANIFEST_PATH,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
    get_au_correlation_matrix,
)
from pipelines.synthetic_video_v3.conditioning import extract_cohort_conditioning_v3


class SyntheticVideoGeneratorV3:
    """Generates clinically conditioned 24-channel temporal video feature tensors."""

    def __init__(self, seed: int = DEFAULT_RANDOM_SEED) -> None:
        self.seed = seed

        # 1. Action Unit Covariance & Cholesky Decomposition
        self.au_corr = get_au_correlation_matrix()
        D_au = np.diag(AU_STDS)
        self.au_cov = (D_au @ self.au_corr @ D_au).astype(np.float32)
        self.au_chol = np.linalg.cholesky(self.au_cov).astype(np.float32)

        # 2. Head Pose Covariance & Cholesky Decomposition
        pose_corr = np.eye(3, dtype=np.float32)
        pose_corr[1, 2] = pose_corr[2, 1] = POSE_CORR_YAW_ROLL
        D_pose = np.diag(POSE_STDS)
        self.pose_cov = (D_pose @ pose_corr @ D_pose).astype(np.float32)
        self.pose_chol = np.linalg.cholesky(self.pose_cov).astype(np.float32)

        # 3. Eye Gaze Covariance & Cholesky Decomposition
        gaze_corr = np.eye(2, dtype=np.float32)
        gaze_corr[0, 1] = gaze_corr[1, 0] = 0.10
        D_gaze = np.diag(GAZE_STDS)
        self.gaze_cov = (D_gaze @ gaze_corr @ D_gaze).astype(np.float32)
        self.gaze_chol = np.linalg.cholesky(self.gaze_cov).astype(np.float32)

        # 4. Clinical shift weights
        self.shift_weights = CLINICAL_SHIFT_WEIGHTS_VIDEO

    def _sample_dropout_bursts(
        self, seq_len: int, rng: np.random.Generator
    ) -> Tuple[Set[int], int]:
        """Generate temporally clustered tracking dropout bursts."""
        min_drop = int(np.ceil(MIN_DROPOUT_RATE * seq_len))
        max_drop = int(np.floor(MAX_DROPOUT_RATE * seq_len))
        n_drop = int(rng.integers(min_drop, max_drop + 1))

        if n_drop <= 3:
            burst_lengths = [n_drop]
        else:
            if rng.random() < 0.5:
                burst_lengths = [n_drop]
            else:
                b1 = int(rng.integers(2, n_drop - 1))
                b2 = n_drop - b1
                burst_lengths = [b1, b2]

        dropout_indices: Set[int] = set()

        for b_len in burst_lengths:
            max_start = seq_len - b_len
            if max_start <= 0:
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
                available = [i for i in range(seq_len) if i not in dropout_indices]
                if len(available) >= b_len:
                    dropout_indices.update(available[:b_len])

        return dropout_indices, len(burst_lengths)

    def generate_single_sequence(
        self,
        participant_sr: int,
        covariate_vector: np.ndarray,
    ) -> Tuple[np.ndarray, Dict[str, Union[int, float]]]:
        """Generate a single (T, 24) float32 feature tensor conditioned on non-target covariates.

        Args:
            participant_sr: Unique integer index (1 to 800) from frozen split manifest.
            covariate_vector: Normalized clinical conditioning vector of shape (5,).

        Returns:
            Tuple[np.ndarray, Dict]: The (T, 24) float32 tensor and metadata dictionary.
        """
        rng = np.random.default_rng(self.seed * 10000 + participant_sr)

        # 1. Sample sequence length T within [MIN_SEQUENCE_LENGTH, MAX_SEQUENCE_LENGTH]
        seq_len = int(rng.integers(MIN_SEQUENCE_LENGTH, MAX_SEQUENCE_LENGTH + 1))

        # 2. Compute linear clinical covariate shift vector: delta = x_i @ W (shape: [24])
        shift_delta = (covariate_vector @ self.shift_weights).astype(np.float32)

        # 3. Sample participant-level resting baselines (with anatomical offset + clinical shift)
        au_offset = AU_PARTICIPANT_STD * rng.standard_normal(14).astype(np.float32)
        au_baseline = np.clip(AU_MEANS + au_offset + shift_delta[0:14], 0.05, 1.50)

        pose_offset = POSE_PARTICIPANT_STD * rng.standard_normal(3).astype(np.float32)
        pose_baseline = POSE_MEANS + pose_offset + shift_delta[14:17]

        gaze_offset = GAZE_PARTICIPANT_STD * rng.standard_normal(2).astype(np.float32)
        gaze_baseline = GAZE_MEANS + gaze_offset + shift_delta[17:19]

        # 4. Autoregressive AR(1) state evolution with correlated innovations
        alpha = np.float32(AR1_ALPHA)
        beta = np.float32(np.sqrt(1.0 - alpha**2))

        au_traj = np.zeros((seq_len, 14), dtype=np.float32)
        au_state = self.au_chol @ rng.standard_normal(14).astype(np.float32)

        pose_traj = np.zeros((seq_len, 3), dtype=np.float32)
        pose_state = self.pose_chol @ rng.standard_normal(3).astype(np.float32)

        gaze_traj = np.zeros((seq_len, 2), dtype=np.float32)
        gaze_state = self.gaze_chol @ rng.standard_normal(2).astype(np.float32)

        for t in range(seq_len):
            if t > 0:
                au_innov = self.au_chol @ rng.standard_normal(14).astype(np.float32)
                au_state = (alpha * au_state) + (beta * au_innov)

                pose_innov = self.pose_chol @ rng.standard_normal(3).astype(np.float32)
                pose_state = (alpha * pose_state) + (beta * pose_innov)

                gaze_innov = self.gaze_chol @ rng.standard_normal(2).astype(np.float32)
                gaze_state = (alpha * gaze_state) + (beta * gaze_innov)

            au_traj[t] = au_baseline + au_state
            pose_traj[t] = pose_baseline + pose_state
            gaze_traj[t] = gaze_baseline + gaze_state

        # Apply strict physical bounds
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

        # 5. Mathematically derive gaze stability and motion metrics
        dt = np.float32(FRAME_INTERVAL_SEC)
        gaze_stability = np.zeros(seq_len, dtype=np.float32)
        rigid_motion = np.zeros(seq_len, dtype=np.float32)
        non_rigid_motion = np.zeros(seq_len, dtype=np.float32)

        gaze_stability[0] = np.clip(1.0 + shift_delta[19], 0.0, 1.0)
        rigid_motion[0] = 0.0
        non_rigid_motion[0] = 0.0

        for t in range(1, seq_len):
            delta_gaze_sq = (gaze_traj[t, 0] - gaze_traj[t - 1, 0]) ** 2 + (
                gaze_traj[t, 1] - gaze_traj[t - 1, 1]
            ) ** 2
            omega = np.sqrt(delta_gaze_sq) / dt
            base_stab = np.exp(-omega / GAZE_STABILITY_OMEGA_0)
            gaze_stability[t] = np.clip(base_stab + shift_delta[19], 0.0, 1.0)

            delta_pose_sq = (
                (pose_traj[t, 0] - pose_traj[t - 1, 0]) ** 2
                + (pose_traj[t, 1] - pose_traj[t - 1, 1]) ** 2
                + (pose_traj[t, 2] - pose_traj[t - 1, 2]) ** 2
            )
            v_head = np.sqrt(delta_pose_sq) / dt
            rigid_motion[t] = np.clip(np.tanh(v_head / RIGID_MOTION_V_0), 0.0, 1.0)

            delta_au = np.mean(np.abs(au_traj[t, :] - au_traj[t - 1, :])) / dt
            base_nrm = np.tanh(delta_au / NON_RIGID_MOTION_ALPHA_0)
            non_rigid_motion[t] = np.clip(base_nrm + shift_delta[21], 0.0, 1.0)

        # 6. Simulate clustered tracking dropouts
        dropout_indices, burst_count = self._sample_dropout_bursts(seq_len, rng)
        tracking_conf = np.zeros(seq_len, dtype=np.float32)
        success_flag = np.zeros(seq_len, dtype=np.float32)

        for t in range(seq_len):
            if t in dropout_indices:
                success_flag[t] = 0.0
                tracking_conf[t] = float(rng.uniform(0.10, 0.55))
            else:
                success_flag[t] = 1.0
                tracking_conf[t] = float(rng.uniform(0.75, 0.99))

        # 7. Assemble 24-channel tensor
        tensor = np.zeros((seq_len, FEATURE_DIM), dtype=np.float32)
        tensor[:, 0:14] = au_traj
        tensor[:, 14:17] = pose_traj
        tensor[:, 17:19] = gaze_traj
        tensor[:, 19] = gaze_stability
        tensor[:, 20] = rigid_motion
        tensor[:, 21] = non_rigid_motion
        tensor[:, 22] = tracking_conf
        tensor[:, 23] = success_flag

        # Validation assertions
        if np.isnan(tensor).any() or np.isinf(tensor).any():
            raise ValueError(f"NaN/Inf detected in generated tensor for sr {participant_sr}")

        for ch_idx in range(FEATURE_DIM):
            ch_name = CHANNEL_NAMES[ch_idx]
            lower, upper = CHANNEL_BOUNDS[ch_name]
            if (tensor[:, ch_idx] < lower - 1e-5).any() or (
                tensor[:, ch_idx] > upper + 1e-5
            ).any():
                raise ValueError(f"Channel {ch_name} exceeded bounds [{lower}, {upper}]")

        actual_missing = int((success_flag == 0.0).sum())
        mean_conf = float(tracking_conf.mean())
        actual_drop_rate = float(actual_missing / seq_len)

        meta: Dict[str, Union[int, float]] = {
            "sequence_length": seq_len,
            "feature_dimension": FEATURE_DIM,
            "missing_frame_count": actual_missing,
            "mean_tracking_confidence": round(mean_conf, 4),
            "dropout_rate": round(actual_drop_rate, 4),
            "burst_count": burst_count,
        }

        return tensor, meta

    def generate_cohort(
        self,
        manifest_path: Union[str, Path] = TRAIN_TEST_SPLIT_MANIFEST_PATH,
        matrix_path: Union[str, Path] = MODELING_MATRIX_PATH,
        output_dir: Union[str, Path] = SYNTHETIC_VIDEO_V3_DIR,
    ) -> pd.DataFrame:
        """Generate all 800 synthetic video v3 feature trajectories and write manifest."""
        out_dir = Path(output_dir)
        features_dir = out_dir / "features"
        features_dir.mkdir(parents=True, exist_ok=True)

        manifest_df = pd.read_csv(manifest_path)
        matrix_df = pd.read_csv(matrix_path)

        if len(manifest_df) != 800 or len(matrix_df) != 800:
            raise ValueError(f"Expected exactly 800 rows, got {len(manifest_df)}, {len(matrix_df)}")

        # Extract conditioning strictly fitting normalizer on training slice
        conditioning_df = extract_cohort_conditioning_v3(manifest_df, matrix_df)

        manifest_records: List[Dict[str, Union[str, int, float]]] = []

        for idx, row in manifest_df.iterrows():
            participant_id = str(row["participant_id"])
            sr_num = int(row["sr"])
            split_partition = str(row["split_partition"])
            cov_vector = conditioning_df.iloc[idx].values.astype(np.float32)

            tensor, meta = self.generate_single_sequence(sr_num, cov_vector)

            # Save tensor
            out_file = features_dir / f"{participant_id}.npy"
            np.save(out_file, tensor)

            record = {
                "participant_id": participant_id,
                "split_partition": split_partition,
                "data_origin": DATA_ORIGIN_TAG,
                "generator_version": GENERATOR_VERSION,
                "random_seed": self.seed,
                "feature_file_path": str(out_file.as_posix()),
                "sequence_length": meta["sequence_length"],
                "feature_dimension": meta["feature_dimension"],
                "dtype": "float32",
                "missing_frame_count": meta["missing_frame_count"],
                "mean_tracking_confidence": meta["mean_tracking_confidence"],
                "dropout_rate": meta["dropout_rate"],
                "burst_count": meta["burst_count"],
            }
            manifest_records.append(record)

        v3_manifest = pd.DataFrame(manifest_records)
        v3_manifest.to_csv(out_dir / "video_manifest.csv", index=False)
        return v3_manifest


def run_generation_v3(seed: int = DEFAULT_RANDOM_SEED) -> pd.DataFrame:
    """Convenience function to run the full V3 cohort generation."""
    generator = SyntheticVideoGeneratorV3(seed=seed)
    return generator.generate_cohort()


if __name__ == "__main__":
    df = run_generation_v3()
    print(f"Generated Video V3 for {len(df)} participants successfully.")

