"""Reusable inference interface and Pydantic v2 schemas for Text Named Entity Recognition.

Engineered for seamless integration into FastAPI backend endpoints and future multimodal fusion layers.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from pipelines.text_ner.config import MODELS_DIR
from pipelines.text_ner.models import TextNERModel


class TextEntitySpan(BaseModel):
    """Pydantic v2 schema representing an individual extracted entity span."""

    text: str = Field(..., description="Verbatim extracted entity text span")
    label: str = Field(..., description="Entity category label (e.g., MMLite)")
    start: int = Field(..., ge=0, description="0-based character start index in source text")
    end: int = Field(..., ge=0, description="0-based character end index in source text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence score")


class TextNEROutput(BaseModel):
    """Pydantic v2 schema for end-to-end text NER response."""

    entities: List[TextEntitySpan] = Field(default_factory=list, description="List of extracted entity spans")
    total_entities_detected: int = Field(..., ge=0, description="Total count of extracted entities")
    processed_character_count: int = Field(..., ge=0, description="Total characters processed")
    model_version: str = Field(default="1.0.0", description="Text NER model release version")


class TextNERPredictor:
    """Thread-safe prediction service for extracting biomedical entities from free-text strings."""

    DEFAULT_MODEL_PATH: Path = MODELS_DIR / "v1.3.0" / "text_ner_model.joblib"
    LEGACY_V120_MODEL_PATH: Path = MODELS_DIR / "v1.2.0" / "text_ner_model.joblib"
    FALLBACK_MODEL_PATH: Path = MODELS_DIR / "text_ner_model.joblib"
    MAX_SAFE_CHARACTER_LIMIT: int = 50000

    @classmethod
    def resolve_model_path(
        cls,
        model_path: Optional[Path] = None,
        model_version: Optional[str] = None,
    ) -> Path:
        """Resolve an explicit model path or select v1.3.0 default with v1.2.0 compatibility."""
        if model_path is not None:
            return Path(model_path)
        if model_version is not None:
            normalized = model_version.strip().lstrip("v")
            if normalized == "1.3.0":
                return cls.DEFAULT_MODEL_PATH
            if normalized == "1.2.0":
                return cls.LEGACY_V120_MODEL_PATH
            raise ValueError(
                f"Unsupported text NER model_version '{model_version}'. Expected '1.3.0' or '1.2.0'."
            )
        for candidate in (cls.DEFAULT_MODEL_PATH, cls.FALLBACK_MODEL_PATH, cls.LEGACY_V120_MODEL_PATH):
            if candidate.exists():
                return candidate
        return cls.DEFAULT_MODEL_PATH

    def __init__(
        self,
        model_path: Optional[Path] = None,
        max_characters: int = MAX_SAFE_CHARACTER_LIMIT,
        model_version: Optional[str] = None,
    ) -> None:
        self.model_path = self.resolve_model_path(model_path=model_path, model_version=model_version)
        self.max_characters = max_characters
        self._model: Optional[TextNERModel] = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the persisted model artifact or raise an informative error."""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Text NER model checkpoint missing at: {self.model_path}. "
                f"Please execute `python -m pipelines.text_ner.train_v130` (or `train`) "
                f"to generate the artifact before serving inference."
            )
        self._model = TextNERModel.load(self.model_path)

    def predict(self, text: Optional[str]) -> TextNEROutput:
        """Extract structured entity spans from a raw text input string.

        Safely handles empty input, whitespace, and excessively long strings.
        Does not persist, print, or log raw input text.
        """
        if text is None or not isinstance(text, str):
            return TextNEROutput(
                entities=[],
                total_entities_detected=0,
                processed_character_count=0,
            )

        # Enforce safe character limit to defend against memory exhaustion
        sanitized_text = text[: self.max_characters]
        char_count = len(sanitized_text)

        if not sanitized_text.strip():
            return TextNEROutput(
                entities=[],
                total_entities_detected=0,
                processed_character_count=char_count,
            )

        if self._model is None:
            raise RuntimeError("Text NER predictor model is not initialized.")

        raw_spans = self._model.predict_text(sanitized_text)
        validated_spans = [
            TextEntitySpan(
                text=span["text"],
                label=span["label"],
                start=span["start"],
                end=span["end"],
                confidence=span["confidence"],
            )
            for span in raw_spans
        ]

        return TextNEROutput(
            entities=validated_spans,
            total_entities_detected=len(validated_spans),
            processed_character_count=char_count,
            model_version=getattr(self._model, "model_version", "1.0.0"),
        )

    def get_model_metadata(self) -> Dict[str, Any]:
        """Return diagnostic metadata about the loaded model."""
        if self._model is None:
            return {"status": "uninitialized"}
        return {
            "model_path": str(self.model_path),
            "model_version": getattr(self._model, "model_version", "1.0.0"),
            "is_fitted": self._model.is_fitted,
            "classes": list(self._model.classes_) if self._model.classes_ is not None else [],
            "classifier_type": self._model.classifier_type,
            "feature_window": self._model.window,
            "feature_version": getattr(self._model, "feature_version", "v1"),
            "use_viterbi": bool(getattr(self._model, "use_viterbi", False)),
        }

