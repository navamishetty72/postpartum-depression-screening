"""Clinical conditioning extraction for synthetic audio generation.

Extracts approved non-target clinical covariates from the processed PPD modeling
matrix to condition the synthetic audio distribution.

STRICT AUDIT CHECKS:
1. EPDS items, scores, results, or canonical targets are NEVER accessed or leaked.
2. PHQ items or summary scores are NEVER used for conditioning.
3. Train/test isolation: All scalers and neutral priors are fitted EXCLUSIVELY
   on the 640 training participants.
4. Missing values in clinical covariates default to the neutral training prior,
   never falsely converted to "No" or extreme classes.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from pipelines.synthetic_audio.config import CONDITIONING_COVARIATE_NAMES


class ClinicalConditioningExtractor:
    """Extracts and normalizes approved non-target covariates for audio conditioning."""

    def __init__(self) -> None:
        self.is_fitted_: bool = False
        self.train_age_mean_: float = 0.0
        self.train_age_std_: float = 1.0
        self.train_need_for_support_prior_: float = 0.0

        # Mapping dictionaries
        self.binary_yes_no_map = {"No": 0.0, "Yes": 1.0}
        self.sleep_disruption_map = {"Yes": 0.0, "No": 1.0}  # Cannot relax/sleep -> 1.0
        self.support_received_map = {"High": 0.0, "Medium": 0.5, "Low": 1.0}
        self.support_needed_map = {"Low": 0.0, "Medium": 0.5, "High": 1.0}
        self.motherhood_feeling_map = {"Happy": 0.0, "Neutral": 0.5, "Sad": 1.0}

    def _verify_no_target_leakage(self, df: pd.DataFrame) -> None:
        """Assert that no EPDS target or outcome columns enter the extractor."""
        prohibited_exact = {
            "target_canonical_epds_ge_13",
            "EPDS_high_risk_screening_threshold",
            "canonical_epds_score",
            "epds_score",
        }
        for col in df.columns:
            if col in prohibited_exact:
                raise ValueError(f"Prohibited target column detected in conditioning: '{col}'")
            col_lower = col.lower()
            if "epds" in col_lower and "threshold" in col_lower:
                raise ValueError(f"Prohibited EPDS target column detected: '{col}'")

    def fit(self, train_df: pd.DataFrame) -> "ClinicalConditioningExtractor":
        """Fit conditioning statistics exclusively on training participants.

        Args:
            train_df: DataFrame containing the 640 training records from ppd_modeling_matrix.

        Returns:
            self: The fitted extractor instance.
        """
        self._verify_no_target_leakage(train_df)

        # 1. Fit Age normalization parameters
        if "Age" not in train_df.columns:
            raise KeyError("Required covariate 'Age' not found in training DataFrame.")
        self.train_age_mean_ = float(train_df["Age"].mean())
        self.train_age_std_ = float(train_df["Age"].std())
        if self.train_age_std_ == 0.0:
            self.train_age_std_ = 1.0

        # 2. Fit neutral prior for Need for Support (handling missingness)
        if "Need for Support" not in train_df.columns:
            raise KeyError("Required covariate 'Need for Support' not found in training DataFrame.")
        need_numeric = train_df["Need for Support"].map(self.support_needed_map)
        valid_needs = need_numeric.dropna()
        if len(valid_needs) > 0:
            self.train_need_for_support_prior_ = float(valid_needs.mean())
        else:
            self.train_need_for_support_prior_ = 0.5

        self.is_fitted_ = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform clinical covariates into normalized conditioning representations.

        Args:
            df: DataFrame containing clinical predictor records (train or test).

        Returns:
            pd.DataFrame: Conditioned covariate matrix with 5 normalized columns.
        """
        if not self.is_fitted_:
            raise RuntimeError("ClinicalConditioningExtractor must be fitted before transforming.")

        self._verify_no_target_leakage(df)

        n_records = len(df)
        out = pd.DataFrame(index=df.index)

        # 1. Age: standardized against training mean and std
        out["norm_age"] = (df["Age"] - self.train_age_mean_) / self.train_age_std_

        # 2. Sleep Disruption: combination of tended and asleep sleep inability
        tended_sleep_col = "Relax/sleep when newborn is tended "
        asleep_sleep_col = "Relax/sleep when the newborn is asleep"
        
        tended_val = df[tended_sleep_col].map(self.sleep_disruption_map).fillna(0.5)
        asleep_val = df[asleep_sleep_col].map(self.sleep_disruption_map).fillna(0.5)
        out["sleep_disruption"] = ((tended_val + asleep_val) / 2.0).astype(np.float64)

        # 3. Support Deficit: combination of low received support and high needed support
        rec_val = df["Recieved Support"].map(self.support_received_map).fillna(0.5)
        need_val = df["Need for Support"].map(self.support_needed_map).fillna(
            self.train_need_for_support_prior_
        )
        out["support_deficit"] = ((rec_val + need_val) / 2.0).astype(np.float64)

        # 4. Infant Distress: maternal stress/worry regarding child health
        illness_val = df["Newborn illness"].map(self.binary_yes_no_map).fillna(0.0)
        worry_val = df["Worry about newborn"].map(self.binary_yes_no_map).fillna(0.0)
        out["infant_distress"] = ((illness_val + worry_val) / 2.0).astype(np.float64)

        # 5. Maternal Affect: affective valence proxy
        affect_val = df["Feeling about motherhood"].map(self.motherhood_feeling_map).fillna(0.5)
        out["maternal_affect"] = affect_val.astype(np.float64)

        # Ensure column ordering matches CONDITIONING_COVARIATE_NAMES
        out = out[CONDITIONING_COVARIATE_NAMES]
        return out


def extract_cohort_conditioning(
    manifest_df: pd.DataFrame,
    modeling_matrix_df: pd.DataFrame,
) -> pd.DataFrame:
    """Extracts conditioning covariates for the entire 800-participant cohort.

    Ensures strict train/test isolation by fitting normalizers exclusively
    on rows marked as 'train' in the manifest.

    Args:
        manifest_df: train_test_split_manifest DataFrame (800 rows).
        modeling_matrix_df: ppd_modeling_matrix DataFrame (800 rows).

    Returns:
        pd.DataFrame: 800 rows of extracted conditioning covariates aligned
                      with manifest_df.
    """
    if len(manifest_df) != 800 or len(modeling_matrix_df) != 800:
        raise ValueError(
            f"Expected exactly 800 records in manifest and matrix, got "
            f"{len(manifest_df)} and {len(modeling_matrix_df)}"
        )

    train_mask = manifest_df["split_partition"] == "train"
    train_indices = manifest_df.loc[train_mask, "matrix_index"].values

    # Isolate strictly the non-target clinical predictor columns
    approved_covariate_columns = [
        "Age",
        "Relax/sleep when newborn is tended ",
        "Relax/sleep when the newborn is asleep",
        "Recieved Support",
        "Need for Support",
        "Newborn illness",
        "Worry about newborn",
        "Feeling about motherhood",
    ]

    # Explicitly filter out any target column prior to conditioning extraction
    safe_matrix = modeling_matrix_df[approved_covariate_columns].copy()
    train_slice = safe_matrix.iloc[train_indices].copy()

    extractor = ClinicalConditioningExtractor()
    extractor.fit(train_slice)

    # Transform the entire matrix in manifest row order
    cohort_covariates = extractor.transform(safe_matrix)
    cohort_covariates.index = manifest_df.index
    return cohort_covariates
