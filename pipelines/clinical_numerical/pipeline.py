"""End-to-end inference and orchestration pipeline for clinical numerical features.

Postpartum Depression (PPD) Multimodal Recognition Research Prototype.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

from .config import (
    ARTIFACTS_DIR,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    DECISION_THRESHOLD,
)
from .preprocessor import ClinicalPreprocessor
from .models import get_model


class ClinicalNumericalPipeline:
    """Unified runtime pipeline for clinical numerical PPD screening."""

    def __init__(
        self,
        model_name: str = "hist_gradient_boosting",
        artifacts_dir: Path = ARTIFACTS_DIR,
    ):
        self.model_name = model_name
        self.artifacts_dir = Path(artifacts_dir)
        self.preprocessor: Optional[ClinicalPreprocessor] = None
        self.model: Optional[Any] = None
        self.is_ready = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "ClinicalNumericalPipeline":
        """Fit preprocessor and baseline model on training records."""
        self.preprocessor = ClinicalPreprocessor()
        X_trans = self.preprocessor.fit_transform(X)
        self.model = get_model(self.model_name)
        self.model.fit(X_trans, y.values)
        self.is_ready = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probability of high risk for Postpartum Depression (class 1)."""
        self._ensure_ready()
        X_trans = self.preprocessor.transform(X)
        probs = self.model.predict_proba(X_trans)[:, 1]
        return np.asarray(probs, dtype=float)

    def predict(self, X: pd.DataFrame, threshold: float = DECISION_THRESHOLD) -> np.ndarray:
        """Predict binary screening class (1 = High Risk, 0 = Low Risk)."""
        probs = self.predict_proba(X)
        return (probs >= threshold).astype(int)

    def predict_single(
        self,
        record: Dict[str, Any],
        threshold: float = DECISION_THRESHOLD,
    ) -> Dict[str, Any]:
        """Inference endpoint for a single participant survey record."""
        df_single = pd.DataFrame([record])
        prob = float(self.predict_proba(df_single)[0])
        pred = int(prob >= threshold)

        if prob >= 0.70:
            category = "HIGH_RISK"
        elif prob >= 0.40:
            category = "MODERATE_RISK"
        else:
            category = "LOW_RISK"

        return {
            "participant_id": record.get("participant_id", "UNKNOWN"),
            "predicted_risk_probability": round(prob, 4),
            "predicted_class": pred,
            "risk_category": category,
            "decision_threshold": threshold,
            "model_utilized": self.model_name,
            "data_origin": "REAL_CLINICAL_SURVEY",
            "clinical_disclaimer": "Research Prototype Benchmark Only — Not Clinically Validated for Medical Diagnosis",
        }

    def save(self, directory: Optional[Path] = None) -> None:
        """Serialize pipeline components to disk."""
        target_dir = Path(directory) if directory else self.artifacts_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        if not self.is_ready:
            raise RuntimeError("Pipeline must be fitted or loaded before saving.")
        self.preprocessor.save(target_dir / "preprocessor.joblib")
        joblib.dump(self.model, target_dir / f"{self.model_name}.joblib")

    def load(
        self_or_dir: Any = None,
        directory: Optional[Union[str, Path]] = None,
        model_name: Optional[str] = None,
    ) -> "ClinicalNumericalPipeline":
        """Load fitted pipeline components from disk.

        Can be called either as a class factory:
            pipeline = ClinicalNumericalPipeline.load("models/clinical_numerical")
        or as an instance method:
            pipeline = ClinicalNumericalPipeline(model_name="random_forest")
            pipeline.load()
        """
        if isinstance(self_or_dir, ClinicalNumericalPipeline):
            self = self_or_dir
            target_dir = Path(directory) if directory else self.artifacts_dir
            if model_name is not None:
                self.model_name = model_name
        else:
            # Called directly on class: ClinicalNumericalPipeline.load(...)
            target_dir = Path(self_or_dir) if self_or_dir else ARTIFACTS_DIR
            target_name = model_name if model_name is not None else "hist_gradient_boosting"
            self = ClinicalNumericalPipeline(model_name=target_name, artifacts_dir=target_dir)

        preprocessor_path = target_dir / "preprocessor.joblib"
        model_path = target_dir / f"{self.model_name}.joblib"

        if not preprocessor_path.exists():
            raise FileNotFoundError(f"Preprocessor artifact not found at {preprocessor_path}")
        if not model_path.exists():
            raise FileNotFoundError(f"Model artifact not found at {model_path}")

        self.preprocessor = ClinicalPreprocessor.load(preprocessor_path)
        self.model = joblib.load(model_path)
        self.is_ready = True
        return self

    def _ensure_ready(self) -> None:
        if not self.is_ready or self.preprocessor is None or self.model is None:
            raise RuntimeError(
                "ClinicalNumericalPipeline is not ready. Call fit() or load() before making predictions."
            )

