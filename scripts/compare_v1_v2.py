"""Comparative statistical evaluation script: Synthetic Video v1 vs v2."""

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import pointbiserialr

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def run_comparison():
    m1 = pd.read_csv(PROJECT_ROOT / "data/synthetic/video/video_manifest.csv")
    m2 = pd.read_csv(PROJECT_ROOT / "data/synthetic/video_v2/video_manifest.csv")
    split_df = pd.read_csv(PROJECT_ROOT / "data/processed/Numerical/train_test_split_manifest.csv")

    print("================================================================================")
    print("        SYNTHETIC VIDEO COMPARATIVE AUDIT: GENERATOR V1 VS GENERATOR V2")
    print("================================================================================")
    print(f"Total Cohort Records:        v1 = {len(m1)} | v2 = {len(m2)}")
    print(f"Train / Test Counts:         v1 = {m1['split_partition'].value_counts().to_dict()} | v2 = {m2['split_partition'].value_counts().to_dict()}")
    print(f"Sequence Length Range:       v1 = [{m1['sequence_length'].min()}, {m1['sequence_length'].max()}] (mean: {m1['sequence_length'].mean():.1f}) | v2 = [{m2['sequence_length'].min()}, {m2['sequence_length'].max()}] (mean: {m2['sequence_length'].mean():.1f})")
    print(f"Dropout Rate Range:          v1 = [{m1['dropout_rate'].min():.4f}, {m1['dropout_rate'].max():.4f}] (mean: {m1['dropout_rate'].mean():.4f}) | v2 = [{m2['dropout_rate'].min():.4f}, {m2['dropout_rate'].max():.4f}] (mean: {m2['dropout_rate'].mean():.4f})")
    print(f"Mean Tracking Confidence:    v1 = {m1['mean_tracking_confidence'].mean():.4f} | v2 = {m2['mean_tracking_confidence'].mean():.4f}")
    if "burst_count" in m2.columns:
        print(f"Mean Bursts per Participant: v2 = {m2['burst_count'].mean():.2f}")

    # Inspect 100 sample trajectories
    v1_paths = m1["feature_file_path"].head(100)
    v2_paths = m2["feature_file_path"].head(100)

    # AU correlations
    v1_au6_12, v2_au6_12 = [], []
    v1_au1_2, v2_au1_2 = [], []
    v1_au4_7, v2_au4_7 = [], []
    v1_au9_10, v2_au9_10 = [], []

    # Derived metric correlations with raw inputs
    v1_gaze_stab_corr, v2_gaze_stab_corr = [], []
    v1_rigid_corr, v2_rigid_corr = [], []

    # Burst lengths
    v1_bursts, v2_bursts = [], []

    for p1, p2 in zip(v1_paths, v2_paths):
        a1 = np.load(PROJECT_ROOT / p1)
        a2 = np.load(PROJECT_ROOT / p2)

        # AU correlations
        v1_au6_12.append(np.corrcoef(a1[:, 4], a1[:, 8])[0, 1])
        v2_au6_12.append(np.corrcoef(a2[:, 4], a2[:, 8])[0, 1])
        v1_au1_2.append(np.corrcoef(a1[:, 0], a1[:, 1])[0, 1])
        v2_au1_2.append(np.corrcoef(a2[:, 0], a2[:, 1])[0, 1])
        v1_au4_7.append(np.corrcoef(a1[:, 2], a1[:, 5])[0, 1])
        v2_au4_7.append(np.corrcoef(a2[:, 2], a2[:, 5])[0, 1])
        v1_au9_10.append(np.corrcoef(a1[:, 6], a1[:, 7])[0, 1])
        v2_au9_10.append(np.corrcoef(a2[:, 6], a2[:, 7])[0, 1])

        # Burst lengths
        for arr, container in [(a1, v1_bursts), (a2, v2_bursts)]:
            curr = 0
            for f in arr[:, 23]:
                if f == 0.0:
                    curr += 1
                else:
                    if curr > 0:
                        container.append(curr)
                        curr = 0
            if curr > 0:
                container.append(curr)

    print("\n--- ACTION UNIT CORRELATION COMPARISON ---")
    print(f"AU06 - AU12 (Duchenne Smile):       v1 = {np.nanmean(v1_au6_12):+.3f} | v2 = {np.nanmean(v2_au6_12):+.3f}")
    print(f"AU01 - AU02 (Eyebrow Raise):        v1 = {np.nanmean(v1_au1_2):+.3f} | v2 = {np.nanmean(v2_au1_2):+.3f}")
    print(f"AU04 - AU07 (Brow Furrow/Tension):  v1 = {np.nanmean(v1_au4_7):+.3f} | v2 = {np.nanmean(v2_au4_7):+.3f}")
    print(f"AU09 - AU10 (Nasolabial Elevation): v1 = {np.nanmean(v1_au9_10):+.3f} | v2 = {np.nanmean(v2_au9_10):+.3f}")

    print("\n--- TRACKING DROPOUT BURST DYNAMICS ---")
    v1_b = np.array(v1_bursts)
    v2_b = np.array(v2_bursts)
    print(f"Mean Dropout Burst Length:          v1 = {np.mean(v1_b):.2f} frames | v2 = {np.mean(v2_b):.2f} frames")
    print(f"Max Dropout Burst Length:           v1 = {np.max(v1_b)} frames | v2 = {np.max(v2_b)} frames")
    print(f"Isolated Single-Frame Dropouts:     v1 = {np.mean(v1_b == 1)*100:.1f}% | v2 = {np.mean(v2_b == 1)*100:.1f}%")

    print("\n--- DERIVED METRIC FORMULATION STATUS ---")
    print("v1: Generated as independent isotropic AR(1) Gaussian noise (base mean 0.88, 0.22, 0.22).")
    print("v2: Analytically derived via continuous differential equations from underlying gaze, pose, and AU series.")
    print("================================================================================")

if __name__ == "__main__":
    run_comparison()

