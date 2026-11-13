"""Synthetic multimodal dataset generation orchestrator.

Generates reproducible synthetic clinical numerical data (or processes raw survey data
if present), followed by synthetic audio profiles, synthetic text narratives, and
synthetic video feature trajectories for the PPD Multimodal Research Prototype.
"""

import sys
from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.clinical_numerical.config import (
    RAW_DATA_PATH,
    MODELING_MATRIX_PATH,
    SPLIT_MANIFEST_PATH,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    RANDOM_SEED,
)
from pipelines.synthetic_audio.generator import run_generation as generate_audio
from pipelines.synthetic_text.generator import run_generation as generate_text
from pipelines.synthetic_video.generator import run_generation as generate_video


def process_raw_clinical_data(raw_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Process authentic Bangladesh survey dataset into modeling matrix and split manifest."""
    raw = pd.read_csv(raw_path)
    df = raw.copy()

    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)

    response_map = {
        "several days": "Several days",
        "several days ": "Several days",
        "মাঝে মধ্যে (several days)": "Several days",
        "around half the days": "Around half the days",
        "nearly every day": "Nearly every day",
        "not at all": "Not at all",
    }
    for col in df.columns:
        df[col] = df[col].map(
            lambda v: response_map.get(str(v).lower().strip(), v)
            if pd.notna(v) and isinstance(v, str)
            else v
        )

    category_maps = {
        "Education Level": {"High school": "High School", "Primary school": "Primary School"},
        "Husband's education level": {"High school": "High School", "Primary school": "Primary School"},
        "Total children": {"More than Two": "More than two"},
        "Occupation before latest pregnancy": {"House wife": "Housewife"},
        "Occupation After Your Latest Childbirth": {"House wife": "Housewife"},
        "Diseases during pregnancy": {"Non-chronic disease": "Non-Chronic Disease", "Chronic disease": "Chronic Disease"},
    }
    for col, mapping in category_maps.items():
        if col in df.columns:
            df[col] = df[col].replace(mapping)

    epds_cols = [
        "You have been able to laugh and see the funny side of things",
        "You have looked forward with enjoyment to things",
        "You have blamed myself unnecessarily when things went wrong",
        "You have been anxious or worried for no good reason",
        "You have felt scared or panicky for no good reason",
        "Things have been getting to you",
        "You have been so unhappy that you have had difficulty sleeping",
        "You have felt sad or miserable",
        "You have been so unhappy that you have been crying",
        "The thought of harming yourself has occurred ",
    ]
    score_map = {
        "Not at all": 0,
        "Several days": 1,
        "Around half the days": 2,
        "More than half the days": 2,
        "Nearly every day": 3,
    }

    for i, col in enumerate(epds_cols, 1):
        s = df[col].map(score_map)
        if i in (1, 2):
            s = 3 - s
        df[f"EPDS_{i}_score"] = s.astype("Int64")

    score_cols = [f"EPDS_{i}_score" for i in range(1, 11)]
    df["EPDS_score_recomputed"] = df[score_cols].sum(axis=1, min_count=10).astype("Int64")
    y = (df["EPDS_score_recomputed"] >= 13).astype(int)

    train_idx, test_idx = train_test_split(
        df.index, test_size=0.20, random_state=RANDOM_SEED, stratify=y
    )

    manifest = pd.DataFrame({
        "participant_id": [f"BGD_{sr:03d}" for sr in df["sr"]],
        "sr": df["sr"],
        "matrix_index": df.index,
        "split_partition": ["train" if i in train_idx else "test" for i in df.index],
        "target_canonical_epds_ge_13": y,
    })

    feature_cols = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
    matrix = df[feature_cols].copy()
    matrix["EPDS_high_risk_screening_threshold"] = y

    return matrix, manifest


def generate_synthetic_clinical_data(seed: int = RANDOM_SEED) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate reproducible synthetic clinical numerical data conforming to study schema."""
    rng = np.random.default_rng(seed)
    n = 800

    y = np.zeros(n, dtype=int)
    perm = rng.permutation(n)
    y[perm[:351]] = 1

    train_idx, test_idx = train_test_split(
        np.arange(n), test_size=0.20, random_state=seed, stratify=y
    )

    data = {}
    data["Age"] = np.where(y == 1, rng.integers(24, 38, size=n), rng.integers(18, 32, size=n))
    data["Number of the latest pregnancy"] = rng.integers(1, 4, size=n)

    cat_specs = {
        "Residence": ["City", "Village"],
        "Education Level": ["University", "College", "Primary School", "High School"],
        "Marital status": ["Married", "Divorced"],
        "Occupation before latest pregnancy": ["Student", "Doctor", "Service", "Housewife", "Teacher", "Other", "Business"],
        "Monthly income before latest pregnancy": ["10000 to 20000", "More than 30000", "Less than 5000", "5000 to 10000", "20000 to 30000"],
        "Occupation After Your Latest Childbirth": ["Student", "Doctor", "Service", "Housewife", "Teacher", "Business", "Other"],
        "Current monthly income": ["10000 to 20000", "More than 30000", "Less than 5000", "5000 to 10000", "20000 to 30000"],
        "Husband's education level": ["University", "College", "Primary School", "High School"],
        "Husband’s monthly income": ["More than 30000", "10000 to 20000", "5000 to 10000", "20000 to 30000", "Less than 5000"],
        "Addiction": ["Smoking", "Drinking", "Drugs"],
        "Total children": ["One", "Two", "More than two"],
        "Disease before pregnancy": ["Non-Chronic Disease", "Chronic Disease"],
        "History of pregnancy loss": ["Miscarriage", "Still-born delivery"],
        "Family type": ["Nuclear", "Joint"],
        "Number of household members": ["6 to 8", "2 to 5", "9 or more"],
        "Relationship with the in-laws": ["Neutral", "Good", "Bad", "Friendly", "Poor"],
        "Relationship with husband": ["Good", "Neutral", "Bad"],
        "Relationship with the newborn": ["Good", "Neutral", "Bad", "Very good"],
        "Relationship between father and newborn": ["Good", "Neutral", "Bad", "Very good"],
        "Feeling about motherhood": ["Neutral", "Happy", "Sad"],
        "Recieved Support": ["High", "Medium", "Low"],
        "Need for Support": ["Medium", "Low", "High"],
        "Major changes or losses during pregnancy": ["Yes", "No"],
        "Abuse": ["Yes", "No"],
        "Trust and share feelings": ["Yes", "No"],
        "Pregnancy length": ["10 months", "9 months", "8 months", "Less than 5 months", "7 months", "6 months"],
        "Pregnancy plan": ["No", "Yes"],
        "Regular checkups": ["Yes", "No"],
        "Fear of pregnancy": ["Yes", "No"],
        "Diseases during pregnancy": ["Chronic Disease", "Non-Chronic Disease"],
        "Age of newborn": ["6 months to 1 year", "Older than 1.5 year", "0 to 6 months", "1 year to 1.5 year"],
        "Age of immediate older children": ["13yr or more", "1yr to 3yr", "7yr to 12yr", "4yr to 6yr"],
        "Mode of delivery": ["Normal Delivery", "Caesarean Section"],
        "Birth weight": ["2.5kg to 3.5kg", "Less than 2.5kg", "More than 3.5kg"],
        "Newborn illness": ["No", "Yes"],
        "Worry about newborn": ["Yes", "No"],
        "Breastfeed": ["Yes", "No"],
        "Breastfeeding struggle": ["No", "Yes"],
        "Relax/sleep when newborn is tended ": ["Yes", "No"],
        "Relax/sleep when the newborn is asleep": ["Yes", "No"],
        "Baby cry reason": ["Hungry", "Colic", "Sleepy", "Wet"],
        "Self blame when baby cries": ["No", "Yes"],
        "Support from family members": ["Yes", "No"],
        "Who is primary support": ["Mother", "Husband", "Mother-in-law", "Sister"],
    }

    for col in CATEGORICAL_FEATURES:
        levels = cat_specs.get(col, ["Category A", "Category B"])
        if col == "Relationship with husband":
            data[col] = np.where(y == 1, rng.choice(["Bad", "Neutral"], size=n, p=[0.7, 0.3]),
                                         rng.choice(["Good", "Neutral"], size=n, p=[0.8, 0.2]))
        elif col == "Feeling about motherhood":
            data[col] = np.where(y == 1, rng.choice(["Sad", "Neutral"], size=n, p=[0.75, 0.25]),
                                         rng.choice(["Happy", "Neutral"], size=n, p=[0.8, 0.2]))
        elif col == "Recieved Support":
            data[col] = np.where(y == 1, rng.choice(["Low", "Medium"], size=n, p=[0.7, 0.3]),
                                         rng.choice(["High", "Medium"], size=n, p=[0.7, 0.3]))
        elif col == "Need for Support":
            vals = np.where(y == 1, rng.choice(["High", "Medium"], size=n, p=[0.7, 0.3]),
                                    rng.choice(["Low", "Medium"], size=n, p=[0.8, 0.2])).astype(object)
            # Set exactly 167 missing values (132 train, 35 test) to match clinical cohort specification
            vals[train_idx[:132]] = np.nan
            vals[test_idx[:35]] = np.nan
            data[col] = vals
        elif col == "Trust and share feelings":
            vals = rng.choice(levels, size=n).astype(object)
            vals[train_idx[0]] = np.nan
            data[col] = vals
        elif col in ["Relax/sleep when newborn is tended ", "Relax/sleep when the newborn is asleep"]:
            data[col] = np.where(y == 1, rng.choice(["No", "Yes"], size=n, p=[0.8, 0.2]),
                                         rng.choice(["Yes", "No"], size=n, p=[0.8, 0.2]))
        elif col == "Worry about newborn":
            data[col] = np.where(y == 1, rng.choice(["Yes", "No"], size=n, p=[0.85, 0.15]),
                                         rng.choice(["No", "Yes"], size=n, p=[0.75, 0.25]))
        else:
            data[col] = rng.choice(levels, size=n)

    df_matrix = pd.DataFrame(data)
    df_matrix["EPDS_high_risk_screening_threshold"] = y

    partition = np.array(["train"] * n, dtype=object)
    partition[test_idx] = "test"

    df_manifest = pd.DataFrame({
        "participant_id": [f"BGD_{i+1:03d}" for i in range(n)],
        "sr": np.arange(1, n + 1),
        "matrix_index": np.arange(n),
        "split_partition": partition,
        "target_canonical_epds_ge_13": y,
    })

    return df_matrix, df_manifest


def main() -> None:
    """Run full synthetic multimodal generation sequence."""
    print("=" * 60)
    print("Postpartum Depression (PPD) Multimodal Dataset Generator")
    print("=" * 60)

    MODELING_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 1. Clinical Numerical Foundation
    if MODELING_MATRIX_PATH.exists() and SPLIT_MANIFEST_PATH.exists():
        print(f"[1/4] Using existing clinical matrix: {MODELING_MATRIX_PATH}")
    elif RAW_DATA_PATH.exists():
        print(f"[1/4] Processing raw clinical data: {RAW_DATA_PATH}")
        matrix, manifest = process_raw_clinical_data(RAW_DATA_PATH)
        matrix.to_csv(MODELING_MATRIX_PATH, index=False)
        manifest.to_csv(SPLIT_MANIFEST_PATH, index=False)
        print(f"      Saved modeling matrix: {MODELING_MATRIX_PATH}")
        print(f"      Saved split manifest:  {SPLIT_MANIFEST_PATH}")
    else:
        print("[1/4] Raw data not found. Generating synthetic clinical baseline fixtures...")
        matrix, manifest = generate_synthetic_clinical_data()
        matrix.to_csv(MODELING_MATRIX_PATH, index=False)
        manifest.to_csv(SPLIT_MANIFEST_PATH, index=False)
        print(f"      Generated synthetic matrix: {MODELING_MATRIX_PATH}")
        print(f"      Generated split manifest:   {SPLIT_MANIFEST_PATH}")

    # 2. Synthetic Audio Generation
    print("\n[2/4] Generating synthetic audio profiles and temporal embeddings...")
    generate_audio()

    # 3. Synthetic Text Generation
    print("\n[3/4] Generating synthetic clinical intake text narratives...")
    generate_text()

    # 4. Synthetic Video Generation
    print("\n[4/4] Generating synthetic video Action Unit feature trajectories...")
    generate_video()

    print("\n" + "=" * 60)
    print("Multimodal dataset generation successfully completed across all 4 branches!")
    print("=" * 60)


if __name__ == "__main__":
    main()
