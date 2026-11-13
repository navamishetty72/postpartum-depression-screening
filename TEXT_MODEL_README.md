# Text Machine Learning Branch: Postpartum Depression Forum Named Entity Recognition (NER)

**Document Version:** 1.2.0  
**Pipeline Module:** `pipelines/text_ner/`  
**License:** Project Research License / Upstream MIT License  

---

## 1. Scientific Scope & Regulatory Boundaries

> [!CAUTION]
> ### CRITICAL SCIENTIFIC & METHODOLOGICAL CONSTRAINTS
> 1. **Biomedical Named Entity Extraction Only — Not a Diagnostic Instrument:**  
>    The dataset utilized for this pipeline is an annotated forum-text Named Entity Recognition (NER) dataset derived from public online discussion boards. It is **NOT** a participant-level psychiatric diagnostic dataset and does **NOT** provide verified clinical PPD-positive or PPD-negative classification labels.
> 2. **Strict Prohibition on Fabricated Diagnosis:**  
>    The text model extracts biomedical entity mentions (e.g., symptom phrases, medications, affective expressions) identified in the annotation configuration. It does **not** predict PPD diagnosis, compute diagnostic probabilities, or classify patients.
> 3. **Never Describe Extracted Entities as Diagnostic Probabilities:**  
>    Extracted entity confidence scores represent token classification confidence in span recognition under the vocabulary distribution, **not** clinical probability of depression.
> 4. **Limitations of Forum Text:**  
>    Online support community discussions reflect informal self-reports, lay descriptions, colloquialisms, and selection bias. They do not constitute standardized psychiatric evaluations or clinically calibrated psychometric observations.

---

## 2. Upstream Dataset & Provenance

- **Repository:** [`https://github.com/tirilab/ppd-named-entity-dataset`](https://github.com/tirilab/ppd-named-entity-dataset)
- **License:** MIT License (Copyright &copy; 2018 Translational Informatics @ Johns Hopkins University)
- **Scientific Publication:**  
  Chowdhuri S, McCrea S, Fushman DD, Taylor CO. *Extracting Biomedical Terms from Postpartum Depression Online Health Communities.* AMIA Summits on Translational Science Proceedings. 2019;2019:592. ([PMC6568056](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6568056/))
- **Source Data:** 10,548 BabyCenter.com forum threads (posts and comments) from three postpartum depression and anxiety discussion groups.
- **Annotation Tooling:** MetaMap Lite (MMLite) biomedical term extraction mapped to Unified Medical Language System (UMLS) semantic types and concept identifiers.
- **Local Storage:** `data/raw/ppd-named-entity-dataset/` (safely excluded from version control via `.gitignore`).

---

## 3. Annotation Schema & Brat Configuration

The corpus uses the standard Brat standoff format (`.ann`), where each text-bound annotation is recorded as:
```
T<id>\t<label> <start> <end>\t<span_text>
N<id>\tReference T<id> SemanticType:<sem_type>\t<sem_type>
N<id>\tReference T<id> ConceptId:<cui>\t<concept_name>
```

The canonical Brat configuration file is defined at [`pipelines/text_ner/annotation.conf`](file:///d:/ppd/pipelines/text_ner/annotation.conf):
```ini
[entities]
MMLite

[attributes]
SemanticType Arg:MMLite, Value:phsu|menp|orch|mobd|dsyn|sosy|socb|inbe|antb|bodm|inch|bacs|aapp|horm|bhvr
ConceptId Arg:MMLite, Value:<UMLS_CUI>
```

- **Entity Labels in Corpus:** 100% of text-bound spans (`T` records) carry the label `MMLite`.
- **Top UMLS Semantic Types:** `phsu` (Pharmacologic Substance), `menp` (Mental Process), `orch` (Organic Chemical), `mobd` (Mental or Behavioral Dysfunction), `dsyn` (Disease or Syndrome), `sosy` (Sign or Symptom).

---

## 4. Pipeline Architecture & Directory Layout

```
pipelines/text_ner/
├── __init__.py               # Public API exports
├── annotation.conf           # Formal Brat entity schema
├── config.py                 # Paths, random seeds (42), and hyperparameters
├── parser.py                 # Brat standoff format parser for .txt and .ann archives
├── validator.py              # Offset verification, bounds checks, overlap resolution
├── splitter.py               # Document/thread-isolated 70/15/15 dataset partitioning
├── features.py               # Offset-preserving regex tokenizer and orthographic features
├── models.py                 # Scikit-learn token sequence classifier with streaming sparse vectorization
├── train.py                  # Legacy training & evaluation entrypoint
├── final_eval.py             # Leak-free split, validation selection, checkpoint freezing & full final eval
├── evaluate.py               # Strict entity-span evaluator (exact boundaries + label)
└── inference.py              # Thread-safe predictor with Pydantic v2 schemas and model versioning
```

---

## 5. Data Validation & Preprocessing Audit

The preprocessing pipeline ([`pipelines/text_ner/validator.py`](file:///d:/ppd/pipelines/text_ner/validator.py)) performs comprehensive integrity auditing:
1. **Offset Order:** Verifies $start < end$.
2. **Boundary Bounds:** Verifies $0 \le start < end \le \text{length}(text)$.
3. **Exact Span Text Matching:** Verifies $text[start:end] == span\_text$.
4. **Offset Reconciliation:** Reconciles line-break and encoding drifts caused by Windows CRLF (`\r\n`) line endings using bounded local-window matching ($\pm 15$ characters).
5. **Deduplication:** Removes duplicate annotations on identical spans.
6. **Explicit Overlap Resolution:** Detects intersecting and nested spans and resolves them deterministically using a configurable policy (`longest` span retained).

### Validation & Reconciliation Audit Summary (`data/processed/text_ner/validation_report.json`)

| Metric | Count | Percentage / Note |
|---|---|---|
| **Total Ingested Documents** | 10,569 | 100.0% matching `.txt` and `.ann` pairs |
| **Documents with Annotations** | 10,524 | 99.57% |
| **Documents without Annotations** | 45 | 0.43% |
| **Total Raw Annotations** | 326,752 | Ingested from Brat files |
| **Exact Span Matches (Raw / Retained)** | 17,632 / 17,518 | Verbatim match as-is (after dedup & overlap resolution) |
| **Uniquely Reconciled Offset Spans** | 210,181 | Unambiguously aligned within $\pm 15$ char window |
| **Ambiguous Reconciliations (Dropped)** | 1,225 | $> 1$ candidate match in $\pm 15$ char window (`AMBIGUOUS_LOCAL_MATCH`) |
| **Failed Zero-Match Reconciliations (Dropped)** | 97,438 | $0$ candidate matches in $\pm 15$ char window (`FAILED_RECONCILIATION_ZERO_MATCH`) |
| **Out-of-Bounds Offsets (Dropped)** | 276 | Beyond file end |
| **Duplicate Annotations (Dropped)** | 31 | Redundant spans |
| **Overlapping Spans Resolved** | 84 | Resolved via `longest` span retention |
| **Final Retained Valid Spans** | **227,699** | Ground-truth non-overlapping NER spans |

**Offset Reconciliation Audit Findings:**
1. **Repeated Occurrences:** If a term drifts beyond $\pm 15$ chars while an identical repeated term lies inside `[start - 15, end + 15]` uniquely, naive window search could misbind. Keeping the search window tightly bounded ($\pm 15$) and discarding multi-match windows prevents intra-window ambiguity.
2. **Local Constraint:** Search is strictly bounded to `[max(0, start - 15), min(text_len, end + 15)]`.
3. **Multiple Match Detection:** Multiple occurrences within the window are detected via iterative search; `validator.py` now explicitly distinguishes `AMBIGUOUS_LOCAL_MATCH` (1,225 spans) from `FAILED_RECONCILIATION_ZERO_MATCH` (97,438 spans).
4. **CRLF & Unicode Handling:** Raw zip files retain Windows `\r\n` sequences while upstream MetaMapLite indices reflect LF/whitespace normalization; cumulative offset drift beyond 15 chars accounts for failed reconciliations rather than destructive text rewrites.
5. **Text Preservation:** `span.text` is preserved verbatim without mutation; only `start`/`end` coordinates are reconciled when an exact unique local match is verified.
6. **Overlap Handling:** `resolve_overlaps(..., strategy="longest")` deterministically discards shorter colliding fragments and records exact collision counts.

---

## 6. Dataset Splitting & Leak-Free Final Evaluation Split

Dataset partitioning ([`pipelines/text_ner/splitter.py`](file:///d:/ppd/pipelines/text_ner/splitter.py)) guarantees **strict document/thread isolation**:
- Split by entire original forum thread document (verified 10,569 unique IDs and 10,563 unique `# URL:` headers, 6 empty 0-byte docs), **never** by sentence or token.
- Zero thread/document leakage across partitions.

### 6.1 Legacy Initial Split (`seed=42`, `data/processed/text_ner/dataset_splits.json`)

> [!WARNING]
> **Evaluation Limitation on Legacy 150-Doc Split (`ec27965`):**  
> Prior reported metrics (`Precision: 0.5711`, `Recall: 0.8640`, `F1: 0.6877`) evaluated **only the first 150 of 1,586 test documents** (`test_docs[:150]`). Because error analysis was performed on those 150 test documents to inform feature/loss iteration, that 150-document result is **not** a pristine held-out evaluation and does **not** represent full test partition performance.

Legacy exposure audit reconstructed exact touched document sets:
- Previously trained (`old_train[:1500]`): `1,500` documents
- Previously tuned on validation (`old_val[:150]`): `150` documents
- Previously evaluated & error-analyzed (`old_test[:150]`): `150` documents
- Total previously exposed unique documents: **`1,800`** (leaving `8,769` completely untouched documents)

### 6.2 Fresh Leak-Free Final Split (`seed=2026`, `data/processed/text_ner/final_dataset_splits.json`)

To obtain an uncontaminated final benchmark, `split_leak_free_final(final_seed=2026)` sampled `final_test` (`1,586` docs, 15%) strictly from the `8,769` untouched documents (`excluded_prior_exposed_count = 1,800`), excluded the `150` previously inspected `old_test[:150]` docs from `val`, and verified:
- `overlap_verified_zero_doc_ids`: `true`
- `overlap_verified_zero_thread_urls`: `true`
- `final_test_zero_prior_exposure_verified`: `true`

| Partition | Documents | Retained `MMLite` Spans | Exposure Status |
|---|---|---|---|
| **Train (`final_dataset_splits.json`)** | 7,398 (70.0%) | 156,873 | Permitted development only |
| **Validation (`final_dataset_splits.json`)** | 1,585 (15.0%) | 35,948 | Clean model selection (excludes `old_test[:150]`) |
| **Fresh Final Test (`final_dataset_splits.json`)** | **1,586** (15.0%) | **34,878** | **Zero prior exposure** (0 of 1,800 exposed IDs) |
| **Total Corpus** | **10,569** (100.0%) | **227,699** | All source documents preserved |

---

## 7. Model Training, Validation Selection & Frozen Checkpoint (`v1.2.0`)

Model selection was conducted strictly on the clean `train` and `val` partitions (`pipelines/text_ner/final_eval.py`) using memory-safe chunked sparse vectorization (`TextNERModel.fit_documents(..., dtype=np.float32)`). `final_test` remained completely uninspected until after freezing.

### Validation Comparison (`val_docs[:400]`, 9,005 gold spans)

| Candidate Model | Train Docs | Tokens | Features | Val Prec | Val Rec | Val Micro F1 |
|---|---|---|---|---|---|---|
| `Enhanced_ModifiedHuber_C2.0_Train1500` | 1,500 | 1,152,191 | 555,410 | 0.5810 | 0.8841 | 0.7012 |
| `Enhanced_ModifiedHuber_C2.0_Train3500` | 3,500 | 2,737,569 | 949,923 | 0.5926 | 0.8600 | 0.7017 |
| `Enhanced_ModifiedHuber_C1.0_TrainAll` | 7,398 | 5,864,667 | 1,526,503 | 0.5855 | 0.8815 | 0.7036 |
| **`Enhanced_ModifiedHuber_C2.0_TrainAll`** | **7,398** | **5,864,667** | **1,526,503** | **0.5957** | **0.9021** | **0.7175** |

- **Full Validation Confirmation (`1,585` docs, `35,948` gold spans):** Precision `0.5957`, Recall `0.9001`, Micro F1 `0.7169` (`242.08s`).
- **Frozen Model Artifacts (saved before `final_test` evaluation):**
  - Checkpoint: `models/text_ner/text_ner_model.joblib` (`70,864,435` bytes / `67.58 MB`, SHA-256 `28d42e9b8c50f571c44e2fced9efcd25a60222ad37d9d3cbce029acab7941f2d`)
  - Configuration: `models/text_ner/model_config.json`
  - Version Metadata: `models/text_ner/model_version.json` (`model_version: "1.2.0"`, `base_git_commit: "ec27965"`)
  - Split Manifest: `data/processed/text_ner/final_dataset_splits.json`
  - Training Log: `models/text_ner/training_final.log`

---

## 8. Final Held-Out Test Set Evaluation (Complete Fresh Partition)

The frozen `v1.2.0` checkpoint was evaluated **once** across **all 1,586 fresh `final_test` documents** using **strict entity-span matching** (exact character offsets + entity label). Full metrics are saved in `data/processed/text_ner/final_evaluation_metrics.json` and [`docs/text_ner_final_evaluation_summary.json`](file:///d:/ppd/docs/text_ner_final_evaluation_summary.json).

| Evaluation Run | Partition Scope | Gold Support | Predicted | TP | FP | FN | Precision | Recall | Micro F1 | Macro F1 |
|---|---|---|---|---|---|---|---|---|---|---|
| Legacy Initial Baseline (`seed=42`) | `test[:150]` (non-pristine subset) | 3,146 | — | 1,935 | 2,087 | 1,211 | 0.4811 | 0.6151 | 0.5399 | 0.5399 |
| Legacy `ec27965` (`seed=42`) | `test[:150]` (inspected subset — not pristine) | 3,146 | 4,759 | 2,718 | 2,041 | 428 | 0.5711 | 0.8640 | 0.6877 | 0.6877 |
| **Frozen Final Model (`v1.2.0`, `seed=2026`)** | **Complete Fresh `final_test` (1,586 docs)** | **34,878** | **52,621** | **31,213** | **21,408** | **3,665** | **0.5932** | **0.8949** | **0.7134** | **0.7134** |

- **Strict Entity-Level Error Breakdown (1,586 docs):** `spurious_entity`: `19,917` | `boundary_mismatch_same_label`: `1,491` | `completely_missed_entity`: `1,971`
- **Full Final Test Evaluation Runtime:** `251.65s` (Total end-to-end selection + freezing + evaluation pipeline runtime: `3304.11s`)
- **Model Artifact Size:** `70,864,435` bytes (`67.58 MB`)

---

## 9. UMLS `SemanticType` & Sub-Type Audit

While all Brat `T` spans carry top-level label `MMLite`, normalized `N` annotations attach UMLS `SemanticType` attributes (`227,699` retained valid spans):
- **Schema Discrepancy:** Corpus contains **`28` distinct semantic types**, whereas `annotation.conf` declares only **`15`**. Omitted types actually appearing in `.ann` files include `imft` (`799`), `vita` (`658`), `hops` (`545`), `elii` (`488`), `cgab` (`302`), `acab` (`134`), `clnd` (`25`), `irda` (`22`), `food` (`21`), `nnon` (`10`), `cell` (`3`), `enzy` (`2`), `anab` (`1`).
- **Multi-Label Ambiguity:** **`58,479 / 227,699` (`25.68%`)** of retained spans carry **2–6 simultaneous semantic types** (`2` types: `51,499`; `3`: `6,832`; `4`: `132`; `6`: `16`), dominated by `orch+phsu` (`40,816` spans — almost all drug mentions), `mobd+orch+phsu` (`4,638`), and `antb+orch` (`4,360`). Only `13` of `28` types ever appear standalone (the other `15` have `0` single-label occurrences; e.g., `orch` appears `54,114` times total but only `667` times standalone).
- **Support Tiers Across Validated Spans:**
  - *High Support ($\ge 5,000$ total mentions):* `phsu` (`65,190`), `menp` (`58,634`), `orch` (`54,114`), `mobd` (`48,886`), `dsyn` (`19,943`), `sosy` (`18,632`), `socb` (`5,957`), `inbe` (`5,331`).
  - *Moderate Support ($500\text{--}4,999$):* `antb` (`4,422`), `bodm` (`3,116`), `inch` (`1,422`), `bacs` (`1,421`), `aapp` (`1,197`), `bhvr` (`1,058`), `horm` (`1,005`), `imft` (`799`), `vita` (`658`), `hops` (`545`).
  - *Inadequate / Extreme-Tail Support ($< 500$):* `elii` (`488`), `cgab` (`302`), `acab` (`134`), `clnd` (`25`), `irda` (`22`), `food` (`21`), `nnon` (`10`), `cell` (`3`), `enzy` (`2`), `anab` (`1`).
- **Recommendation:** Do **not** blindly split `MMLite` into 28 flat single-label NER classes — forced single-label BIO tagging breaks on the `25.68%` multi-label spans (especially `orch+phsu`) and has unviable support in the `< 500` tail. Retain `MMLite` for span extraction and, if typed downstream features are desired later, aggregate into 4–5 coarse priority/multi-label semantic groups (e.g., Mental/Affective Process, Disorder/Symptom, Pharmacologic/Chemical, Social/Behavioral, Other) or resolve `ConceptId` / `SemanticType` cleanly via UMLS lookup post-extraction.

---

## 10. Reusable Inference Interface & FastAPI Integration Guide

The inference module ([`pipelines/text_ner/inference.py`](file:///d:/ppd/pipelines/text_ner/inference.py)) provides a defensive, thread-safe service ready for integration into the FastAPI backend or multimodal fusion combiner.

### Output Schemas (Pydantic v2)

```python
class TextEntitySpan(BaseModel):
    text: str        # Verbatim extracted entity text span
    label: str       # Entity category label ('MMLite')
    start: int       # 0-based character start index in source text
    end: int         # 0-based character end index in source text
    confidence: float # Model prediction confidence score [0.0, 1.0]

class TextNEROutput(BaseModel):
    entities: List[TextEntitySpan]
    total_entities_detected: int
    processed_character_count: int
    model_version: str = "1.0.0"  # Propagated from loaded model checkpoint (v1.2.0)
```

### Python Usage Example

```python
from pipelines.text_ner.inference import TextNERPredictor

# Initialize predictor (loads checkpoint from models/text_ner/text_ner_model.joblib)
predictor = TextNERPredictor()

# Run inference
result = predictor.predict(
    "Postpartum depression and anxiety symptoms after taking Zoloft."
)

print(f"Model: {result.model_version} | Entities found: {result.total_entities_detected}")
for entity in result.entities:
    print(f"[{entity.label}] '{entity.text}' ({entity.start}:{entity.end}) conf={entity.confidence:.2f}")
# Output (v1.2.0):
# [MMLite] 'Postpartum depression' (0:21) conf=0.67
# [MMLite] 'anxiety symptoms' (26:42) conf=0.58
# [MMLite] 'Zoloft' (56:62) conf=0.87
```

### FastAPI Endpoint Integration

The biomedical entity extraction branch is integrated into the FastAPI service:
- **Router:** [`backend/routers/text_ner.py`](file:///d:/ppd/backend/routers/text_ner.py) (`POST /api/text-ner/extract`)
- **Service (Startup-Loaded Singleton):** [`backend/services/text_ner_service.py`](file:///d:/ppd/backend/services/text_ner_service.py)
- **Request / Response Schemas:** [`backend/schemas/text_ner.py`](file:///d:/ppd/backend/schemas/text_ner.py) (`TextNERExtractRequest`, re-exporting `TextNEROutput` & `TextEntitySpan`)
- **Documentation & Sample Payloads:** See [`backend/README.md`](file:///d:/ppd/backend/README.md).

---

## 11. How to Reproduce Final Evaluation & Tests

```bash
# 1. Download/verify dataset in data/raw/
git clone --depth 1 https://github.com/tirilab/ppd-named-entity-dataset.git data/raw/ppd-named-entity-dataset

# 2. Run leak-free splitting, validation selection, freezing & complete 1,586-doc evaluation
python -u -m pipelines.text_ner.final_eval --seed 2026 --val_eval_limit 400

# 3. Execute the unit & integration test suite
python -m pytest tests/test_text_ner.py -v
```
