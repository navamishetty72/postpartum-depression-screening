"""FastAPI router for Central Multimodal Screening Orchestration.

Exposes:
- POST /api/screenings/analyze: Multipart/form-data endpoint orchestrating clinical numerical,
  biomedical text NER, and acoustic/visual screening inputs without fabricating predictions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile

from backend.schemas.screening import ScreeningAnalysisResponse
from backend.services.screening_service import (
    ScreeningOrchestrationService,
    get_screening_service,
)

router = APIRouter(
    prefix="/api/screenings",
    tags=["Central Screening Orchestration"],
)


@router.post(
    "/analyze",
    response_model=ScreeningAnalysisResponse,
    summary="Analyze multimodal screening inputs for postpartum depression risk",
    description=(
        "Central multimodal analysis orchestrator accepting multipart/form-data. "
        "Coordinates validated 46-feature clinical numerical ML screening, biomedical "
        "text entity extraction (Text NER), and safely reports unavailable statuses for "
        "unimplemented audio and video models. Preserves partial completion states when "
        "individual modalities fail."
    ),
)
async def analyze_screening(
    motherId: Optional[str] = Form(None, description="Registered mother / participant identifier"),
    mother_id: Optional[str] = Form(None, description="Alternative snake_case mother identifier"),
    modalities: str = Form(
        ...,
        description='JSON stringified modalities, e.g. \'{"clinical": true, "text": true}\' or \'["clinical", "text"]\'',
    ),
    consentConfirmed: Optional[str] = Form(
        None,
        description="Boolean string ('true'/'false') confirming maternal consent",
    ),
    consent_confirmed: Optional[str] = Form(
        None,
        description="Alternative snake_case consent flag",
    ),
    clinical_features: Optional[str] = Form(
        None,
        description="JSON string containing the complete 46 clinical survey predictors (required if clinical=true)",
    ),
    files_text: Optional[UploadFile] = File(
        None,
        description="Optional narrative text file (.txt, .json) for biomedical entity extraction",
    ),
    files_voice: Optional[UploadFile] = File(
        None,
        description="Optional acoustic audio file (.wav, .mp3)",
    ),
    files_video: Optional[UploadFile] = File(
        None,
        description="Optional video recording file (.mp4)",
    ),
    text_content: Optional[str] = Form(
        None,
        description="Alternative direct narrative text string for text NER",
    ),
    service: ScreeningOrchestrationService = Depends(get_screening_service),
) -> ScreeningAnalysisResponse:
    """Orchestrate central multimodal screening analysis."""
    effective_mother_id = motherId if motherId is not None else mother_id
    effective_consent = consentConfirmed if consentConfirmed is not None else consent_confirmed

    files_text_bytes: Optional[bytes] = None
    if files_text is not None:
        files_text_bytes = await files_text.read()

    files_voice_bytes: Optional[bytes] = None
    if files_voice is not None:
        files_voice_bytes = await files_voice.read()

    files_video_bytes: Optional[bytes] = None
    if files_video is not None:
        files_video_bytes = await files_video.read()

    return await service.orchestrate_screening(
        mother_id=effective_mother_id,
        consent_confirmed=effective_consent or False,
        modalities_raw=modalities,
        clinical_features_raw=clinical_features,
        files_text_bytes=files_text_bytes,
        text_content=text_content,
        files_voice_bytes=files_voice_bytes,
        files_video_bytes=files_video_bytes,
    )

