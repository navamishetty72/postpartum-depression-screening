"""Backend API tests for POST /api/text-ner/extract (Biomedical Entity Extraction).

Uses FastAPI TestClient and lightweight mocked / temporary-artifact predictors to
verify startup-only model loading, schema compliance, defensive input handling,
no-PII logging, error responses, and strict independence from EPDS safety logic.
"""

import logging
from pathlib import Path
from typing import Iterator
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.text_ner_service import (
    TextNERService,
    get_text_ner_service,
    text_ner_service,
)
from pipelines.text_ner.features import (
    align_spans_to_bio,
    extract_document_features,
    tokenize_with_offsets,
)
from pipelines.text_ner.inference import TextNEROutput, TextNERPredictor
from pipelines.text_ner.models import TextNERModel
from pipelines.text_ner.parser import Document, EntitySpan


def _build_small_predictor_checkpoint(tmp_path: Path) -> Path:
    """Train and serialize a tiny deterministic TextNERModel for fast API tests."""
    samples = [
        ("Severe postpartum depression and anxiety symptoms daily.", ["postpartum depression", "anxiety"]),
        ("Doctor discussed therapy and support for mood changes.", ["therapy"]),
        ("Feeling hopeful and rested after sleep.", []),
    ]
    X_dicts, y_tags = [], []
    for idx, (text, kws) in enumerate(samples):
        spans = [
            EntitySpan(
                id=f"T{idx}_{text.index(kw)}",
                label="MMLite",
                start=text.index(kw),
                end=text.index(kw) + len(kw),
                text=kw,
            )
            for kw in kws
        ]
        doc = Document(id=f"mock_{idx}", group="Test", text=text, spans=spans)
        tokens = tokenize_with_offsets(doc.text)
        X_dicts.extend(extract_document_features(tokens))
        y_tags.extend(align_spans_to_bio(tokens, doc.spans))

    model = TextNERModel(
        classifier_type="sgd",
        loss="modified_huber",
        max_iter=150,
        random_state=42,
        model_version="1.2.0-test",
    )
    model.fit(X_dicts, y_tags)
    ckpt_path = tmp_path / "small_text_ner_model.joblib"
    model.save(ckpt_path)
    return ckpt_path


@pytest.fixture
def small_real_predictor(tmp_path: Path) -> TextNERPredictor:
    """Return a real TextNERPredictor backed by a tiny temporary checkpoint."""
    ckpt = _build_small_predictor_checkpoint(tmp_path)
    return TextNERPredictor(model_path=ckpt)


@pytest.fixture
def api_client_with_small_predictor(
    small_real_predictor: TextNERPredictor,
) -> Iterator[TestClient]:
    """Provide a TestClient with dependency override cleaned up after each test."""
    service = TextNERService(predictor=small_real_predictor)
    app.dependency_overrides[get_text_ner_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_startup_loads_model_once_not_per_request(
    small_real_predictor: TextNERPredictor,
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify FastAPI lifespan loads TextNERPredictor once at startup, never per request."""
    load_calls = 0

    def counting_factory() -> TextNERPredictor:
        nonlocal load_calls
        load_calls += 1
        return small_real_predictor

    # Reset singleton state safely for isolated lifespan verification
    monkeypatch.setattr(text_ner_service, "_predictor_factory", counting_factory)
    monkeypatch.setattr(text_ner_service, "_predictor", None)
    monkeypatch.setattr(text_ner_service, "_startup_attempted", False)
    monkeypatch.setattr(text_ner_service, "_load_error", None)

    app.dependency_overrides.clear()
    with TestClient(app) as client:
        assert load_calls == 1
        assert text_ner_service.is_loaded is True

        for _ in range(3):
            resp = client.post(
                "/api/text-ner/extract",
                json={"text": "Patient reports postpartum depression and anxiety."},
            )
            assert resp.status_code == 200
            assert load_calls == 1

    assert text_ner_service.is_loaded is False


def test_extract_biomedical_entities_returns_schema_without_diagnosis(
    api_client_with_small_predictor: TestClient,
):
    """Verify valid extraction payload matches TextNEROutput without diagnostic fields."""
    payload_text = "Postpartum depression and anxiety symptoms reported."
    response = api_client_with_small_predictor.post(
        "/api/text-ner/extract",
        json={"text": payload_text},
    )
    assert response.status_code == 200
    data = response.json()

    # Validate exact TextNEROutput structure
    parsed = TextNEROutput.model_validate(data)
    assert parsed.processed_character_count == len(payload_text)
    assert parsed.total_entities_detected == len(parsed.entities)
    assert parsed.model_version == "1.2.0-test"

    for ent in parsed.entities:
        assert ent.label == "MMLite"
        assert 0.0 <= ent.confidence <= 1.0
        assert payload_text[ent.start : ent.end] == ent.text

    # Strict prohibition on diagnostic predictions or probabilities
    forbidden_keys = {
        "diagnosis",
        "ppd_diagnosis",
        "ppd_probability",
        "probability",
        "risk_score",
        "risk_tier",
        "classification",
        "is_diagnostic",
    }
    assert forbidden_keys.isdisjoint(set(data.keys()))


def test_extract_empty_and_whitespace_input(
    api_client_with_small_predictor: TestClient,
):
    """Empty or whitespace-only text returns 200 with zero detected entities."""
    resp_empty = api_client_with_small_predictor.post(
        "/api/text-ner/extract",
        json={"text": ""},
    )
    assert resp_empty.status_code == 200
    empty_data = resp_empty.json()
    assert empty_data["total_entities_detected"] == 0
    assert empty_data["entities"] == []
    assert empty_data["processed_character_count"] == 0

    ws = "   \t\n  "
    resp_ws = api_client_with_small_predictor.post(
        "/api/text-ner/extract",
        json={"text": ws},
    )
    assert resp_ws.status_code == 200
    ws_data = resp_ws.json()
    assert ws_data["total_entities_detected"] == 0
    assert ws_data["entities"] == []
    assert ws_data["processed_character_count"] == len(ws)


def test_extract_max_length_boundary_and_overflow(
    api_client_with_small_predictor: TestClient,
):
    """Enforce TextNERPredictor.MAX_SAFE_CHARACTER_LIMIT (50,000 chars) on API boundary."""
    max_len = TextNERPredictor.MAX_SAFE_CHARACTER_LIMIT

    # Exactly max_len characters passes
    ok_resp = api_client_with_small_predictor.post(
        "/api/text-ner/extract",
        json={"text": "a" * max_len},
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["processed_character_count"] == max_len

    # Exceeding max_len returns 422 validation error
    too_long_resp = api_client_with_small_predictor.post(
        "/api/text-ner/extract",
        json={"text": "a" * (max_len + 1)},
    )
    assert too_long_resp.status_code == 422


def test_extract_missing_model_artifact_returns_503(tmp_path: Path):
    """Missing .joblib checkpoint must not crash startup and must return HTTP 503."""
    missing_path = tmp_path / "does_not_exist.joblib"
    service = TextNERService(
        predictor_factory=lambda: TextNERPredictor(model_path=missing_path)
    )
    service.startup()
    assert service.is_loaded is False

    app.dependency_overrides[get_text_ner_service] = lambda: service
    try:
        client = TestClient(app)
        resp = client.post("/api/text-ner/extract", json={"text": "feeling anxious"})
        assert resp.status_code == 503
        assert "missing or unavailable" in resp.json()["detail"].lower()

        # Health and other endpoints continue functioning
        assert client.get("/").status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "bad_body",
    [
        {},
        {"text": None},
        {"text": 12345},
        {"text": ["anxiety"]},
        {"text": "anxiety", "unexpected_field": "invalid"},
    ],
)
def test_extract_malformed_requests_return_422(
    api_client_with_small_predictor: TestClient,
    bad_body: dict,
):
    """Malformed JSON payloads must return HTTP 422 Unprocessable Entity."""
    resp = api_client_with_small_predictor.post("/api/text-ner/extract", json=bad_body)
    assert resp.status_code == 422


def test_extract_invalid_json_syntax_returns_422(
    api_client_with_small_predictor: TestClient,
):
    """Non-JSON request body returns HTTP 422."""
    resp = api_client_with_small_predictor.post(
        "/api/text-ner/extract",
        content="{broken json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_extract_inference_failure_returns_500_without_leaking_pii(
    caplog: pytest.LogCaptureFixture,
):
    """Internal predictor failure yields HTTP 500 and never logs raw input text."""

    class FailingMockPredictor:
        def predict(self, text: str) -> TextNEROutput:
            raise RuntimeError(f"Simulated crash containing narrative: {text}")

        def get_model_metadata(self) -> dict:
            return {"model_version": "mock-fail", "classifier_type": "mock"}

    service = TextNERService(predictor=FailingMockPredictor())  # type: ignore[arg-type]
    app.dependency_overrides[get_text_ner_service] = lambda: service
    sensitive_marker = "PATIENT_JANE_DOE_CONFIDENTIAL_NARRATIVE"

    try:
        with caplog.at_level(logging.DEBUG):
            client = TestClient(app)
            resp = client.post(
                "/api/text-ner/extract",
                json={"text": sensitive_marker},
            )

        assert resp.status_code == 500
        assert "inference error" in resp.json()["detail"].lower()
        assert sensitive_marker not in resp.json()["detail"]

        combined_logs = "\n".join(rec.getMessage() for rec in caplog.records)
        assert sensitive_marker not in combined_logs
        assert "error_type=RuntimeError" in combined_logs
        assert f"input_chars={len(sensitive_marker)}" in combined_logs
    finally:
        app.dependency_overrides.clear()


def test_extract_does_not_log_patient_narrative_or_entity_text(
    api_client_with_small_predictor: TestClient,
    caplog: pytest.LogCaptureFixture,
):
    """Successful requests log only non-PII counts and never log patient text or entity spans."""
    sensitive_name = "PATIENT_ALICE_998877"
    narrative = f"{sensitive_name} reports postpartum depression and anxiety."

    with caplog.at_level(logging.INFO, logger="ppd.text_ner"):
        resp = api_client_with_small_predictor.post(
            "/api/text-ner/extract",
            json={"text": narrative},
        )
        assert resp.status_code == 200

    combined_logs = "\n".join(rec.getMessage() for rec in caplog.records)
    assert sensitive_name not in combined_logs
    assert "postpartum depression" not in combined_logs
    assert "anxiety" not in combined_logs
    assert f"input_chars={len(narrative)}" in combined_logs
    assert "entities_detected=" in combined_logs


def test_text_ner_does_not_alter_or_override_epds_q10_safety(
    api_client_with_small_predictor: TestClient,
):
    """EPDS scoring and positive Question 10 urgent alert work independently of text NER."""
    # Even when text NER extracts zero entities from calm text, EPDS Q10 stays strictly enforced
    ner_resp = api_client_with_small_predictor.post(
        "/api/text-ner/extract",
        json={"text": "Feeling hopeful and rested after sleep."},
    )
    assert ner_resp.status_code == 200
    assert ner_resp.json()["total_entities_detected"] == 0

    # Positive Q10 on EPDS submission with low total score=1 MUST still trigger URGENT_SAFETY_ASSESSMENT
    answers = [
        {"question_id": f"EPDS_Q{i:02d}", "selected_index": 0 if i in {1, 2, 4} else 3}
        for i in range(1, 10)
    ]
    answers.append({"question_id": "EPDS_Q10", "selected_index": 2})  # score=1 ("Hardly ever")

    epds_resp = api_client_with_small_predictor.post(
        "/api/questionnaire/epds/submit",
        json={"answers": answers},
    )
    assert epds_resp.status_code == 200
    epds_data = epds_resp.json()
    assert epds_data["total_score"] == 1
    assert epds_data["safety_alert"]["triggered"] is True
    assert epds_data["safety_alert"]["severity"] == "URGENT_SAFETY_ASSESSMENT"


@pytest.mark.parametrize("version_tag,expected_version", [("v1.3.0", "1.3.0"), ("v1.2.0", "1.2.0")])
def test_extract_endpoint_supports_v130_and_v120_artifacts(version_tag: str, expected_version: str):
    """Verify FastAPI startup & POST /api/text-ner/extract with live v1.3.0 and v1.2.0 artifacts."""
    resolved = TextNERPredictor.resolve_model_path(model_version=version_tag)
    if not resolved.exists():
        pytest.skip(f"Model artifact {resolved} not present locally")

    service = TextNERService(
        predictor_factory=lambda: TextNERPredictor(model_version=version_tag)
    )
    service.startup()
    assert service.is_loaded is True

    app.dependency_overrides[get_text_ner_service] = lambda: service
    try:
        client = TestClient(app)
        sample_text = "Severe postpartum depression and anxiety symptoms while taking Zoloft."
        resp = client.post("/api/text-ner/extract", json={"text": sample_text})
        assert resp.status_code == 200
        body = resp.json()
        assert body["model_version"] == expected_version
        assert body["processed_character_count"] == len(sample_text)
        assert body["total_entities_detected"] == len(body["entities"])
        assert body["total_entities_detected"] >= 1
        for ent in body["entities"]:
            assert sample_text[ent["start"] : ent["end"]] == ent["text"]
            assert ent["label"] == "MMLite"
            assert 0.0 <= ent["confidence"] <= 1.0
    finally:
        app.dependency_overrides.clear()


