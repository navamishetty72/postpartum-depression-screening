# Backend REST API

## Overview
This module exposes FastAPI REST endpoints for Postpartum Depression (PPD) screening support, verified EPDS questionnaire administration, and biomedical text entity extraction.

> [!IMPORTANT]
> **Scientific & Clinical Boundaries:**  
> - Neither the EPDS screening score nor the biomedical text NER endpoint constitutes a medical or psychiatric diagnosis.  
> - `POST /api/text-ner/extract` performs **biomedical entity extraction (`MMLite` spans)** only. It does **not** return a PPD diagnosis or PPD probability, and must **never** override EPDS scoring or Question 10 self-harm safety escalation.  
> - No patient narratives, EPDS item answers, or personally identifiable information (PII) are written to logs.

## Implemented Endpoints

- `GET /`: Health check and system metadata.
- `GET /api/questionnaire/epds`: Retrieve the verified 10-item EPDS question bank from `data/questions.json`.
- `POST /api/questionnaire/epds/submit`: Calculate validated EPDS score and enforce independent Question 10 safety alert rules.
- `POST /api/text-ner/extract`: Biomedical Named Entity Recognition (`MMLite` spans) powered by the preloaded [`TextNERPredictor`](file:///d:/ppd/pipelines/text_ner/inference.py).

### Planned Fusion / Multimodal Endpoints (Separate Branches)
- `POST /predict/clinical`: Single-record clinical inference.
- `POST /predict/clinical/batch`: Batch clinical inference.
- `POST /predict/multimodal`: 4-branch late fusion inference.
- `POST /predict/multimodal/batch`: Batch multimodal inference.

---

## Biomedical Text NER Integration (`POST /api/text-ner/extract`)

### Architecture & Lifecycle
- **Model Reuse:** Directly wraps [`pipelines/text_ner/inference.py`](file:///d:/ppd/pipelines/text_ner/inference.py) (`TextNERPredictor`) via [`backend/services/text_ner_service.py`](file:///d:/ppd/backend/services/text_ner_service.py).
- **Startup Initialization:** Loaded **once** during FastAPI `lifespan` startup in [`backend/main.py`](file:///d:/ppd/backend/main.py) (`text_ner_service.startup()`), never reloaded per request.
- **Privacy Guarantee:** Operational logs record only non-identifying telemetry (`input_chars`, `entities_detected`, `model_version`, or `error_type`). Patient narratives and extracted span strings are never logged.

### Sample Request
```http
POST /api/text-ner/extract HTTP/1.1
Content-Type: application/json

{
  "text": "Postpartum depression and anxiety symptoms after taking Zoloft."
}
```

### Sample Response (`200 OK`, Schema: `TextNEROutput`)
```json
{
  "entities": [
    {
      "text": "Postpartum depression",
      "label": "MMLite",
      "start": 0,
      "end": 21,
      "confidence": 0.6653
    },
    {
      "text": "anxiety symptoms",
      "label": "MMLite",
      "start": 26,
      "end": 42,
      "confidence": 0.5823
    },
    {
      "text": "Zoloft",
      "label": "MMLite",
      "start": 56,
      "end": 62,
      "confidence": 0.8664
    }
  ],
  "total_entities_detected": 3,
  "processed_character_count": 63,
  "model_version": "1.2.0"
}
```

### Validation & Error Handling
- **Empty / Whitespace Input (`""`, `"   "`):** Returns `200 OK` with `"entities": []`, `"total_entities_detected": 0`.
- **Maximum Input Length:** Rejects payloads exceeding `50,000` characters (`TextNERPredictor.MAX_SAFE_CHARACTER_LIMIT`) with HTTP `422 Unprocessable Entity`.
- **Malformed Requests:** Missing `"text"`, non-string values, extra unknown fields, or invalid JSON return HTTP `422 Unprocessable Entity`.
- **Missing Model Artifact:** App startup succeeds cleanly without crashing EPDS routes; calls to `POST /api/text-ner/extract` return HTTP `503 Service Unavailable`.
- **Inference Failures:** Unexpected runtime errors return sanitized HTTP `500 Internal Server Error` without exposing patient text.

### Local Run
```bash
uvicorn backend.main:app --reload
```
