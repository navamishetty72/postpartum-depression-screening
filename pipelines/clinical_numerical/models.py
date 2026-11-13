"""Model definitions for clinical numerical baseline classifiers.

Implements Logistic Regression, Random Forest, and HistGradientBoosting.
"""

from typing import Dict, Any, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.base import BaseEstimator

from .config import MODEL_CONFIGS, RANDOM_SEED


def get_model(model_name: str, custom_params: Optional[Dict[str, Any]] = None) -> BaseEstimator:
    """Instantiate a baseline classifier with reproducible configuration.

    Args:
        model_name: One of 'logistic_regression', 'random_forest', 'hist_gradient_boosting'.
        custom_params: Optional parameter overrides.

    Returns:
        BaseEstimator: Unfitted scikit-learn classifier.
    """
    if model_name not in MODEL_CONFIGS:
        valid_models = list(MODEL_CONFIGS.keys())
        raise ValueError(f"Unknown model_name '{model_name}'. Valid options: {valid_models}")

    params = dict(MODEL_CONFIGS[model_name])
    if custom_params:
        params.update(custom_params)

    if model_name == "logistic_regression":
        return LogisticRegression(**params)
    elif model_name == "random_forest":
        return RandomForestClassifier(**params)
    elif model_name == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(**params)
    else:
        raise ValueError(f"Unhandled model name: {model_name}")

