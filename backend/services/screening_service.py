"""Screening persistence and retrieval service for MIORA clinical backend.

Member 1 owns multimodal analysis; Member 2 owns storing and retrieving its results.
This service provides a transactional persistence function that Member 1 can call
after `/api/screenings/analyze` completes.
"""

import logging
from typing import List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.mother import Mother
from backend.models.screening import Screening
from backend.schemas.screening import ScreeningPersistRequest

logger = logging.getLogger("ppd.services.screening")


class ScreeningPersistenceError(Exception):
    """Raised when screening persistence fails (e.g. invalid foreign key or transaction error)."""
    pass


class MotherNotFoundError(ScreeningPersistenceError):
    """Raised when the referenced mother does not exist."""
    pass


class ScreeningService:
    """Service providing transactional persistence and retrieval for screening records."""

    @staticmethod
    def persist_screening(
        db: Session,
        data: ScreeningPersistRequest,
    ) -> Screening:
        """Persist a completed screening session and multimodal prediction results.

        Guarantees:
        - Verifies that the referenced Mother exists; raises MotherNotFoundError if missing.
        - Persists screening_status, modality_status, and fusion_status strictly according to contract.
        - Stores model_metadata and multimodal_scores only when explicitly supplied.
        - Strictly preserves the EPDS Q10 safety alert.
        - Never fabricates or calculates combined risk scores. Missing modalities remain missing.
        - Executes within a database transaction; safely rolls back on any failure.
        """
        # 1. Verify mother existence
        mother = db.get(Mother, data.mother_id)
        if not mother:
            logger.warning("Screening persistence rejected: Mother [id=%s] not found", data.mother_id)
            raise MotherNotFoundError(f"Mother with ID '{data.mother_id}' does not exist.")

        # 2. Extract and format status dictionaries cleanly
        modality_status_dict = {
            mod: (val.value if hasattr(val, "value") else str(val))
            for mod, val in data.modality_status.items()
        }

        # Model metadata & multimodal scores: store only what Member 1 supplied, else empty dict
        stored_metadata = data.model_metadata if data.model_metadata is not None else {}
        stored_multimodal = data.multimodal_scores if data.multimodal_scores is not None else {}

        screening = Screening(
            mother_id=data.mother_id,
            instrument=data.instrument,
            total_score=data.total_score,
            risk_classification=data.risk_classification,
            q10_safety_alert=data.q10_safety_alert,
            submitted_answers=data.submitted_answers,
            item_scores=data.item_scores,
            screening_status=(
                data.screening_status.value
                if hasattr(data.screening_status, "value")
                else str(data.screening_status)
            ),
            fusion_status=(
                data.fusion_status.value
                if hasattr(data.fusion_status, "value")
                else str(data.fusion_status)
            ),
            modality_status=modality_status_dict,
            model_metadata=stored_metadata,
            multimodal_scores=stored_multimodal,
            notes=data.notes,
        )

        try:
            db.add(screening)
            db.commit()
            db.refresh(screening)
            logger.info(
                "Persisted screening [id=%s] for Mother [id=%s] with status=%s, q10_alert=%s",
                screening.id,
                screening.mother_id,
                screening.screening_status,
                screening.q10_safety_alert,
            )
            return screening
        except Exception as exc:
            db.rollback()
            logger.error(
                "Failed to persist screening for Mother [id=%s]: %s",
                data.mother_id,
                type(exc).__name__,
            )
            raise ScreeningPersistenceError(f"Database error during screening persistence: {exc}") from exc

    @staticmethod
    def get_screening_by_id(
        db: Session,
        screening_id: uuid.UUID,
    ) -> Optional[Screening]:
        """Retrieve an individual screening record by UUID."""
        return db.get(Screening, screening_id)

    @staticmethod
    def get_screenings_by_mother_id(
        db: Session,
        mother_id: uuid.UUID,
    ) -> Optional[List[Screening]]:
        """Retrieve all screenings for a specific mother, newest first.

        Returns None if the Mother does not exist.
        """
        mother = db.get(Mother, mother_id)
        if not mother:
            return None

        stmt = (
            select(Screening)
            .where(Screening.mother_id == mother_id)
            .order_by(desc(Screening.screening_date), desc(Screening.created_at))
        )
        return list(db.scalars(stmt).all())


screening_service = ScreeningService()
"""Service layer for central multimodal screening orchestration.

Coordinates single- and multi-modality screening workflows across clinical numerical
predictions, biomedical text NER, and placeholder interfaces for audio/video/fusion.
Protects sensitive patient data, preserves partial completion states, and provides
an explicit MotherValidator interface for Member 2 database integration.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional, Union
import uuid

from fastapi import Depends, HTTPException
from pydantic import ValidationError

from backend.ml.fusion_engine import (
    MultimodalFusionEngine,
    NonNegativeStackingFusionStrategy,
    fusion_engine,
    get_fusion_engine,
)
from backend.schemas.audio import AcousticFeatures
from backend.schemas.clinical_numerical import ClinicalFeatures
from backend.schemas.screening import (
    AudioModalityResult,
    ClinicalModalityResult,
    FusionModalityResult,
    ModalitiesSelection,
    ScreeningAnalysisResponse,
    TextModalityResult,
    VideoModalityResult,
)
from backend.services.audio_service import (
    AudioScreeningService,
    audio_service,
    get_audio_service,
)
from backend.services.clinical_service import (
    ClinicalScreeningService,
    clinical_service,
    get_clinical_service,
)
from backend.services.text_ner_service import (
    TextNERService,
    get_text_ner_service,
    text_ner_service,
)
from pipelines.text_ner.inference import TextNERPredictor

logger = logging.getLogger("ppd.screening_orchestrator")


class MotherValidator:
    """Interface for mother existence and cohort registry verification.

    Exposed for Member 2 to integrate with relational/SQL database persistence.
    """

    def validate_mother_exists(self, mother_id: str) -> bool:
        """Validate if mother_id exists in the registry.

        Default implementation verifies non-empty string identifier format.
        Member 2 will replace/override this with a database query.
        """
        if not mother_id or not isinstance(mother_id, str) or not mother_id.strip():
            return False
        return True


class EligibilityValidator:
    """Interface for participant self-declared postpartum eligibility verification.

    Postpartum eligibility (within 12 months of childbirth) is self-declared by the mother
    before screening. This is a clinical protocol requirement, NOT an automated classification.
    """

    def validate_eligibility(self, eligibility_confirmed: Optional[Union[bool, str]]) -> bool:
        """Verify whether the mother confirmed self-declared postpartum eligibility."""
        if eligibility_confirmed is True:
            return True
        if isinstance(eligibility_confirmed, str) and eligibility_confirmed.strip().lower() in ("true", "1", "yes"):
            return True
        return False


default_eligibility_validator = EligibilityValidator()


def get_eligibility_validator() -> EligibilityValidator:
    """FastAPI dependency provider for EligibilityValidator."""
    return default_eligibility_validator


class ScreeningOrchestrationService:
    """Central orchestrator coordinating multimodal PPD screening inferences."""

    def __init__(
        self,
        clinical_svc: Optional[ClinicalScreeningService] = None,
        text_svc: Optional[TextNERService] = None,
        audio_svc: Optional[AudioScreeningService] = None,
        mother_val: Optional[MotherValidator] = None,
        fusion_eng: Optional[MultimodalFusionEngine] = None,
        elig_val: Optional[EligibilityValidator] = None,
    ) -> None:
        self.clinical_service: ClinicalScreeningService = clinical_svc or clinical_service
        self.text_ner_service: TextNERService = text_svc or text_ner_service
        self.audio_service: AudioScreeningService = audio_svc or audio_service
        self.mother_validator: MotherValidator = mother_val or MotherValidator()
        self.fusion_engine: MultimodalFusionEngine = (
            fusion_eng
            if fusion_eng is not None
            else MultimodalFusionEngine(strategy=NonNegativeStackingFusionStrategy())
        )
        self.eligibility_validator: EligibilityValidator = elig_val or default_eligibility_validator

    async def orchestrate_screening(
        self,
        mother_id: Optional[str],
        consent_confirmed: Union[bool, str],
        modalities_raw: Union[str, Dict[str, Any], List[str]],
        clinical_features_raw: Optional[Union[str, Dict[str, Any]]] = None,
        audio_features_raw: Optional[Union[str, Dict[str, Any]]] = None,
        files_text_bytes: Optional[bytes] = None,
        text_content: Optional[str] = None,
        files_voice_bytes: Optional[bytes] = None,
        files_video_bytes: Optional[bytes] = None,
        eligibility_confirmed: Optional[Union[bool, str]] = None,
    ) -> ScreeningAnalysisResponse:
        """Execute multimodal screening analysis preserving partial completion states."""
        # 1. Validate Mother ID Format (422)
        if not mother_id or not isinstance(mother_id, str) or not mother_id.strip():
            raise HTTPException(
                status_code=422,
                detail="motherId is required and cannot be empty.",
            )
        clean_mother_id = mother_id.strip()

        # 2. Validate Modalities Syntax & Selection (422)
        try:
            modalities = ModalitiesSelection.from_raw(modalities_raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid modalities parameter: {exc}",
            )

        if not any([modalities.clinical, modalities.text, modalities.audio, modalities.video]):
            raise HTTPException(
                status_code=422,
                detail="At least one screening modality must be requested.",
            )

        # 3. Validate Clinical / Text Feature Payloads Schema & Syntax (422)
        clean_features = None
        if modalities.clinical:
            if not clinical_features_raw:
                raise HTTPException(
                    status_code=422,
                    detail="clinical_features JSON payload is required when clinical modality is requested.",
                )
            if isinstance(clinical_features_raw, str):
                try:
                    features_dict = json.loads(clinical_features_raw)
                except Exception as exc:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Invalid clinical_features JSON syntax: {exc}",
                    )
            elif isinstance(clinical_features_raw, dict):
                features_dict = clinical_features_raw
            else:
                raise HTTPException(
                    status_code=422,
                    detail="clinical_features must be a valid JSON object string or dictionary.",
                )
            try:
                validated_features = ClinicalFeatures.model_validate(features_dict)
                clean_features = validated_features.to_feature_dict()
            except (ValidationError, ValueError) as exc:
                raise HTTPException(
                    status_code=422,
                    detail=f"Clinical features schema validation failed: {exc}",
                )

        raw_text: Optional[str] = None
        if modalities.text:
            if files_text_bytes is not None and len(files_text_bytes) > 0:
                raw_text = files_text_bytes.decode("utf-8", errors="replace").strip()
            elif text_content is not None and text_content.strip():
                raw_text = text_content.strip()

            if not raw_text:
                raise HTTPException(
                    status_code=422,
                    detail="Text narrative content or files_text is required when text modality is requested.",
                )

            if len(raw_text) > TextNERPredictor.MAX_SAFE_CHARACTER_LIMIT:
                raise HTTPException(
                    status_code=422,
                    detail=f"Text input exceeds safe maximum limit of {TextNERPredictor.MAX_SAFE_CHARACTER_LIMIT} characters.",
                )

        # 4. Validate Mother Registration / Existence in Database (404)
        if not self.mother_validator.validate_mother_exists(clean_mother_id):
            raise HTTPException(
                status_code=404,
                detail=f"Registered mother record not found for motherId='{clean_mother_id}'.",
            )

        # 5. Validate Maternal Consent (400)
        is_consented = (
            consent_confirmed is True
            or (
                isinstance(consent_confirmed, str)
                and consent_confirmed.strip().lower() in ("true", "1", "yes")
            )
        )
        if not is_consented:
            raise HTTPException(
                status_code=400,
                detail="Maternal consent must be confirmed before submitting screening files for analysis.",
            )

        # 6. Validate Self-Declared Postpartum Eligibility (403)
        if not self.eligibility_validator.validate_eligibility(eligibility_confirmed):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Screening halted. Participant self-declared postpartum eligibility confirmation is required "
                    "before screening predictions can be generated."
                ),
            )

        # 7. Clinical Numerical Modality
        clinical_result: ClinicalModalityResult
        if modalities.clinical:
            # Execute clinical prediction
            try:
                raw_pred = self.clinical_service.predict(
                    mother_id=clean_mother_id,
                    features=clean_features,
                )
                clinical_result = ClinicalModalityResult(
                    status="completed",
                    prediction=raw_pred["prediction"],
                    model_version=raw_pred.get("model_utilized", "random_forest"),
                )
            except HTTPException as exc:
                logger.warning(
                    "Clinical service returned HTTP error during orchestration: status=%d, detail=%s",
                    exc.status_code,
                    exc.detail,
                )
                status_label = "unavailable" if exc.status_code == 503 else "failed"
                clinical_result = ClinicalModalityResult(
                    status=status_label,
                    error=str(exc.detail),
                )
            except Exception as exc:
                logger.error(
                    "Unexpected clinical inference error during orchestration: %s",
                    exc,
                    exc_info=True,
                )
                clinical_result = ClinicalModalityResult(
                    status="failed",
                    error="Clinical inference failed due to an internal error.",
                )
        else:
            clinical_result = ClinicalModalityResult(
                status="not_requested",
                prediction=None,
                model_version=None,
            )

        # 8. Biomedical Text NER Modality
        text_result: TextModalityResult
        if modalities.text:
            # Execute entity extraction
            try:
                ner_out = self.text_ner_service.extract_entities(raw_text)
                text_result = TextModalityResult(
                    status="completed",
                    processing_type="biomedical_ner",
                    entities=[e.model_dump() for e in ner_out.entities],
                    total_entities_detected=ner_out.total_entities_detected,
                    processed_character_count=ner_out.processed_character_count,
                    model_version=ner_out.model_version,
                )
            except HTTPException as exc:
                logger.warning(
                    "Text NER service returned HTTP error during orchestration: status=%d, detail=%s",
                    exc.status_code,
                    exc.detail,
                )
                status_label = "unavailable" if exc.status_code == 503 else "failed"
                text_result = TextModalityResult(
                    status=status_label,
                    processing_type="biomedical_ner",
                    error=str(exc.detail),
                )
            except Exception as exc:
                logger.error(
                    "Unexpected text NER extraction error during orchestration: %s",
                    exc,
                    exc_info=True,
                )
                text_result = TextModalityResult(
                    status="failed",
                    processing_type="biomedical_ner",
                    error="Biomedical entity extraction failed due to an internal error.",
                )
        else:
            text_result = TextModalityResult(
                status="not_requested",
                processing_type=None,
                entities=[],
            )

        # 6. Audio Modality (Experimental Synthetic Baseline / Research Pathway)
        audio_result: AudioModalityResult
        if modalities.audio:
            if audio_features_raw:
                # Parse JSON if passed as string
                if isinstance(audio_features_raw, str):
                    try:
                        audio_dict = json.loads(audio_features_raw)
                    except Exception as exc:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Invalid audio_features JSON syntax: {exc}",
                        )
                elif isinstance(audio_features_raw, dict):
                    audio_dict = audio_features_raw
                else:
                    raise HTTPException(
                        status_code=422,
                        detail="audio_features must be a valid JSON object string or dictionary.",
                    )

                # Validate against strict 7-feature physiological acoustic schema
                try:
                    validated_audio = AcousticFeatures.model_validate(audio_dict)
                except (ValidationError, ValueError) as exc:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Audio features schema validation failed: {exc}",
                    )

                # Execute audio inference or safe unavailable handling
                try:
                    raw_audio_pred = self.audio_service.predict(
                        features=validated_audio,
                        mother_id=clean_mother_id,
                        as_response=False,
                    )
                    audio_result = AudioModalityResult(
                        status="completed",
                        prediction=raw_audio_pred,
                        model_version=raw_audio_pred.get("model_utilized", "audio_random_forest_v1"),
                        message="Audio acoustic profile processed under experimental research protocol (non-predictive).",
                    )
                except HTTPException as exc:
                    status_label = "unavailable" if exc.status_code == 503 else "failed"
                    audio_result = AudioModalityResult(
                        status=status_label,
                        prediction=None,
                        model_version=None,
                        message=str(exc.detail),
                        error=str(exc.detail) if status_label == "failed" else None,
                    )
                except Exception as exc:
                    logger.error("Audio feature inference failed unexpectedly: %s", exc, exc_info=True)
                    audio_result = AudioModalityResult(
                        status="failed",
                        prediction=None,
                        model_version=None,
                        error="Acoustic feature inference failed due to an internal error.",
                    )
            elif files_voice_bytes is not None and len(files_voice_bytes) > 0:
                audio_result = AudioModalityResult(
                    status="unavailable",
                    prediction=None,
                    model_version=None,
                    message=(
                        "Raw audio waveform extraction pipeline is offline in this environment. "
                        "Audio screening requires 7 pre-extracted acoustic features (f0_mean_hz, "
                        "f0_std_hz, jitter_local_percent, shimmer_local_percent, hnr_db, "
                        "speech_rate_syllables_per_sec, pause_ratio)."
                    ),
                )
            else:
                audio_result = AudioModalityResult(
                    status="unavailable",
                    prediction=None,
                    model_version=None,
                    message=(
                        "Audio screening inference model is unavailable or audio features were not provided. "
                        "Audio acoustic feature profiles remain experimental benchmarks (non-predictive)."
                    ),
                )
        else:
            audio_result = AudioModalityResult(
                status="not_requested",
                prediction=None,
                model_version=None,
            )

        # 7. Video Modality (Experimental Synthetic Simulation / Offline Benchmark)
        video_result: VideoModalityResult
        if modalities.video:
            video_result = VideoModalityResult(
                status="unavailable",
                prediction=None,
                model_version=None,
                message=(
                    "Video screening model is an experimental synthetic simulation / offline benchmark. "
                    "In live screening, visual dynamics inference is unavailable to protect patient privacy "
                    "and avoid uncalibrated diagnostic predictions."
                ),
            )
        else:
            video_result = VideoModalityResult(
                status="not_requested",
                prediction=None,
                model_version=None,
            )

        # 8. Late Fusion & Cross-Modal Discordance via MultimodalFusionEngine
        fusion_result = self.fusion_engine.evaluate(
            clinical=clinical_result,
            text=text_result,
            audio=audio_result,
            video=video_result,
        )

        # 9. Compute Overall Screening Status
        requested_results = []
        if modalities.clinical:
            requested_results.append(clinical_result)
        if modalities.text:
            requested_results.append(text_result)
        if modalities.audio:
            requested_results.append(audio_result)
        if modalities.video:
            requested_results.append(video_result)

        completed_count = sum(1 for r in requested_results if r.status == "completed")
        if completed_count == len(requested_results):
            overall_status = "completed"
        elif completed_count > 0:
            overall_status = "partially_completed"
        else:
            overall_status = "failed"

        # 10. Generate Response Object
        screening_id = str(uuid.uuid4())
        processed_at = datetime.now(timezone.utc).isoformat()

        return ScreeningAnalysisResponse(
            screening_id=screening_id,
            mother_id=clean_mother_id,
            status=overall_status,
            clinical=clinical_result,
            text=text_result,
            audio=audio_result,
            video=video_result,
            fusion=fusion_result,
            processed_at=processed_at,
        )


# Global default instances
default_mother_validator = MotherValidator()
screening_orchestration_service = ScreeningOrchestrationService()


def get_mother_validator() -> MotherValidator:
    """FastAPI dependency provider for MotherValidator.

    Designed for Member 2 to plug in their database patient existence verification:
        app.dependency_overrides[get_mother_validator] = lambda: SQLDatabaseMotherValidator(db_session)
    """
    return default_mother_validator


def get_screening_service(
    clinical_svc: ClinicalScreeningService = Depends(get_clinical_service),
    text_svc: TextNERService = Depends(get_text_ner_service),
    audio_svc: AudioScreeningService = Depends(get_audio_service),
    mother_val: MotherValidator = Depends(get_mother_validator),
    fusion_eng: MultimodalFusionEngine = Depends(get_fusion_engine),
    elig_val: EligibilityValidator = Depends(get_eligibility_validator),
) -> ScreeningOrchestrationService:
    """FastAPI dependency provider for ScreeningOrchestrationService."""
    active_engine = fusion_eng
    if active_engine is fusion_engine and active_engine.strategy is None:
        active_engine = MultimodalFusionEngine(strategy=NonNegativeStackingFusionStrategy())

    return ScreeningOrchestrationService(
        clinical_svc=clinical_svc,
        text_svc=text_svc,
        audio_svc=audio_svc,
        mother_val=mother_val,
        fusion_eng=active_engine,
        elig_val=elig_val,
    )

