# Member 1 & Member 2 Handoff: Screening Persistence & Retrieval

## Architecture Boundary & Ownership

- **Member 1 owns**:
  - Multimodal analysis (`POST /api/screenings/analyze`)
  - Audio, video, and text NER inference pipelines
  - Multimodal discordance analysis and score fusion
- **Member 2 owns**:
  - PostgreSQL & SQLAlchemy database schemas and migrations
  - Screening persistence and retrieval service (`ScreeningService`)
  - Endpoints:
    - `GET /api/mothers/{mother_id}/screenings` (screening history, newest first)
    - `GET /api/screenings/{screening_id}` (individual screening details)

---

## Screening Persistence Service

Member 1 invokes Member 2's persistence service at the end of the `/api/screenings/analyze` execution pipeline to safely commit multimodal screening results to the database.

### Import Path
```python
from backend.services.screening_service import (
    screening_service,
    MotherNotFoundError,
    ScreeningPersistenceError,
)
from backend.schemas.screening import ScreeningPersistRequest
```

### Method Signature
```python
screening_service.persist_screening(
    db: Session,
    data: ScreeningPersistRequest,
) -> Screening
```

---

## Input Data Specification (`ScreeningPersistRequest`)

```python
payload = ScreeningPersistRequest(
    mother_id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
    instrument="EPDS",
    total_score=14,
    risk_classification="high",
    q10_safety_alert=True,
    submitted_answers={"EPDS_Q01": 1, "EPDS_Q10": 2},
    item_scores={"EPDS_Q01": 1, "EPDS_Q10": 2},
    screening_status="completed",          # 'completed' | 'partially_completed' | 'failed'
    fusion_status="completed",             # 'completed' | 'not_available' | 'insufficient_data' | 'failed'
    modality_status={
        "text": "completed",               # 'completed' | 'unavailable' | 'failed' | 'not_requested'
        "audio": "completed",
        "video": "unavailable",
    },
    model_metadata={
        "pipeline_version": "v1.3.0",
        "audio_model": "cnn_audio_v1",
        "text_ner_model": "v1.3.0",
        "fusion_strategy": "late_fusion_weighted",
    },
    multimodal_scores={
        "text_risk_probability": 0.72,
        "audio_risk_probability": 0.65,
        "fused_probability": 0.69,
    },
    notes="Patient completed questionnaire and speech sample at clinic kiosk.",
)
```

### Field Definitions & Guarantees
1. **`mother_id`** *(Required UUID)*:
   - Must reference a registered Mother record in the `mothers` table.
   - If the mother does not exist, `MotherNotFoundError` is raised immediately.
2. **`total_score` & `risk_classification`** *(Required)*:
   - Derived directly from validated EPDS questionnaire scoring.
3. **`q10_safety_alert`** *(Required boolean)*:
   - **Non-negotiable invariant**: Must be set to `True` whenever EPDS Question 10 is > 0.
   - It is never overridden by a low total score, audio/video scores, or multimodal fusion.
4. **`screening_status`**:
   - `completed`: All requested modalities processed successfully.
   - `partially_completed`: Some modalities succeeded, others were unavailable.
   - `failed`: Pipeline encountered an unrecoverable error.
5. **`modality_status`**:
   - Each modality must report `completed`, `unavailable`, `failed`, or `not_requested`.
   - **Crucial Clinical Rule**: Missing or unavailable modalities are **never** treated as negative or low-risk predictions.
6. **`fusion_status`**:
   - `completed`: Valid multimodal fusion was computed.
   - `not_available` or `insufficient_data`: Fusion was skipped or insufficient data was present.
   - If absent, Member 2 defaults to `not_available` and **never** fabricates a combined score.
7. **`model_metadata` & `multimodal_scores`**:
   - Optional dictionaries stored verbatim as JSON.

---

## Transaction & Error Behavior

- **Atomic Commit / Rollback**:
  - The persistence operation executes inside a single database transaction.
  - If any exception or database integrity violation occurs, `db.rollback()` is invoked automatically before raising `ScreeningPersistenceError`.
- **Exception Types**:
  - `MotherNotFoundError`: Raised when the `mother_id` does not exist (HTTP 404 in API callers).
  - `ScreeningPersistenceError`: Raised on constraint violations or unexpected database failures (HTTP 500 in API callers).

---

## Example Member 1 Integration Code Snippet

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.screening_service import (
    screening_service,
    MotherNotFoundError,
    ScreeningPersistenceError,
)
from backend.schemas.screening import ScreeningPersistRequest, ScreeningResponse

router = APIRouter(prefix="/api/screenings", tags=["Multimodal Screening Analysis"])

@router.post("/analyze", response_model=ScreeningResponse, status_code=status.HTTP_201_CREATED)
def analyze_screening(
    request: AnalysisRequestPayload,
    db: Session = Depends(get_db),
):
    # 1. Member 1 runs multimodal inference pipelines
    analysis_results = run_multimodal_analysis(request)
    
    # 2. Member 1 builds the persistence payload
    persist_payload = ScreeningPersistRequest(
        mother_id=request.mother_id,
        instrument="EPDS",
        total_score=analysis_results.epds_score,
        risk_classification=analysis_results.risk_tier,
        q10_safety_alert=analysis_results.q10_alert,
        submitted_answers=analysis_results.answers,
        item_scores=analysis_results.item_scores,
        screening_status=analysis_results.status,
        fusion_status=analysis_results.fusion_status,
        modality_status=analysis_results.modality_status,
        model_metadata=analysis_results.metadata,
        multimodal_scores=analysis_results.scores,
    )

    # 3. Member 1 invokes Member 2 persistence service
    try:
        saved_record = screening_service.persist_screening(db, persist_payload)
        return ScreeningResponse.model_validate(saved_record)
    except MotherNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ScreeningPersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save screening result.")
```

