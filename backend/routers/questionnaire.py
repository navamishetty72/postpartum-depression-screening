"""FastAPI Router for EPDS Questionnaire endpoints.

Exposes GET /api/questionnaire/epds and POST /api/questionnaire/epds/submit.
"""

from fastapi import APIRouter, Depends, Query
from backend.schemas.questionnaire import (
    EPDSQuestionnaireResponse,
    EPDSSubmissionRequest,
    EPDSSubmissionResponse,
)
from backend.services.questionnaire_service import (
    EPDSQuestionnaireService,
    questionnaire_service,
)

router = APIRouter(prefix="/api/questionnaire", tags=["EPDS Questionnaire"])


@router.get("/epds", response_model=EPDSQuestionnaireResponse)
def get_epds_questionnaire(
    lang: str = Query(default="en", description="ISO 639-1 language code (en, hi, bn, kn, ta, te, ml, mr)"),
    service: EPDSQuestionnaireService = Depends(lambda: questionnaire_service),
) -> EPDSQuestionnaireResponse:
    """Retrieve the full 10-item EPDS question bank, metadata, options, and guidance.

    Accepts optional lang query parameter to retrieve verified clinical translations.
    """
    return service.get_questionnaire(language=lang)


@router.post("/epds/submit", response_model=EPDSSubmissionResponse)
def submit_epds_questionnaire(
    submission: EPDSSubmissionRequest,
    service: EPDSQuestionnaireService = Depends(lambda: questionnaire_service),
) -> EPDSSubmissionResponse:
    """Validate completed questionnaire responses, calculate score, and enforce Item 10 safety."""
    return service.calculate_score(submission)
