"""Statistical baseline models for participant-level PPD video screening.

Implements:
1. ParticipantStatisticalFeatureExtractor: Extract participant-level summary statistics
   (mean, std, min, max, quantiles [10%, 25%, 50%, 75%, 90%], sequence length, tracking dropout rate)
   using strictly valid tracked frames.
2. VideoLogisticRegressionBaseline: Scikit-learn pipeline wrapper with internal median imputation
   and standard scaling fitted strictly within training folds.
3. VideoRandomForestBaseline: Scikit-learn random forest classifier wrapper with internal median
   imputation and standard scaling.

SCIENTIFIC INTEGRITY NOTICE:
Synthetic Video V2 features are abstract numerical simulations. Video features alone
do not represent authentic patient observations or diagnostic biomarkers.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import torch
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from pipelines.video_model.config import (
    CHANNEL_NAMES,
    CONFIDENCE_THRESHOLD,
    DEFAULT_RANDOM_SEED,
    FEATURE_DIM,
)

SELECTED_QUANTILES: List[float] = [0.10, 0.25, 0.50, 0.75, 0.90]
SUPPORTED_FEATURE_SUBSETS: Tuple[str, ...] = ("all", "facial_motion", "tracking_only")


class ParticipantStatisticalFeatureExtractor(BaseEstimator):
    """Extracts participant-level statistical summary vector from temporal video sequences.

    Supports three feature subsets:
    - 'all': All 220 features (channels 0..21 stats + channels 22..23 stats + 4 tracking metadata).
    - 'facial_motion': 198 features (channels 0..21 stats only; excludes all tracking channels and metadata).
    - 'tracking_only': 22 features (channels 22..23 stats [18] + 4 sequence tracking metadata).
    """

    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        quantiles: Optional[List[float]] = None,
        channels: Optional[List[str]] = None,
        feature_subset: str = "all",
    ) -> None:
        """Initialize ParticipantStatisticalFeatureExtractor.

        Args:
            confidence_threshold: Minimum tracking confidence to consider frame valid.
            quantiles: List of quantiles to extract (defaults to [0.10, 0.25, 0.50, 0.75, 0.90]).
            channels: Channel names corresponding to the 24 columns (defaults to CHANNEL_NAMES).
            feature_subset: Feature subset ablation ('all', 'facial_motion', or 'tracking_only').
        """
        self.confidence_threshold = confidence_threshold
        self.quantiles = quantiles if quantiles is not None else SELECTED_QUANTILES
        self.channels = channels if channels is not None else CHANNEL_NAMES
        self.feature_subset = feature_subset.lower()

        if self.feature_subset not in SUPPORTED_FEATURE_SUBSETS:
            raise ValueError(
                f"Unsupported feature_subset '{self.feature_subset}'. Choose from {SUPPORTED_FEATURE_SUBSETS}."
            )

        # Generate deterministic feature names
        self.feature_names_: List[str] = self._build_feature_names()
        self.n_features_out_: int = len(self.feature_names_)

    def _build_feature_names(self) -> List[str]:
        """Construct descriptive feature names for the chosen feature subset."""
        all_channel_names: List[str] = []
        for ch in self.channels:
            all_channel_names.append(f"{ch}_mean")
            all_channel_names.append(f"{ch}_std")
            all_channel_names.append(f"{ch}_min")
            all_channel_names.append(f"{ch}_max")
            for q in self.quantiles:
                q_pct = int(round(q * 100))
                all_channel_names.append(f"{ch}_q{q_pct:02d}")

        meta_names = [
            "sequence_length",
            "valid_frames_count",
            "tracking_dropout_rate",
            "mean_tracking_confidence",
        ]

        if self.feature_subset == "all":
            return all_channel_names + meta_names
        elif self.feature_subset == "facial_motion":
            # Channels 0..21 (22 channels * 9 stats = 198 features)
            return all_channel_names[: 22 * 9]
        elif self.feature_subset == "tracking_only":
            # Channels 22..23 (2 channels * 9 stats = 18 features) + 4 meta = 22 features
            return all_channel_names[22 * 9 :] + meta_names
        else:
            raise ValueError(f"Unknown feature subset: {self.feature_subset}")

    def extract_single(self, tensor: Union[np.ndarray, torch.Tensor]) -> np.ndarray:
        """Extract statistical vector from a single (T, 24) sequence.

        Args:
            tensor: (T, 24) NumPy array or PyTorch Tensor.

        Returns:
            1D float64 NumPy array of shape (220,).
        """
        if isinstance(tensor, torch.Tensor):
            arr = tensor.detach().cpu().numpy()
        else:
            arr = np.asarray(tensor)

        if arr.ndim != 2 or arr.shape[1] != FEATURE_DIM:
            raise ValueError(f"Expected 2D array of shape (T, {FEATURE_DIM}), got {arr.shape}")

        T = arr.shape[0]
        if T < 1:
            raise ValueError("Sequence length must be at least 1.")

        # Tracking channels: 22=tracking_confidence, 23=success_flag
        tracking_conf = arr[:, 22]
        success_flag = arr[:, 23]

        valid_mask = (success_flag == 1.0) & (tracking_conf >= self.confidence_threshold)
        n_valid = int(np.sum(valid_mask))
        dropout_rate = 1.0 - (float(n_valid) / float(T))
        mean_conf = float(np.mean(tracking_conf))

        # Fallback to all frames if tracking failed on all frames to avoid NaNs
        if n_valid > 0:
            tracked_arr = arr[valid_mask, :]
        else:
            tracked_arr = arr

        feats: List[float] = []

        # 9 statistics per channel
        for ch_idx in range(FEATURE_DIM):
            col = tracked_arr[:, ch_idx]
            mu = float(np.mean(col))
            # Safe standard deviation with ddof=0
            sigma = float(np.std(col)) if len(col) > 1 else 0.0
            col_min = float(np.min(col))
            col_max = float(np.max(col))
            q_vals = [float(q_val) for q_val in np.quantile(col, self.quantiles)]

            feats.append(mu)
            feats.append(sigma)
            feats.append(col_min)
            feats.append(col_max)
            feats.extend(q_vals)

        # 4 metadata features
        feats.append(float(T))
        feats.append(float(n_valid))
        feats.append(float(dropout_rate))
        feats.append(mean_conf)

        out_arr = np.array(feats, dtype=np.float64)

        # Final safety check: guarantee zero NaNs/Infs
        if np.isnan(out_arr).any() or np.isinf(out_arr).any():
            out_arr = np.nan_to_num(out_arr, nan=0.0, posinf=1.0, neginf=-1.0)

        # Select feature subset
        if self.feature_subset == "all":
            return out_arr
        elif self.feature_subset == "facial_motion":
            return out_arr[: 22 * 9]
        elif self.feature_subset == "tracking_only":
            return out_arr[22 * 9 :]
        else:
            raise ValueError(f"Unknown feature subset: {self.feature_subset}")

    def fit(self, X: Any = None, y: Any = None) -> "ParticipantStatisticalFeatureExtractor":
        """Stateless transformer fit."""
        return self

    def transform(self, X: Union[List[np.ndarray], np.ndarray]) -> np.ndarray:
        """Extract statistical features for a list or batch of sequences.

        Args:
            X: List of (T_i, 24) arrays or 3D array (N, T, 24).

        Returns:
            2D float64 array of shape (N, 220).
        """
        if isinstance(X, np.ndarray) and X.ndim == 2 and X.shape[1] == self.n_features_out_:
            # Already extracted
            return X

        rows: List[np.ndarray] = []
        for item in X:
            rows.append(self.extract_single(item))

        return np.vstack(rows)

    def fit_transform(self, X: Any, y: Any = None) -> np.ndarray:
        """Fit and transform sequences."""
        return self.transform(X)

    def get_feature_names_out(self, input_features: Any = None) -> List[str]:
        """Return output feature names."""
        return self.feature_names_


class VideoLogisticRegressionBaseline(BaseEstimator, ClassifierMixin):
    """Logistic Regression baseline classifier for participant-level video screening.

    Wraps a leak-free Scikit-learn Pipeline with:
    1. ParticipantStatisticalFeatureExtractor (if raw sequence tensors are passed).
    2. SimpleImputer (median strategy).
    3. StandardScaler.
    4. LogisticRegression (class_weight='balanced').
    """

    def __init__(
        self,
        C: float = 1.0,
        penalty: Optional[str] = None,
        solver: str = "lbfgs",
        max_iter: int = 1000,
        random_state: int = DEFAULT_RANDOM_SEED,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        feature_subset: str = "all",
    ) -> None:
        self.C = C
        self.penalty = penalty
        self.solver = solver
        self.max_iter = max_iter
        self.random_state = random_state
        self.confidence_threshold = confidence_threshold
        self.feature_subset = feature_subset

        self.extractor = ParticipantStatisticalFeatureExtractor(
            confidence_threshold=confidence_threshold,
            feature_subset=feature_subset,
        )
        self.pipeline: Optional[Pipeline] = None

    def _build_pipeline(self) -> Pipeline:
        """Construct scikit-learn pipeline."""
        clf_kwargs: Dict[str, Any] = {
            "C": self.C,
            "solver": self.solver,
            "max_iter": self.max_iter,
            "random_state": self.random_state,
            "class_weight": "balanced",
        }
        if self.penalty is not None:
            clf_kwargs["penalty"] = self.penalty

        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(**clf_kwargs)),
        ])

    def _prepare_features(self, X: Any) -> np.ndarray:
        """Ensure features are converted to 2D statistical representation."""
        if isinstance(X, list) or (isinstance(X, np.ndarray) and X.ndim == 3):
            return self.extractor.transform(X)
        elif isinstance(X, np.ndarray) and X.ndim == 2:
            return X
        else:
            raise ValueError(f"Unsupported feature input shape or type: {type(X)}")

    def fit(self, X: Any, y: np.ndarray) -> "VideoLogisticRegressionBaseline":
        """Fit pipeline strictly on training data."""
        X_mat = self._prepare_features(X)
        y_arr = np.asarray(y).astype(int)

        self.pipeline = self._build_pipeline()
        self.pipeline.fit(X_mat, y_arr)
        return self

    def predict(self, X: Any) -> np.ndarray:
        """Predict binary class labels."""
        if self.pipeline is None:
            raise ValueError("Model is not fitted. Call fit() first.")
        X_mat = self._prepare_features(X)
        return self.pipeline.predict(X_mat)

    def predict_proba(self, X: Any) -> np.ndarray:
        """Predict class probabilities."""
        if self.pipeline is None:
            raise ValueError("Model is not fitted. Call fit() first.")
        X_mat = self._prepare_features(X)
        return self.pipeline.predict_proba(X_mat)

    def score(self, X: Any, y: np.ndarray) -> float:
        """Compute mean accuracy on given test data and labels."""
        if self.pipeline is None:
            raise ValueError("Model is not fitted. Call fit() first.")
        X_mat = self._prepare_features(X)
        return float(self.pipeline.score(X_mat, y))

    @property
    def coefficients_(self) -> Optional[np.ndarray]:
        """Return model coefficients mapped to statistical features."""
        if self.pipeline is None:
            return None
        return self.pipeline.named_steps["classifier"].coef_


class VideoRandomForestBaseline(BaseEstimator, ClassifierMixin):
    """Random Forest baseline classifier for participant-level video screening.

    Wraps a leak-free Scikit-learn Pipeline with:
    1. ParticipantStatisticalFeatureExtractor (if raw sequence tensors are passed).
    2. SimpleImputer (median strategy).
    3. StandardScaler.
    4. RandomForestClassifier (class_weight='balanced').
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = 5,
        min_samples_split: int = 5,
        min_samples_leaf: int = 2,
        random_state: int = DEFAULT_RANDOM_SEED,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        feature_subset: str = "all",
    ) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.confidence_threshold = confidence_threshold
        self.feature_subset = feature_subset

        self.extractor = ParticipantStatisticalFeatureExtractor(
            confidence_threshold=confidence_threshold,
            feature_subset=feature_subset,
        )
        self.pipeline: Optional[Pipeline] = None

    def _build_pipeline(self) -> Pipeline:
        """Construct scikit-learn pipeline."""
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=self.n_estimators,
                    max_depth=self.max_depth,
                    min_samples_split=self.min_samples_split,
                    min_samples_leaf=self.min_samples_leaf,
                    random_state=self.random_state,
                    class_weight="balanced",
                ),
            ),
        ])

    def _prepare_features(self, X: Any) -> np.ndarray:
        """Ensure features are converted to 2D statistical representation."""
        if isinstance(X, list) or (isinstance(X, np.ndarray) and X.ndim == 3):
            return self.extractor.transform(X)
        elif isinstance(X, np.ndarray) and X.ndim == 2:
            return X
        else:
            raise ValueError(f"Unsupported feature input shape or type: {type(X)}")

    def fit(self, X: Any, y: np.ndarray) -> "VideoRandomForestBaseline":
        """Fit pipeline strictly on training data."""
        X_mat = self._prepare_features(X)
        y_arr = np.asarray(y).astype(int)

        self.pipeline = self._build_pipeline()
        self.pipeline.fit(X_mat, y_arr)
        return self

    def predict(self, X: Any) -> np.ndarray:
        """Predict binary class labels."""
        if self.pipeline is None:
            raise ValueError("Model is not fitted. Call fit() first.")
        X_mat = self._prepare_features(X)
        return self.pipeline.predict(X_mat)

    def predict_proba(self, X: Any) -> np.ndarray:
        """Predict class probabilities."""
        if self.pipeline is None:
            raise ValueError("Model is not fitted. Call fit() first.")
        X_mat = self._prepare_features(X)
        return self.pipeline.predict_proba(X_mat)

    def score(self, X: Any, y: np.ndarray) -> float:
        """Compute mean accuracy on given test data and labels."""
        if self.pipeline is None:
            raise ValueError("Model is not fitted. Call fit() first.")
        X_mat = self._prepare_features(X)
        return float(self.pipeline.score(X_mat, y))

    @property
    def feature_importances_(self) -> Optional[np.ndarray]:
        """Return Gini feature importances."""
        if self.pipeline is None:
            return None
        return self.pipeline.named_steps["classifier"].feature_importances_
