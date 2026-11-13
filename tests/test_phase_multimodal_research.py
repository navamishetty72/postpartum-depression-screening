"""Phase 8G Test Suite: Experimental Multimodal Research Integration.

Verifies:
1. Two strictly separated pathways: Clinical baseline remains unchanged and independent.
2. Research-only multimodal late fusion with learned non-negative stacking weights.
3. Preservation of individual modality predictions (clinical and audio).
4. Audio inclusion in research pipeline without altering the clinical baseline probability.
5. Biomedical Text NER extraction strictly excluded from predictive probability fusion.
6. Clean handling of missing modalities without zero-fabrication.
7. Video modality explicit simulation notice.
8. EPDS Q10 safety escalation independence from ML scores.
9. Transparent research benchmark reporting (empirical comparisons from offline experiments).
"""

import json
from pathlib import Path
from typing import Any, Dict
import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from backend.main import app
from backend.ml.fusion_engine import (
    CANONICAL_STACKING_WEIGHTS,
    RESEARCH_FUSION_BENCHMARKS,
    FusionStatus,
    ModalityCandidate,
    MultimodalFusionEngine,
    NonNegativeStackingFusionStrategy,
    WeightedAverageFusionStrategy,
)
from backend.schemas.audio import ACOUSTIC_FEATURE_NAMES
from backend.schemas.screening import (
    AudioModalityResult,
    ClinicalModalityResult,
    TextModalityResult,
    VideoModalityResult,
)
from backend.services.audio_service import (
    AudioScreeningService,
    EXPECTED_AUDIO_FEATURES,
    get_audio_service,
)
from backend.services.screening_service import (
    ScreeningOrchestrationService,
    get_screening_service,
)
from tests.test_backend_screening import _get_valid_clinical_features


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create TestClient with application lifespan active."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_acoustic_dict() -> Dict[str, float]:
    """Valid acoustic features adhering to physiological bounds."""
    return {
        "f0_mean_hz": 210.5,
        "f0_std_hz": 28.4,
        "jitter_local_percent": 1.25,
        "shimmer_local_percent": 4.80,
        "hnr_db": 18.5,
        "speech_rate_syllables_per_sec": 3.75,
        "pause_ratio": 0.28,
    }


@pytest.fixture
def mock_audio_artifacts(tmp_path: Path):
    """Create temporary mock audio model and scaler artifacts for research testing."""
    model_dir = tmp_path / "mock_audio_rf"
    model_dir.mkdir(parents=True, exist_ok=True)

    # Train a minimal 2-class RF on synthetic 7 acoustic features
    rng = np.random.RandomState(42)
    X = rng.randn(40, len(EXPECTED_AUDIO_FEATURES))
    y = rng.choice([0, 1], size=40)

    scaler = StandardScaler()
    df_X = pd.DataFrame(X, columns=EXPECTED_AUDIO_FEATURES)
    scaler.fit(df_X)

    rf = RandomForestClassifier(n_estimators=5, random_state=42)
    scaled_X = scaler.transform(df_X)
    rf.fit(scaled_X, y)

    scaler_path = model_dir / "scaler.joblib"
    model_path = model_dir / "random_forest.joblib"
    joblib.dump(scaler, scaler_path)
    joblib.dump(rf, model_path)

    metrics = {
        "model_type": "RandomForestClassifier",
        "n_features": 7,
        "features": EXPECTED_AUDIO_FEATURES,
        "metrics": {"roc_auc": 0.5339, "pr_auc": 0.4759, "f1_score": 0.4782},
        "provenance": "CLINICALLY_CONDITIONED_SYNTHETIC",
        "data_origin": "CLINICALLY_CONDITIONED_SYNTHETIC",
    }
    with open(model_dir / "audio_model_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f)

    return model_dir


# ---------------------------------------------------------------------------
# 1. Clinical Baseline Independence
# ---------------------------------------------------------------------------
def test_clinical_baseline_remains_independent_and_unaffected(client: TestClient):
    """Verify clinical pathway is unchanged and does not depend on experimental modalities."""
    payload = {
        "motherId": "M-RESEARCH-01",
        "modalities": json.dumps({"clinical": True, "audio": False, "video": False, "text": False}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
    }
    response = client.post("/api/screenings/analyze", data=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["clinical"]["status"] == "completed"

    clin_pred = data["clinical"]["prediction"]
    assert 0.0 <= clin_pred["predicted_risk_probability"] <= 1.0
    assert clin_pred["risk_category"] in ("LOW_RISK", "MODERATE_RISK", "HIGH_RISK")

    # Multimodal research fusion reports not_available (only 1 predictive modality present)
    assert data["fusion"]["status"] == "not_available"
    assert data["fusion"]["combined_score"] is None
    # Research benchmarks are transparently included
    assert "single_modality_benchmarks" in data["fusion"]["research_benchmarks"]
    assert data["fusion"]["research_benchmarks"]["single_modality_benchmarks"]["clinical_only"]["roc_auc"] == 0.8373


# ---------------------------------------------------------------------------
# 2. Non-Negative Stacking Strategy
# ---------------------------------------------------------------------------
def test_non_negative_stacking_strategy_weights_and_normalization():
    """Verify learned stacking weights: clinical: 1.0, audio: 0.0, video: 0.0, text: 0.0."""
    strategy = NonNegativeStackingFusionStrategy()

    clin_cand = ModalityCandidate(
        modality="clinical",
        status="completed",
        probability=0.8200,
        is_predictive=True,
    )
    audio_cand = ModalityCandidate(
        modality="audio",
        status="completed",
        probability=0.3500,
        is_predictive=True,
    )

    combined_score, risk_cat, epds_equiv, contribs = strategy.combine([clin_cand, audio_cand])

    # Under canonical stacking, clinical weight is 1.0 and audio is 0.0
    assert contribs == {"clinical": 1.0, "audio": 0.0}
    # Combined score matches the clinical baseline probability exactly!
    assert combined_score == 0.8200
    assert risk_cat == "HIGH_RISK"
    assert epds_equiv == 25


# ---------------------------------------------------------------------------
# 3. Audio Integration into Central Screening Pipeline
# ---------------------------------------------------------------------------
def test_multimodal_research_screening_with_mock_audio(
    client: TestClient,
    mock_audio_artifacts: Path,
    valid_acoustic_dict: Dict[str, float],
):
    """Verify end-to-end screening with Clinical + Audio under research protocol."""
    test_audio_svc = AudioScreeningService(
        model_dir=mock_audio_artifacts,
        model_name="random_forest",
    )
    test_audio_svc.startup()

    app.dependency_overrides[get_audio_service] = lambda: test_audio_svc
    try:
        payload = {
            "motherId": "M-RESEARCH-02",
            "modalities": json.dumps({"clinical": True, "audio": True}),
            "consentConfirmed": "true",
            "eligibilityConfirmed": "true",
            "clinical_features": json.dumps(_get_valid_clinical_features()),
            "audio_features": json.dumps(valid_acoustic_dict),
        }
        response = client.post("/api/screenings/analyze", data=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "completed"

        # 1. Clinical baseline preserved
        assert data["clinical"]["status"] == "completed"
        clin_prob = data["clinical"]["prediction"]["predicted_risk_probability"]

        # 2. Audio modality executed and preserved
        assert data["audio"]["status"] == "completed"
        assert data["audio"]["prediction"] is not None
        audio_prob = data["audio"]["prediction"]["predicted_risk_probability"]
        assert 0.0 <= audio_prob <= 1.0

        # 3. Multimodal late fusion evaluated
        fusion = data["fusion"]
        assert fusion["status"] == "completed"
        # Non-negative stacking allocates 1.0 to clinical and 0.0 to synthetic audio
        assert fusion["modality_contributions"] == {"clinical": 1.0, "audio": 0.0}
        assert fusion["combined_score"] == clin_prob

        # 4. Discordance analyzed between clinical and audio
        assert "discordance_detected" in fusion["discordance_analysis"]
        diff = abs(clin_prob - audio_prob)
        assert fusion["discordance_analysis"]["discordance_detected"] == (diff >= 0.25)

    finally:
        app.dependency_overrides.clear()
        test_audio_svc.shutdown()


# ---------------------------------------------------------------------------
# 4. Equal-Weight Fusion for Offline Comparison
# ---------------------------------------------------------------------------
def test_equal_weight_fusion_strategy_comparison():
    """Verify equal weighting strategy aggregates probabilities for research benchmarking."""
    equal_strat = WeightedAverageFusionStrategy(default_weights={"clinical": 0.5, "audio": 0.5})

    clin_cand = ModalityCandidate(modality="clinical", status="completed", probability=0.80, is_predictive=True)
    audio_cand = ModalityCandidate(modality="audio", status="completed", probability=0.40, is_predictive=True)

    score, risk, epds, contribs = equal_strat.combine([clin_cand, audio_cand])

    assert contribs == {"clinical": 0.5, "audio": 0.5}
    # 0.80 * 0.5 + 0.40 * 0.5 = 0.60
    assert score == 0.60
    assert risk == "MODERATE_RISK"
    assert epds == 18


# ---------------------------------------------------------------------------
# 5. Missing Modalities & Safe Unavailability
# ---------------------------------------------------------------------------
def test_missing_modalities_do_not_fabricate_scores(client: TestClient):
    """Verify missing audio/video modalities return explicit unavailable status."""
    payload = {
        "motherId": "M-RESEARCH-03",
        "modalities": json.dumps({"clinical": True, "audio": True, "video": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
        # No audio_features or video files passed
    }
    response = client.post("/api/screenings/analyze", data=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "partially_completed"
    assert data["clinical"]["status"] == "completed"
    assert data["audio"]["status"] == "unavailable"
    assert data["audio"]["prediction"] is None
    assert data["video"]["status"] == "unavailable"
    assert data["video"]["prediction"] is None

    # Fusion status is cleanly not_available without fabricated numbers
    assert data["fusion"]["status"] == "not_available"
    assert data["fusion"]["combined_score"] is None


# ---------------------------------------------------------------------------
# 6. Text NER Non-Predictive Boundary
# ---------------------------------------------------------------------------
def test_text_ner_never_enters_predictive_fusion(client: TestClient):
    """Verify Biomedical Text NER entity extraction is strictly non-predictive."""
    payload = {
        "motherId": "M-RESEARCH-04",
        "modalities": json.dumps({"clinical": True, "text": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
        "clinical_features": json.dumps(_get_valid_clinical_features()),
        "text_content": "Patient reports severe sadness, insomnia, and overwhelming fatigue.",
    }
    response = client.post("/api/screenings/analyze", data=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["clinical"]["status"] == "completed"
    assert data["text"]["status"] == "completed"
    assert data["text"]["processing_type"] == "biomedical_ner"

    # Fusion does NOT consider Text NER as a predictive PPD probability
    assert data["fusion"]["status"] == "not_available"
    assert data["fusion"]["combined_score"] is None


# ---------------------------------------------------------------------------
# 7. Video Simulation Notice & Ethical Safeguards
# ---------------------------------------------------------------------------
def test_video_modality_reports_simulation_notice(client: TestClient):
    """Verify Video modality informs user of offline simulation status."""
    payload = {
        "motherId": "M-RESEARCH-05",
        "modalities": json.dumps({"video": True}),
        "consentConfirmed": "true",
        "eligibilityConfirmed": "true",
    }
    response = client.post("/api/screenings/analyze", data=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["video"]["status"] == "unavailable"
    assert "simulation" in data["video"]["message"].lower() or "offline benchmark" in data["video"]["message"].lower()


# ---------------------------------------------------------------------------
# 8. EPDS Q10 Safety Alert Independence
# ---------------------------------------------------------------------------
def test_epds_q10_safety_alert_independence():
    """Verify EPDS Q10 safety trigger operates independently of ML/fusion probabilities."""
    from backend.schemas.questionnaire import AnswerSubmissionItem, EPDSSubmissionRequest
    from backend.services.questionnaire_service import EPDSQuestionnaireService

    # 10 answers where Item 1-9 are 0 and Item 10 is endorsed (option index 1 = score 1)
    answers = [
        AnswerSubmissionItem(question_id=f"EPDS_Q0{i}", selected_index=0)
        for i in range(1, 10)
    ]
    # Question 10 has options: 0 = Never, 1 = Hardly ever (score 1), 2 = Sometimes (score 2), 3 = Yes, quite often (score 3)
    answers.append(AnswerSubmissionItem(question_id="EPDS_Q10", selected_index=1))

    submission = EPDSSubmissionRequest(answers=answers)
    service = EPDSQuestionnaireService()
    result = service.calculate_score(submission)

    assert result.safety_alert.triggered is True
    assert result.safety_alert.question_10_score > 0
    assert result.safety_alert.severity == "URGENT_SAFETY_ASSESSMENT"
    assert "never be overridden" in result.safety_alert.override_protection.lower()
