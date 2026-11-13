"""Pydantic v2 schemas for the Biomedical Text NER extraction endpoint.

Reuses the canonical output schemas from pipelines.text_ner.inference so backend
responses remain 100% consistent with the ML text branch contract.
"""

from pydantic import BaseModel, ConfigDict, Field

from pipelines.text_ner.inference import (
    TextEntitySpan,
    TextNEROutput,
    TextNERPredictor,
)


class TextNERExtractRequest(BaseModel):
    """Request payload for biomedical Named Entity Recognition (NER)."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        ...,
        max_length=TextNERPredictor.MAX_SAFE_CHARACTER_LIMIT,
        description=(
            "Narrative or forum-style text for biomedical entity extraction (MMLite spans). "
            "Maximum 50,000 characters. Output is strictly for entity extraction and "
            "never constitutes a PPD diagnosis or clinical severity score."
        ),
    )


__all__ = [
    "TextNERExtractRequest",
    "TextEntitySpan",
    "TextNEROutput",
]

