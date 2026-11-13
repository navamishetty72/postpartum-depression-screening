"""Service layer wrapping TextNERPredictor for FastAPI lifecycle management.

Loads the biomedical NER predictor once on application startup rather than per request,
handles missing artifacts or inference errors safely, and never logs patient narratives
or extracted entity strings containing sensitive user text.
"""

import logging
import threading
from typing import Callable, Optional
from fastapi import HTTPException

from pipelines.text_ner.inference import TextNEROutput, TextNERPredictor

logger = logging.getLogger("ppd.text_ner")


class TextNERService:
    """Singleton lifecycle wrapper around pipelines.text_ner.inference.TextNERPredictor."""

    def __init__(
        self,
        predictor_factory: Optional[Callable[[], TextNERPredictor]] = None,
        predictor: Optional[TextNERPredictor] = None,
    ) -> None:
        self._predictor_factory: Callable[[], TextNERPredictor] = (
            predictor_factory or TextNERPredictor
        )
        self._predictor: Optional[TextNERPredictor] = predictor
        self._load_error: Optional[str] = None
        self._startup_attempted: bool = predictor is not None
        self._lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        """Whether a fitted predictor instance is currently ready for inference."""
        return self._predictor is not None

    def startup(self) -> None:
        """Load the TextNERPredictor checkpoint once during application startup."""
        with self._lock:
            if self._predictor is not None:
                self._startup_attempted = True
                return

            self._startup_attempted = True
            try:
                predictor = self._predictor_factory()
                self._predictor = predictor
                self._load_error = None
                metadata = predictor.get_model_metadata()
                logger.info(
                    "Biomedical text NER predictor loaded at startup: model_version=%s, classifier=%s",
                    metadata.get("model_version", "unknown"),
                    metadata.get("classifier_type", "unknown"),
                )
            except FileNotFoundError as exc:
                self._predictor = None
                self._load_error = (
                    "Biomedical entity extraction model artifact is missing or unavailable."
                )
                logger.warning(
                    "Biomedical text NER model artifact missing during startup (error_type=%s); "
                    "POST /api/text-ner/extract will return HTTP 503.",
                    type(exc).__name__,
                )
            except Exception as exc:
                self._predictor = None
                self._load_error = (
                    "Biomedical entity extraction model failed to initialize during startup."
                )
                logger.error(
                    "Biomedical text NER startup failed (error_type=%s).",
                    type(exc).__name__,
                )

    def shutdown(self) -> None:
        """Release reference cleanly on application shutdown."""
        with self._lock:
            if self._predictor is not None:
                logger.info("Shutting down biomedical text NER service.")
            self._predictor = None
            self._startup_attempted = False
            self._load_error = None

    def _get_predictor(self) -> TextNERPredictor:
        """Return initialized predictor or raise HTTP 503 if unavailable."""
        if not self._startup_attempted:
            self.startup()

        if self._predictor is None:
            raise HTTPException(
                status_code=503,
                detail=self._load_error
                or "Biomedical entity extraction model artifact is missing or unavailable.",
            )
        return self._predictor

    def extract_entities(self, text: str) -> TextNEROutput:
        """Execute biomedical NER via the shared TextNERPredictor instance.

        Never logs raw text narratives or extracted span strings.
        Does not emit PPD diagnostic claims or probabilities, and cannot alter EPDS scoring.
        """
        predictor = self._get_predictor()

        try:
            result = predictor.predict(text)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "Biomedical entity extraction inference failed: error_type=%s, input_chars=%d",
                type(exc).__name__,
                len(text),
            )
            raise HTTPException(
                status_code=500,
                detail="Biomedical entity extraction failed due to an internal inference error.",
            ) from exc

        logger.info(
            "Biomedical entity extraction completed: input_chars=%d, entities_detected=%d, model_version=%s",
            result.processed_character_count,
            result.total_entities_detected,
            result.model_version,
        )
        return result


# Shared application service singleton loaded once on FastAPI startup
text_ner_service = TextNERService()


def get_text_ner_service() -> TextNERService:
    """FastAPI dependency returning the shared TextNERService singleton."""
    return text_ner_service

