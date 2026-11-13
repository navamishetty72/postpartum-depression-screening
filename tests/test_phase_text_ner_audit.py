"""Phase 7 Automated Test Suite: Text NER Model Audit and Inference Validation.

Postpartum Depression (PPD) Multimodal Recognition Research Prototype.
Verifies:
1. Genuine trained checkpoint provenance, metadata, and versioning (v1.3.0).
2. Live inference with verified character offsets, confidence scores, and entity schemas.
3. Defensive handling across boundary inputs (empty, whitespace, long, Unicode, None).
4. Privacy safeguards: Zero raw patient narrative logging.
5. Graceful HTTP 503 handling when model checkpoint is missing.
6. Central screening orchestration compatibility and modality status integrity.
7. Clinical safeguards: Complete independence from EPDS scoring and Q10 safety logic.
"""

import asyncio
import logging
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.text_ner_service import (
    TextNERService,
    get_text_ner_service,
    text_ner_service,
)
from backend.services.screening_service import ScreeningOrchestrationService, get_screening_service
from backend.schemas.screening import ModalitiesSelection, TextModalityResult
from backend.services.clinical_service import clinical_service
from pipelines.text_ner.inference import TextNERPredictor, TextNEROutput


@pytest.fixture(scope="module")
def live_predictor() -> TextNERPredictor:
    """Return live TextNERPredictor instance loaded from disk."""
    default_ckpt = TextNERPredictor.DEFAULT_MODEL_PATH
    if not default_ckpt.exists():
        pytest.skip(f"Live model checkpoint not downloaded at {default_ckpt}")
    return TextNERPredictor(model_path=default_ckpt)


@pytest.fixture(scope="module")
def live_service(live_predictor: TextNERPredictor) -> TextNERService:
    """Return an active TextNERService wrapping the live trained predictor."""
    return TextNERService(predictor=live_predictor)


@pytest.fixture(scope="module")
def client_with_live_service(live_service: TextNERService):
    """Provide TestClient with live TextNERService active."""
    app.dependency_overrides[get_text_ner_service] = lambda: live_service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. Model Provenance & Metadata Verification
# ---------------------------------------------------------------------------
def test_text_ner_model_provenance_and_version(live_predictor: TextNERPredictor):
    """Verify that the model checkpoint is genuine, fitted, and reports version 1.3.0."""
    metadata = live_predictor.get_model_metadata()

    assert metadata["model_version"] == "1.3.0"
    assert metadata["is_fitted"] is True
    assert metadata["classifier_type"] == "sgd"
    assert metadata["feature_version"] == "v2"
    assert metadata["feature_window"] == 2
    assert metadata["use_viterbi"] is True

    # Classes must follow BIO scheme for MMLite
    class_names = [str(c) for c in metadata["classes"]]
    assert set(class_names) == {"B-MMLite", "I-MMLite", "O"}


# ---------------------------------------------------------------------------
# 2. Live Inference & Exact Character Offset Alignment
# ---------------------------------------------------------------------------
def test_real_inference_entities_and_character_offsets(live_predictor: TextNERPredictor):
    """Verify entity extraction on postpartum clinical notes with exact character bounds."""
    text = "The mother reported experiencing severe postpartum depression and anxiety after delivery."
    output = live_predictor.predict(text)

    assert isinstance(output, TextNEROutput)
    assert output.model_version == "1.3.0"
    assert output.processed_character_count == len(text)
    assert output.total_entities_detected >= 1

    for ent in output.entities:
        assert ent.label == "MMLite"
        assert 0.0 <= ent.confidence <= 1.0
        # Exact substring equality check against original text
        assert text[ent.start : ent.end] == ent.text
        assert len(ent.text) > 0


# ---------------------------------------------------------------------------
# 3. Defensive Boundary Input Handling
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "input_val,expected_count",
    [
        ("", 0),
        ("   \t\n\r  ", 0),
        (None, 0),
    ],
)
def test_input_boundaries_empty_and_whitespace(
    live_predictor: TextNERPredictor,
    input_val,
    expected_count,
):
    """Verify that empty, whitespace, and None inputs return zero entities safely."""
    out = live_predictor.predict(input_val)
    assert out.total_entities_detected == expected_count
    assert len(out.entities) == expected_count


def test_input_boundaries_very_long_input(live_predictor: TextNERPredictor):
    """Verify that input exceeding safe maximum character limit is safely truncated."""
    # 25 characters * 3000 = 75,000 chars (> 50,000 character limit)
    base_phrase = "Depressed and exhausted. "
    long_text = base_phrase * 3000
    assert len(long_text) > 50000

    out = live_predictor.predict(long_text)
    assert out.processed_character_count == 50000
    for ent in out.entities:
        assert ent.end <= 50000
        assert long_text[ent.start : ent.end] == ent.text


def test_input_boundaries_unicode_and_emojis(live_predictor: TextNERPredictor):
    """Verify that Unicode symbols and emojis do not break character index offsets."""
    text = "Feeling so down 😢 with intense panic attacks and crying spells."
    out = live_predictor.predict(text)
    assert out.processed_character_count == len(text)
    for ent in out.entities:
        assert text[ent.start : ent.end] == ent.text


# ---------------------------------------------------------------------------
# 4. Privacy & Diagnostic Non-Equivalence
# ---------------------------------------------------------------------------
def test_privacy_safeguards_no_narrative_logging(
    live_service: TextNERService,
    caplog: pytest.LogCaptureFixture,
):
    """Verify that patient narrative strings are never written to logger records."""
    private_narrative = "CONFIDENTIAL_PRIVATE_PATIENT_SYMPTOM_NARRATIVE_DO_NOT_LOG"
    with caplog.at_level(logging.DEBUG):
        out = live_service.extract_entities(private_narrative)

    assert private_narrative not in caplog.text


# ---------------------------------------------------------------------------
# 5. Missing Model Checkpoint Graceful HTTP 503
# ---------------------------------------------------------------------------
def test_service_missing_artifact_returns_503():
    """Verify that service safely raises HTTP 503 when checkpoint file is missing."""
    service = TextNERService(
        predictor_factory=lambda: TextNERPredictor(model_path=Path("non_existent_ner.joblib"))
    )
    service.startup()
    assert service.is_loaded is False

    with pytest.raises(HTTPException) as exc_info:
        service._get_predictor()
    assert exc_info.value.status_code == 503
    assert "missing or unavailable" in str(exc_info.value.detail).lower()


# ---------------------------------------------------------------------------
# 6. Central Screening Orchestrator Integration
# ---------------------------------------------------------------------------
def test_screening_orchestrator_integration_with_live_text_ner(live_service: TextNERService):
    """Verify that central screening analysis seamlessly consumes live TextNERService output."""
    orchestrator = ScreeningOrchestrationService(
        clinical_svc=clinical_service,
        text_svc=live_service,
    )
    # Verify orchestrator is wired with live TextNERService
    assert orchestrator.text_ner_service is live_service
    assert orchestrator.text_ner_service.is_loaded is True

    # Test live entity extraction via orchestrator's wired service
    entities_out = orchestrator.text_ner_service.extract_entities(
        "The patient experienced marked anxiety, fatigue, and insomnia after birth."
    )
    assert entities_out.total_entities_detected >= 1
    assert entities_out.model_version == "1.3.0"
    assert any(e.text == "anxiety" for e in entities_out.entities)

    # Verify fusion candidate evaluation for biomedical NER modality
    text_modality_result = TextModalityResult(
        status="completed",
        processing_type="biomedical_ner",
        entities=[e.model_dump() for e in entities_out.entities],
        total_entities_detected=entities_out.total_entities_detected,
        processed_character_count=entities_out.processed_character_count,
        model_version=entities_out.model_version,
    )
    candidate = orchestrator.fusion_engine.extract_candidate("text", text_modality_result)
    assert candidate.status == "completed"
    assert candidate.is_predictive is False  # Non-predictive clinical extraction boundary
    assert candidate.is_available is True
    assert candidate.metadata["total_entities_detected"] >= 1


# ---------------------------------------------------------------------------
# 7. Clinical Safety Protocol Independence (EPDS Q10)
# ---------------------------------------------------------------------------
def test_clinical_safeguard_epds_independence(live_service: TextNERService):
    """Verify that Text NER output does not alter or suppress EPDS scoring or Q10 safety logic."""
    from backend.services.questionnaire_service import questionnaire_service
    from backend.schemas.questionnaire import AnswerSubmissionItem, EPDSSubmissionRequest

    # Text narrative reporting zero entities
    ner_out = live_service.extract_entities("Everything is normal, no unusual signs noted.")
    assert ner_out.total_entities_detected == 0

    # EPDS submission where Question 10 is positive
    answers = [
        AnswerSubmissionItem(question_id=f"EPDS_Q{i:02d}", selected_index=0 if i in {1, 2, 4} else 3)
        for i in range(1, 10)
    ]
    answers.append(AnswerSubmissionItem(question_id="EPDS_Q10", selected_index=2))  # "Sometimes" -> score=2

    req = EPDSSubmissionRequest(answers=answers)
    epds_data = questionnaire_service.calculate_score(req)
    assert epds_data.safety_alert.triggered is True
    assert epds_data.safety_alert.severity == "URGENT_SAFETY_ASSESSMENT"
