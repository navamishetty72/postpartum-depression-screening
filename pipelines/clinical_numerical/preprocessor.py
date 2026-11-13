"""Preprocessing pipeline for the clinical numerical modality.

Separates numerical and categorical streams, preserves missingness information,
and prevents leakage by fitting exclusively on training participants.
"""

from pathlib import Path
from typing import List, Optional
import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import NUMERICAL_FEATURES, CATEGORICAL_FEATURES


class ClinicalPreprocessor(BaseEstimator, TransformerMixin):
    """Scikit-learn compliant preprocessor for 46 clinical survey features.

    Numerical features:
        - Median imputation with MissingIndicator added to capture non-random missingness.
        - Standard scaling (zero mean, unit variance).

    Categorical features:
        - Constant imputation with fill_value='Missing' to preserve non-response without bias.
        - One-hot encoding with handle_unknown='ignore' and dense output.
    """

    def __init__(
        self,
        numerical_features: Optional[List[str]] = None,
        categorical_features: Optional[List[str]] = None,
    ):
        self.numerical_features = numerical_features or list(NUMERICAL_FEATURES)
        self.categorical_features = categorical_features or list(CATEGORICAL_FEATURES)
        self.is_fitted = False
        self.feature_names_: List[str] = []

        # Numerical sub-pipeline
        self.numerical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                ("scaler", StandardScaler()),
            ]
        )

        # Categorical sub-pipeline
        self.categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="constant", fill_value="Missing")),
                (
                    "onehot",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False,
                    ),
                ),
            ]
        )

        # Combined ColumnTransformer
        self.transformer = ColumnTransformer(
            transformers=[
                ("num", self.numerical_pipeline, self.numerical_features),
                ("cat", self.categorical_pipeline, self.categorical_features),
            ],
            remainder="drop",
        )

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "ClinicalPreprocessor":
        """Fit preprocessor exclusively on training data.

        Args:
            X: Training DataFrame containing the 46 features.
            y: Optional target (unused, for sklearn compatibility).

        Returns:
            self: Fitted preprocessor.
        """
        self._validate_input_columns(X)
        self.transformer.fit(X)
        self.is_fitted = True
        self._extract_feature_names()
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """Apply fitted transformations to inputs without data leakage.

        Args:
            X: DataFrame to transform.

        Returns:
            np.ndarray: Transformed float32 array.
        """
        if not self.is_fitted:
            raise RuntimeError("ClinicalPreprocessor must be fitted before calling transform().")
        self._validate_input_columns(X)
        transformed = self.transformer.transform(X)
        return np.asarray(transformed, dtype=np.float32)

    def fit_transform(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> np.ndarray:
        """Fit on training data and transform in a single call."""
        return self.fit(X, y).transform(X)

    def get_feature_names(self) -> List[str]:
        """Return names of transformed features."""
        if not self.is_fitted:
            raise RuntimeError("ClinicalPreprocessor must be fitted to retrieve feature names.")
        return list(self.feature_names_)

    def _validate_input_columns(self, X: pd.DataFrame) -> None:
        """Ensure all required columns are present in input DataFrame."""
        required = set(self.numerical_features + self.categorical_features)
        missing = required - set(X.columns)
        if missing:
            raise ValueError(f"Missing required columns in input DataFrame: {sorted(missing)}")

    def _extract_feature_names(self) -> None:
        """Extract output feature names from the fitted ColumnTransformer."""
        feature_names = []
        try:
            feature_names = list(self.transformer.get_feature_names_out())
        except Exception:
            # Fallback manual reconstruction if get_feature_names_out encounters version quirks
            # Numerical features + indicator columns
            num_imputer = self.transformer.named_transformers_["num"].named_steps["imputer"]
            for col in self.numerical_features:
                feature_names.append(f"num__{col}")
            if hasattr(num_imputer, "indicator_") and num_imputer.indicator_ is not None:
                for idx in num_imputer.indicator_.features_:
                    feature_names.append(f"num__missing_{self.numerical_features[idx]}")

            # Categorical one-hot categories
            cat_encoder = self.transformer.named_transformers_["cat"].named_steps["onehot"]
            for col, cats in zip(self.categorical_features, cat_encoder.categories_):
                for cat in cats:
                    feature_names.append(f"cat__{col}_{cat}")

        self.feature_names_ = feature_names

    def save(self, filepath: Path) -> None:
        """Serialize fitted preprocessor to disk."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, filepath)

    @classmethod
    def load(cls, filepath: Path) -> "ClinicalPreprocessor":
        """Load serialized preprocessor from disk."""
        preprocessor = joblib.load(filepath)
        if not isinstance(preprocessor, cls):
            raise TypeError(f"Loaded object is not an instance of {cls.__name__}")
        return preprocessor

