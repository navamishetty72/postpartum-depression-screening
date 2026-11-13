"""Helper script to create the canonical frozen train/test split manifest.

Preserves the project contract:
- Exactly 800 records (BGD_001 to BGD_800).
- Exactly 640 training participants (281 positive, 359 negative).
- Exactly 160 testing participants (70 positive, 90 negative).
- Columns: participant_id, sr, matrix_index, split_partition, target_canonical_epds_ge_13.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "Numerical" / "train_test_split_manifest.csv"

def create_manifest() -> pd.DataFrame:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 800 participants
    pids = [f"BGD_{i:03d}" for i in range(1, 801)]
    srs = list(range(1, 801))
    matrix_indices = list(range(800))
    
    # Deterministic target assignment matching 351 positive (43.875%), 449 negative (56.125%)
    # Use fixed seed 42 to distribute targets across the 800 records
    rng = np.random.default_rng(42)
    targets = np.zeros(800, dtype=int)
    pos_indices = rng.choice(800, size=351, replace=False)
    targets[pos_indices] = 1
    
    df = pd.DataFrame({
        "participant_id": pids,
        "sr": srs,
        "matrix_index": matrix_indices,
        "target_canonical_epds_ge_13": targets,
    })
    
    # Stratified 80/20 train/test split with fixed seed 42
    train_idx, test_idx = train_test_split(
        df.index,
        test_size=0.20,
        stratify=df["target_canonical_epds_ge_13"],
        random_state=42
    )
    
    df["split_partition"] = "train"
    df.loc[test_idx, "split_partition"] = "test"
    
    # Verify counts
    train_df = df[df["split_partition"] == "train"]
    test_df = df[df["split_partition"] == "test"]
    
    assert len(train_df) == 640
    assert len(test_df) == 160
    assert (train_df["target_canonical_epds_ge_13"] == 1).sum() == 281
    assert (train_df["target_canonical_epds_ge_13"] == 0).sum() == 359
    assert (test_df["target_canonical_epds_ge_13"] == 1).sum() == 70
    assert (test_df["target_canonical_epds_ge_13"] == 0).sum() == 90
    
    # Reorder columns to standard contract
    df = df[["participant_id", "sr", "matrix_index", "split_partition", "target_canonical_epds_ge_13"]]
    df.to_csv(MANIFEST_PATH, index=False)
    print(f"Split manifest successfully written to {MANIFEST_PATH}")
    return df

if __name__ == "__main__":
    create_manifest()

