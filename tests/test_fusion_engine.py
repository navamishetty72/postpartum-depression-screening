"""Tests for the Multimodal Fusion Engine and Cross-Modal Discordance Analyzer.

Verifies:
1. Clinical-only output evaluation.
2. Clinical plus Text NER evaluation (Text NER entity confidence is NOT treated as PPD risk).
3. Missing modalities handling.
4. Unavailable audio/video handling.
5. Incompatible output types handling.
6. No comparable modality predictions handling.
7. Discordance analysis with insufficient data (exact contract match).
8. Invalid modality status handling.
9. Fusion failure exception handling.
10. Future multi-branch fusion extensibility (when >= 2 predictive modalities are present).
11. Future multi-branch concordant vs discordant analysis.
12. Full end-to-end screening endpoint integration regression.
"""

from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.ml.fusion_engine import (
    BaseFusionStrategy,
    DiscordanceAnalyzer,
    FusionStatus,
    ModalityCandidate,
    MultimodalFusionEngine,
    WeightedAverageFusionStrategy,
    fusion_engine,
)
from backend.schemas.screening import (
    AudioModalityResult,
    ClinicalModalityResult,
    TextModalityResult,
    VideoModalityResult,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create TestClient with application lifespan active."""
    with TestClient(app) as test_client:
        yield test_client


def _sample_clinical_completed(prob: float = 0.72) -> ClinicalModalityResult:
    """Create valid completed ClinicalModalityResult fixture."""
    return ClinicalModalityResult(
        status="completed",
        prediction={
            "predicted_risk_probability": prob,
            "predicted_class": 1 if prob >= 0.5 else 0,
            "risk_category": "HIGH_RISK" if prob >= 0.7 else "MODERATE_RISK",
            "decision_threshold": 0.5,
        },
        model_version="random_forest",
    )


def _sample_text_ner_completed() -> TextModalityResult:
    """Create valid completed TextModalityResult fixture (biomedical entity extraction)."""
    return TextModalityResult(
        status="completed",
        processing_type="biomedical_ner",
        entities=[
            {"text": "depression", "label": "MMLite", "start": 0, "end": 10, "confidence": 0.98},
            {"text": "anxiety", "label": "MMLite", "start": 15, "end": 22, "confidence": 0.95},
        ],
        total_entities_detected=2,
        processed_character_count=50,
        model_version="1.2.0-test",
    )


# ---------------------------------------------------------------------------
# 1. Clinical-Only Output
# ---------------------------------------------------------------------------
def test_fusion_clinical_only_output():
    """Verify that a single clinical prediction results in status='not_available' and no fabricated score."""
    engine = MultimodalFusionEngine()
    result = engine.evaluate(clinical=_sample_clinical_completed(0.72))

    assert result.status == FusionStatus.NOT_AVAILABLE.value
    assert result.combined_score is None
    assert result.risk_category is None
    assert result.epds_equivalent is None
    assert result.modality_contributions == {}

    # Discordance requires >= 2 comparable modalities
    assert result.discordance_analysis is not None
    assert result.discordance_analysis["discordance_detected"] is False
    assert result.discordance_analysis["comparison"] == []
    assert result.discordance_analysis["explanation"] == "Insufficient comparable modality predictions."


# ---------------------------------------------------------------------------
# 2. Clinical Plus Text NER (Entity confidence is NOT PPD probability)
# ---------------------------------------------------------------------------
def test_fusion_clinical_plus_text_ner_not_available():
    """Verify Text NER is recognized as non-predictive entity extraction and cannot be fused."""
    engine = MultimodalFusionEngine()
    clinical = _sample_clinical_completed(0.65)
    text = _sample_text_ner_completed()

    result = engine.evaluate(clinical=clinical, text=text)

    # Even with clinical + text, predictive modality count is 1
    assert result.status == FusionStatus.NOT_AVAILABLE.value
    assert result.combined_score is None
    assert result.modality_contributions == {}

    # Must NOT compare text entity confidence with clinical risk probability
    assert result.discordance_analysis["discordance_detected"] is False
    assert result.discordance_analysis["comparison"] == []
    assert result.discordance_analysis["explanation"] == "Insufficient comparable modality predictions."


# ---------------------------------------------------------------------------
# 3. Missing Modalities
# ---------------------------------------------------------------------------
def test_fusion_missing_modalities():
    """Verify that omitting all modalities returns status='not_available'."""
    engine = MultimodalFusionEngine()
    result = engine.evaluate(clinical=None, text=None, audio=None, video=None)

    assert result.status == FusionStatus.NOT_AVAILABLE.value
    assert result.combined_score is None
    assert result.discordance_analysis["discordance_detected"] is False


# ---------------------------------------------------------------------------
# 4. Unavailable Audio & Video
# ---------------------------------------------------------------------------
def test_fusion_unavailable_audio_and_video():
    """Verify that unavailable audio and video models do not enable fusion."""
    engine = MultimodalFusionEngine()
    clinical = _sample_clinical_completed(0.55)
    audio = AudioModalityResult(status="unavailable", message="Unimplemented")
    video = VideoModalityResult(status="unavailable", message="Unimplemented")

    result = engine.evaluate(clinical=clinical, audio=audio, video=video)
    assert result.status == FusionStatus.NOT_AVAILABLE.value
    assert result.combined_score is None
    assert result.discordance_analysis["discordance_detected"] is False


# ---------------------------------------------------------------------------
# 5. Incompatible Output Types
# ---------------------------------------------------------------------------
def test_fusion_incompatible_output_types():
    """Verify that non-predictive formats (e.g. text NER only) are recognized as incompatible."""
    engine = MultimodalFusionEngine()
    text = _sample_text_ner_completed()

    # Candidate extraction check
    candidate = engine.extract_candidate("text", text)
    assert candidate.is_predictive is False
    assert candidate.probability is None

    result = engine.evaluate(text=text)
    assert result.status == FusionStatus.NOT_AVAILABLE.value
    assert result.combined_score is None


# ---------------------------------------------------------------------------
# 6. No Comparable Modality Predictions
# ---------------------------------------------------------------------------
def test_fusion_no_comparable_modality_predictions():
    """Verify that zero predictive modalities cleanly returns insufficient predictions report."""
    engine = MultimodalFusionEngine()
    audio = AudioModalityResult(status="not_requested")
    video = VideoModalityResult(status="not_requested")

    result = engine.evaluate(audio=audio, video=video)
    assert result.status == FusionStatus.NOT_AVAILABLE.value
    assert result.discordance_analysis["discordance_detected"] is False
    assert result.discordance_analysis["comparison"] == []


# ---------------------------------------------------------------------------
# 7. Discordance with Insufficient Data Contract
# ---------------------------------------------------------------------------
def test_discordance_with_insufficient_data():
    """Verify exact contract specification for discordance when < 2 predictive modalities exist."""
    analyzer = DiscordanceAnalyzer(threshold=0.25)

    # Empty candidates
    res_empty = analyzer.analyze([])
    assert res_empty.to_dict() == {
        "discordance_detected": False,
        "comparison": [],
        "explanation": "Insufficient comparable modality predictions.",
    }

    # Single clinical candidate
    clinical_cand = ModalityCandidate(
        modality="clinical",
        status="completed",
        probability=0.81,
        is_predictive=True,
    )
    res_single = analyzer.analyze([clinical_cand])
    assert res_single.to_dict() == {
        "discordance_detected": False,
        "comparison": [],
        "explanation": "Insufficient comparable modality predictions.",
    }


# ---------------------------------------------------------------------------
# 8. Invalid Modality Status Handling
# ---------------------------------------------------------------------------
def test_invalid_modality_status_handling():
    """Verify that invalid modality status strings are rejected and yield status='failed'."""
    engine = MultimodalFusionEngine()
    bad_modality = {"status": "unrecognized_status_code_999"}

    result = engine.evaluate(clinical=bad_modality)  # type: ignore
    assert result.status == FusionStatus.FAILED.value
    assert result.combined_score is None
    assert "validation failed" in result.discordance_analysis["explanation"].lower()


# ---------------------------------------------------------------------------
# 9. Fusion Failure Exception Handling
# ---------------------------------------------------------------------------
def test_fusion_failure_exception_handling():
    """Verify that exceptions thrown inside a fusion strategy are caught and recorded as failed."""
    class CrashingStrategy(BaseFusionStrategy):
        def combine(self, candidates):
            raise RuntimeError("Simulated mathematical singularity or memory fault")

    engine = MultimodalFusionEngine(strategy=CrashingStrategy())

    # Supply 2 mock predictive modalities to trigger strategy combine
    cand_clin = ModalityCandidate(modality="clinical", status="completed", probability=0.8, is_predictive=True)
    cand_audio = ModalityCandidate(modality="audio", status="completed", probability=0.7, is_predictive=True)

    # Mock extract_candidate to return our two candidates
    engine.extract_candidate = lambda mod, data: cand_clin if mod == "clinical" else cand_audio

    result = engine.evaluate(clinical={"status": "completed"}, audio={"status": "completed"})
    assert result.status == FusionStatus.FAILED.value
    assert result.combined_score is None


# ---------------------------------------------------------------------------
# 10. Future Multi-Branch Fusion Extensibility
# ---------------------------------------------------------------------------
def test_future_multi_branch_fusion_execution():
    """Verify that when >= 2 predictive modalities exist and strategy is configured, fusion completes."""
    strategy = WeightedAverageFusionStrategy(default_weights={"clinical": 0.6, "audio": 0.4})
    engine = MultimodalFusionEngine(strategy=strategy)

    cand_clin = ModalityCandidate(modality="clinical", status="completed", probability=0.80, is_predictive=True)
    cand_audio = ModalityCandidate(modality="audio", status="completed", probability=0.40, is_predictive=True)

    engine.extract_candidate = lambda mod, data: (
        cand_clin if mod == "clinical"
        else cand_audio if mod == "audio"
        else ModalityCandidate(modality=mod, status="not_requested")
    )

    result = engine.evaluate(clinical={"status": "completed"}, audio={"status": "completed"})
    assert result.status == FusionStatus.COMPLETED.value
    # 0.80 * 0.6 + 0.40 * 0.4 = 0.48 + 0.16 = 0.64
    assert result.combined_score == 0.64
    assert result.risk_category == "MODERATE_RISK"
    assert result.epds_equivalent == 19
    assert result.modality_contributions == {"clinical": 0.6, "audio": 0.4}

    # Discordance: |0.80 - 0.40| = 0.40 >= 0.25 -> True
    assert result.discordance_analysis["discordance_detected"] is True
    assert len(result.discordance_analysis["comparison"]) == 1


# ---------------------------------------------------------------------------
# 11. Multi-Branch Concordance Check
# ---------------------------------------------------------------------------
def test_future_multi_branch_concordant_analysis():
    """Verify that when probabilities are close (< threshold), discordance_detected is False."""
    strategy = WeightedAverageFusionStrategy()
    engine = MultimodalFusionEngine(strategy=strategy)

    cand_clin = ModalityCandidate(modality="clinical", status="completed", probability=0.75, is_predictive=True)
    cand_audio = ModalityCandidate(modality="audio", status="completed", probability=0.78, is_predictive=True)

    engine.extract_candidate = lambda mod, data: (
        cand_clin if mod == "clinical"
        else cand_audio if mod == "audio"
        else ModalityCandidate(modality=mod, status="not_requested")
    )

    result = engine.evaluate(clinical={"status": "completed"}, audio={"status": "completed"})
    assert result.status == FusionStatus.COMPLETED.value
    # |0.75 - 0.78| = 0.03 < 0.25 -> False
    assert result.discordance_analysis["discordance_detected"] is False


# ---------------------------------------------------------------------------
# 12. Full Screening Endpoint Regression
# ---------------------------------------------------------------------------
def test_screening_endpoint_regression_with_fusion_engine(client: TestClient):
    """Verify live POST /api/screenings/analyze outputs fusion contract via MultimodalFusionEngine."""
    import json
    from tests.test_backend_screening import _get_valid_clinical_features

    payload = {
        "motherId": "M-FUSION-01",
        "modalities": json.dumps({"clinical": True, "text": False}),
        "consentConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    response = client.post("/api/screenings/analyze", data=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["clinical"]["status"] == "completed"

    fusion = data["fusion"]
    assert fusion["status"] == "not_available"
    assert fusion["combined_score"] is None
    assert fusion["risk_category"] is None
    assert fusion["epds_equivalent"] is None
    assert fusion["modality_contributions"] == {}
    assert fusion["discordance_analysis"] == {
        "discordance_detected": False,
        "comparison": [],
        "explanation": "Insufficient comparable modality predictions.",
    }

