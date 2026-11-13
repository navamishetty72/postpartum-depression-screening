# Text NER v1.3.0 Multimodal Integration Guide

This guide provides instructions and reference architecture for integrating the trained **Text Named Entity Recognition (NER) v1.3.0** model into multimodal fusion pipelines, speech-to-text intake transcripts, and the FastAPI backend service.

---

## 1. Model Purpose & Scientific Boundaries

- **Model Purpose:** Extracts biomedical and affective entity spans (`MMLite` concept mentions such as signs, symptoms, emotional states, and pharmacological references) from free-form clinical intake text and patient narratives.
- **Model Version:** `v1.3.0`
- **Training Corpus:** 10,548 BabyCenter postpartum health community discussion threads annotated via MetaMap Lite (MMLite) into Unified Medical Language System (UMLS) semantic categories.

> [!CAUTION]
> **Strict Scientific & Regulatory Constraints:**
> - **Biomedical NER Only — Not a Diagnostic Instrument:** The Text NER model identifies mention spans; it does **not** diagnose Postpartum Depression (PPD), compute diagnostic probabilities, or predict clinical risk categories.
> - **Confidence Score Semantics:** The `confidence` score (0.0 to 1.0) represents token classification confidence in span recognition under the vocabulary distribution, **not** clinical probability of depression.
> - **Never Override EPDS:** Extracted entities must never alter or override validated clinical psychometric instruments (e.g., EPDS) or Item 10 crisis escalation safety triggers.

---

## 2. Architecture, Algorithm & Features

- **Base Classifier:** Scikit-learn `SGDClassifier` configured with log-loss (`loss="log_loss"`) for calibrated token-level posterior probability estimates.
- **Tagging Scheme:** Standard `BIO` tagging (`B-MMLite` for span initiation, `I-MMLite` for span continuation, `O` for outside/non-entity tokens).
- **Feature Pipeline (`v2`):**
  - Sliding symmetric context window ($w = 2$, tokens $t-2$ through $t+2$).
  - Token lowercasing, prefix/suffix character n-grams (lengths 2, 3, 4).
  - Orthographic shape features: `is_title`, `is_upper`, `is_digit`, `has_hyphen`, `has_punctuation`.
  - Offset-preserving regular expression tokenization that maps predictions back to character coordinates `[start:end]` in original raw strings.
- **Sequence Decoding:** **Viterbi Decoding** (`use_viterbi=True`) with learned second-order BIO transition probabilities to forbid invalid state transitions (e.g. `O` $\to$ `I-MMLite`).

---

## 3. Verified Performance Metrics (Test Set Evaluation)

Evaluated on the leak-free, thread-isolated 15% test partition:

| Metric | Score | Clinical / Operational Relevance |
| :--- | :--- | :--- |
| **Recall** | **88.67%** | High sensitivity; captures ~89% of all biomedical entity mentions. |
| **Precision** | **65.13%** | Balances specificity against informal community/spoken vocabulary. |
| **F1-Score** | **75.10%** | State-of-the-art balance for shallow sequence models on forum text. |

---

## 4. Model Artifact Distribution & Download Instructions

The trained model checkpoint is approximately **89.66 MB** and is distributed through official GitHub Releases to avoid bloating Git repository history.

### Checkpoint Specifications
- **Target Path:** `models/text_ner/v1.3.0/text_ner_model.joblib`
- **File Size:** 89.66 MB (`94,014,515` bytes)
- **SHA256 Checksum:** `9797a6058b8c5500cc989d917184a61a266c12d0335d82db9bc5f3128633d5ef`
- **Release Asset URL:** [https://github.com/navamishetty72/postpartum-depression-screening/releases/download/v1.3.0/text_ner_model.joblib](https://github.com/navamishetty72/postpartum-depression-screening/releases/download/v1.3.0/text_ner_model.joblib)

### Automated Download (Recommended)
Run the automated downloader script included in the repository:
```bash
python scripts/download_text_ner_artifact.py
```
This script downloads the artifact directly to `models/text_ner/v1.3.0/text_ner_model.joblib` and validates its SHA256 checksum automatically.

### Manual Download (cURL / PowerShell)
```powershell
# PowerShell
Invoke-WebRequest -Uri "https://github.com/navamishetty72/postpartum-depression-screening/releases/download/v1.3.0/text_ner_model.joblib" -OutFile "models/text_ner/v1.3.0/text_ner_model.joblib"

# Verify SHA256 checksum:
(Get-FileHash -Algorithm SHA256 models/text_ner/v1.3.0/text_ner_model.joblib).Hash -eq "9797a6058b8c5500cc989d917184a61a266c12d0335d82db9bc5f3128633d5ef"
```

---

## 5. Python Import & In-Memory Inference

Multimodal developers can directly load and query the model without retraining:

```python
from pipelines.text_ner.inference import TextNERPredictor, TextNEROutput

# 1. Initialize the thread-safe predictor (loads v1.3.0 default artifact)
predictor = TextNERPredictor()

# 2. Extract entities from free-form text or speech transcription
sample_text = (
    "Patient reports severe sadness, crying spells in the morning, "
    "and extreme fatigue since delivery."
)

output: TextNEROutput = predictor.predict(sample_text)

print(f"Model version: {output.model_version}")
print(f"Detected entities: {output.total_entities_detected}")
for entity in output.entities:
    print(f"  • '{entity.text}' [{entity.start}:{entity.end}] "
          f"Label={entity.label} Confidence={entity.confidence:.4f}")
```

### Missing Artifact Handling
If the `.joblib` artifact is not found at `models/text_ner/v1.3.0/text_ner_model.joblib`, `TextNERPredictor` raises a controlled, informative `FileNotFoundError` explaining how to download or generate the artifact.

---

## 6. Passing Transcribed Audio / Speech to the Model

When integrating with audio pipelines (e.g. Whisper, Google Speech-to-Text, or clinical audio transcription):

```python
def process_audio_transcript(transcript_text: str) -> dict:
    """Extract biomedical entities from clinical interview audio transcript."""
    predictor = TextNERPredictor()
    
    # Pre-clean transcription formatting if necessary
    cleaned_transcript = transcript_text.strip()
    
    # Perform extraction
    ner_result = predictor.predict(cleaned_transcript)
    
    # Return structured features for multimodal fusion
    return {
        "entity_count": ner_result.total_entities_detected,
        "processed_chars": ner_result.processed_character_count,
        "entities": [
            {
                "text": e.text,
                "label": e.label,
                "start": e.start,
                "end": e.end,
                "confidence": e.confidence,
            }
            for e in ner_result.entities
        ],
        "model_version": ner_result.model_version,
    }
```

---

## 7. FastAPI Backend HTTP Endpoint

The inference service is exposed via FastAPI:

### Endpoint
- **Method:** `POST`
- **Route:** `/api/text-ner/extract`
- **Headers:** `Content-Type: application/json`

### Request Body
```json
{
  "text": "I feel so anxious and exhausted every evening, and I can't sleep even when the baby sleeps."
}
```

### Response Body
```json
{
  "entities": [
    {
      "text": "anxious",
      "label": "MMLite",
      "start": 10,
      "end": 17,
      "confidence": 0.5842
    },
    {
      "text": "exhausted",
      "label": "MMLite",
      "start": 22,
      "end": 31,
      "confidence": 0.6120
    },
    {
      "text": "sleep",
      "label": "MMLite",
      "start": 62,
      "end": 67,
      "confidence": 0.4951
    }
  ],
  "total_entities_detected": 3,
  "processed_character_count": 92,
  "model_version": "1.3.0"
}
```

---

## 8. Summary of Integration Requirements

1. **Do not retrain the model:** Use `scripts/download_text_ner_artifact.py` to retrieve the pre-trained `v1.3.0` checkpoint.
2. **Character limit:** Up to 50,000 characters per call are supported with automated truncation protection.
3. **Multimodal fusion:** Combine extracted entity span counts and confidence vectors with audio CNN embeddings and numerical clinical covariates in downstream fusion networks.
