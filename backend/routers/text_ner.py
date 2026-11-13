"""FastAPI router for Biomedical Entity Extraction (Text NER).

Exposes POST /api/text-ner/extract reusing pipelines.text_ner.inference.TextNERPredictor.
Strictly performs biomedical span extraction (MMLite) — does NOT output PPD diagnoses
or probabilities and never overrides EPDS questionnaire scoring or Item 10 safety logic.
"""

from fastapi import APIRouter, Depends

from backend.schemas.text_ner import TextNERExtractRequest, TextNEROutput
from backend.services.text_ner_service import TextNERService, get_text_ner_service

router = APIRouter(
    prefix="/api/text-ner",
    tags=["Biomedical Entity Extraction"],
)


@router.post(
    "/extract",
    response_model=TextNEROutput,
    summary="Extract biomedical entities from text",
    description=(
        "Performs biomedical Named Entity Recognition (MMLite spans) on narrative text "
        "using the preloaded TextNERPredictor. Strictly provides biomedical entity extraction — "
        "it does NOT provide a Postpartum Depression diagnosis or diagnostic probability, and "
        "must NEVER override EPDS scoring or Question 10 self-harm safety escalation."
    ),
)
def extract_biomedical_entities(
    payload: TextNERExtractRequest,
    service: TextNERService = Depends(get_text_ner_service),
) -> TextNEROutput:
    """Extract biomedical entity spans from narrative input text."""
    return service.extract_entities(payload.text)

