"""Service layer for Clinical Numerical ML screening inference.

Manages pipeline lifecycle, loads the trained Random Forest model artifact once at startup,
delegates to ClinicalNumericalPipeline.predict_single(), and prevents exposure of sensitive
patient features in application logs.
"""

import logging
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from fastapi import HTTPException

from pipelines.clinical_numerical.config import ARTIFACTS_DIR
from pipelines.clinical_numerical.pipeline import ClinicalNumericalPipeline

logger = logging.getLogger("ppd.clinical_numerical")


class ClinicalScreeningService:
    """Singleton lifecycle wrapper around pipelines.clinical_numerical.pipeline.ClinicalNumericalPipeline."""

    def __init__(
        self,
        artifacts_dir: Optional[Path] = None,
        model_name: str = "random_forest",
        pipeline_loader: Optional[Callable[..., ClinicalNumericalPipeline]] = None,
        pipeline: Optional[ClinicalNumericalPipeline] = None,
    ) -> None:
        self.artifacts_dir: Path = Path(artifacts_dir) if artifacts_dir else ARTIFACTS_DIR
        self.model_name: str = model_name
        self._pipeline_loader: Callable[..., ClinicalNumericalPipeline] = (
            pipeline_loader or ClinicalNumericalPipeline.load
        )
        self._pipeline: Optional[ClinicalNumericalPipeline] = pipeline
        self._load_error: Optional[str] = None
        self._startup_attempted: bool = pipeline is not None
        self._lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        """Whether a fitted pipeline instance is ready for inference."""
        return self._pipeline is not None and getattr(self._pipeline, "is_ready", False)

    def startup(self) -> None:
        """Load the ClinicalNumericalPipeline once during application startup."""
        with self._lock:
            if self._pipeline is not None:
                self._startup_attempted = True
                return

            self._startup_attempted = True
            try:
                # Use ClinicalNumericalPipeline.load(directory, model_name=...)
                pipeline = self._pipeline_loader(
                    self.artifacts_dir,
                    model_name=self.model_name,
                )
                self._pipeline = pipeline
                self._load_error = None
                logger.info(
                    "Clinical numerical screening pipeline loaded at startup: model=%s, dir=%s",
                    self.model_name,
                    self.artifacts_dir,
                )
            except FileNotFoundError as exc:
                self._pipeline = None
                self._load_error = (
                    f"Clinical numerical model artifact is missing or unavailable ({exc})."
                )
                logger.warning(
                    "Clinical numerical model artifact missing during startup (error_type=%s); "
                    "POST /api/clinical/predict will return HTTP 503.",
                    type(exc).__name__,
                )
            except Exception as exc:
                self._pipeline = None
                self._load_error = (
                    f"Clinical numerical pipeline failed to initialize during startup ({type(exc).__name__}: {exc})."
                )
                logger.error(
                    "Clinical numerical pipeline startup failed: %s",
                    exc,
                    exc_info=True,
                )

    def shutdown(self) -> None:
        """Release pipeline reference cleanly on application shutdown."""
        with self._lock:
            if self._pipeline is not None:
                logger.info("Shutting down clinical numerical screening service.")
            self._pipeline = None
            self._startup_attempted = False
            self._load_error = None

    def _get_pipeline(self) -> ClinicalNumericalPipeline:
        """Return initialized pipeline or raise HTTP 503 if unavailable."""
        if not self._startup_attempted:
            self.startup()

        if self._pipeline is None or not getattr(self._pipeline, "is_ready", False):
            raise HTTPException(
                status_code=503,
                detail=self._load_error
                or "Clinical numerical model artifact is missing or unavailable. Service cannot process predictions.",
            )
        return self._pipeline

    def predict(
        self,
        mother_id: str,
        features: Dict[str, Any],
        threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Execute single-patient screening inference using the loaded pipeline.

        Never logs raw patient survey inputs or sensitive feature records.
        """
        pipeline = self._get_pipeline()

        # Build single record dictionary preserving exact participant identifier
        record = dict(features)
        record["participant_id"] = mother_id

        try:
            # Delegate to existing predict_single method without modifying preprocessing
            raw_result = pipeline.predict_single(record, threshold=threshold)
        except HTTPException:
            raise
        except ValueError as exc:
            logger.warning(
                "Clinical prediction feature validation error for mother_id=%s: %s",
                mother_id,
                exc,
            )
            raise HTTPException(
                status_code=422,
                detail=f"Clinical feature validation failed: {str(exc)}",
            )
        except Exception as exc:
            logger.error(
                "Clinical prediction failed for mother_id=%s (error_type=%s)",
                mother_id,
                type(exc).__name__,
            )
            raise HTTPException(
                status_code=500,
                detail="Clinical numerical prediction failed due to an internal inference error.",
            ) from exc

        return {
            "mother_id": mother_id,
            "status": "completed",
            "prediction": {
                "predicted_risk_probability": raw_result["predicted_risk_probability"],
                "predicted_class": raw_result["predicted_class"],
                "risk_category": raw_result["risk_category"],
                "decision_threshold": raw_result.get("decision_threshold", threshold),
            },
            "model_utilized": raw_result.get("model_utilized", self.model_name),
            "data_origin": raw_result.get("data_origin", "REAL_CLINICAL_SURVEY"),
            "clinical_disclaimer": raw_result.get(
                "clinical_disclaimer",
                "Research Prototype Benchmark Only — Not Clinically Validated for Medical Diagnosis",
            ),
        }


# Global singleton instance for production runtime
clinical_service = ClinicalScreeningService()


def get_clinical_service() -> ClinicalScreeningService:
    """FastAPI dependency provider for the ClinicalScreeningService singleton."""
    return clinical_service

