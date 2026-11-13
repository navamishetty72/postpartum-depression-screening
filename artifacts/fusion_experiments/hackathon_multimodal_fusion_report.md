# Moment AI: Multimodal Late Fusion Benchmark & Hackathon Integration Report

**Document ID:** `FUSION-BENCHMARK-HACKATHON-202611`  
**Artifact Path:** `artifacts/fusion_experiments/hackathon_multimodal_fusion_report.md`  
**Date:** November 2026  
**Audited Cohort:** Canonical 640-participant training split (`data/processed/Numerical/train_test_split_manifest.csv`)  
**Holdout Isolation Status:** 160-participant test partition strictly frozen and unaccessed  
**Backend API Integration:** `POST /api/fusion/screen` registered and verified  

---

## 1. Executive Summary & Mandatory Scientific Integrity Notice

> [!IMPORTANT]
> ### Mandatory Scientific Integrity & Provenance Disclosure
> 1. **Clinical Modality Grounding:** The clinical numerical model operates on authentic maternal demographic, obstetric, domestic, and psychosocial tabular data collected in the primary Bangladeshi cohort. Target labels (`target_canonical_epds_ge_13`) represent validated psychiatric screening thresholds.
> 2. **Synthetic Demonstration Fixtures:** Audio (acoustic vocal prosody), text (fictional clinical interview narratives), and video (24-channel facial action unit kinematics) modalities are **engineered synthetic research fixtures** developed to demonstrate software architecture and pipeline integration.
> 3. **Rejection of the Flawed 0.7686 Result:** The previously reported Video V3 + clinical combiner result ($ROC-AUC = 0.7686$) has been audited and rejected as an artifact of second-level cross-validation leakage and severe signal dilution.
> 4. **No Artificially Inflated Accuracy:** Moment AI does not fabricate performance. All evaluations reflect genuine out-of-fold predictions on the canonical 640 training participants.
> 5. **Non-Diagnostic Device:** Moment AI is an investigational screening research prototype, **not** a clinical diagnostic system.

---

## 2. Phase 1: Modality Inspection & Participant Alignment Audit

We audited the out-of-fold (OOF) prediction artifacts across all four modalities:

```
+---------------------------------------------------------------------------------------------------+
|                        CANONICAL SPLIT MANIFEST (N = 640 Training Rows)                           |
+---------------------------------------------------------------------------------------------------+
       |                                |                               |                        |
       v                                v                               v                        v
+------------------+           +------------------+           +------------------+      +------------------+
| Clinical Tabular |           | Acoustic Audio   |           | Narrative Text   |      | Facial Video     |
| 640 Rows         |           | 640 Rows         |           | 640 Rows         |      | 640 Rows         |
| 5-Fold Stratified|           | 5-Fold Stratified|           | 5-Fold Stratified|      | 5-Fold Stratified|
| Target: EPDS>=13 |           | Target: EPDS>=13 |           | Target: EPDS>=13 |      | Target: EPDS>=13 |
| [0.0105, 0.9964] |           | [0.3111, 0.6669] |           | [0.2546, 0.7237] |      | [0.3060, 0.7280] |
+------------------+           +------------------+           +------------------+      +------------------+
```

### Participant & Fold Alignment Matrix

| Modality | Source Artifact Path | Row Count | Target Column | Participant ID Alignment | Fold Partition Count | Fold Indexing |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Clinical** | `models/clinical_numerical/oof_predictions.csv` | 640 | `y_true` | **100% Identical** | 128 / fold (5 folds) | 1-based (1..5) |
| **Audio** | `models/audio_model/oof_predictions.csv` | 640 | `true_target` | **100% Identical** | 128 / fold (5 folds) | 1-based (1..5) |
| **Text** | `models/text_model/oof_predictions.csv` | 640 | `true_target` | **100% Identical** | 128 / fold (5 folds) | 1-based (1..5) |
| **Video (V2)** | `artifacts/video_model/canonical_aligned/oof_predictions_bilstm.csv` | 640 | `true_target` | **100% Identical** | 128 / fold (5 folds) | 0-based (0..4) |
| **Video (V3)** | `artifacts/video_experiments/video_v3/oof_predictions_v3.csv` | 640 | `y_true` | **100% Identical** | 128 / fold (5 folds) | 0-based (0..4) |

**Verification Outcome:** All five OOF files share identical participant ordering, identical ground truth labels ($359$ negative, $281$ positive, $43.91\%$ prevalence), and zero missing values. Cross-validation fold partitions match identically ($F_{\text{audio}} = F_{\text{text}} = F_{\text{video}} + 1 = F_{\text{clinical}}$).

---

## 3. Phase 2 & 3: Comprehensive Multi-Configuration Benchmark

All models were evaluated using **proper 5-fold cross-fitting** on the 640 canonical training participants. In cross-fitted stacking, the meta-model is trained on 4 folds (512 samples) and evaluated on the held-out validation fold (128 samples), iterating across all 5 folds to generate strictly out-of-fold meta-predictions.

### Comprehensive Benchmark Table (N = 640 OOF Participants)

| Model Configuration | Input Features / Combiner | ROC-AUC | PR-AUC | Brier Score | Log Loss | Balanced Acc. | F1-Score | Sensitivity | Specificity | Precision |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. Clinical-only** | 46 Clinical Features (Logistic) | **0.8373** | **0.8025** | **0.1645** | **0.4973** | **0.7509** | **0.7270** | **0.7580** | **0.7437** | **0.6984** |
| **B. Audio-only** | Acoustic Prosody (Logistic) | 0.5339 | 0.4759 | 0.2500 | 0.6932 | 0.5279 | 0.4782 | 0.4875 | 0.5682 | 0.4692 |
| **C1. Video-only (V2)** | 24-ch Recurrent BiLSTM | 0.4604 | 0.4078 | 0.2593 | 0.7121 | 0.4970 | 0.4914 | 0.5623 | 0.4318 | 0.4365 |
| **C2. Video-only (V3)** | 198 Summary Features (Conditioned) | 0.5454 | 0.4670 | 0.2783 | 0.7825 | 0.5356 | 0.4966 | 0.5196 | 0.5515 | 0.4756 |
| **D. Text-only** | TF-IDF + Logistic Regression | 0.6386 | 0.5579 | 0.2361 | 0.6649 | 0.5985 | 0.5581 | 0.5730 | 0.6240 | 0.5439 |
| **E. Clinical + Audio** | Cross-Fitted Logistic Meta | 0.8336 | 0.7990 | 0.1671 | 0.5079 | 0.7558 | 0.7325 | 0.7651 | 0.7465 | 0.7026 |
| **F1. Clinical + Video V2** | Cross-Fitted Logistic Meta | 0.8347 | 0.7997 | 0.1667 | 0.5069 | 0.7540 | 0.7304 | 0.7616 | 0.7465 | 0.7016 |
| **F2. Clinical + Video V3** | Cross-Fitted Logistic Meta | 0.8327 | 0.7981 | 0.1676 | 0.5088 | 0.7544 | 0.7313 | 0.7651 | 0.7437 | 0.7003 |
| **G. Clinical + Text** | Cross-Fitted Logistic Meta | 0.8340 | 0.7990 | 0.1671 | 0.5077 | 0.7526 | 0.7291 | 0.7616 | 0.7437 | 0.6993 |
| **H1. 4-Modality Fusion (V2)**| Cross-Fitted Logistic Meta | 0.8344 | 0.7983 | 0.1669 | 0.5073 | 0.7509 | 0.7270 | 0.7580 | 0.7437 | 0.6984 |
| **H2. 4-Modality Fusion (V3)**| Cross-Fitted Logistic Meta | 0.8319 | 0.7966 | 0.1678 | 0.5094 | 0.7495 | 0.7257 | 0.7580 | 0.7409 | 0.6961 |
| **H3. 4-Modality Equal-Weight**| Parameter-Free Mean | 0.8115 | 0.7735 | 0.2095 | 0.6106 | 0.7265 | 0.6998 | 0.7260 | 0.7270 | 0.6755 |
| **H4. Non-Negative Stacking** | Constrained Simplex Weights | **0.8360** | **0.8010** | **0.1650** | **0.4993** | **0.7509** | **0.7270** | **0.7580** | **0.7437** | **0.6984** |

---

## 4. Full Confusion Matrices (Threshold = 0.50, N = 640)

```
A. Clinical-Only (Logistic)            D. Text-Only (Logistic)                H4. Non-Negative Stacking
          Predicted                              Predicted                              Predicted
        Neg       Pos                          Neg       Pos                          Neg       Pos
Act Neg 267 (TN)   92 (FP)             Act Neg 224 (TN)  135 (FP)             Act Neg 267 (TN)   92 (FP)
Act Pos  68 (FN)  213 (TP)             Act Pos 120 (FN)  161 (TP)             Act Pos  68 (FN)  213 (TP)

H1. 4-Modality V2 (Logistic Meta)      H2. 4-Modality V3 (Logistic Meta)      H3. 4-Modality Equal-Weight Mean
          Predicted                              Predicted                              Predicted
        Neg       Pos                          Neg       Pos                          Neg       Pos
Act Neg 267 (TN)   92 (FP)             Act Neg 266 (TN)   93 (FP)             Act Neg 261 (TN)   98 (FP)
Act Pos  68 (FN)  213 (TP)             Act Pos  68 (FN)  213 (TP)             Act Pos  77 (FN)  204 (TP)
```

---

## 5. Key Scientific & Methodological Insights

### 1. Clinical Modality Anchor
The clinical numerical model ($ROC-AUC = 0.8373$) is the decisive anchor of Moment AI. Because maternal obstetric history, sleep disruption, and psychosocial support variables represent real, statistically significant psychiatric risk factors, the clinical model far outperforms any synthetic proxy.

### 2. Failure of Unconstrained Stacking & Equal-Weight Averaging
- **Equal-Weight Mean (H3):** Diluting high-confidence clinical probabilities ($0.8373$) with chance-level video ($0.4604$) and noisy audio ($0.5339$) causes an immediate performance drop to $ROC-AUC = 0.8115$ and degrades Brier score from $0.1645$ to $0.2095$.
- **Unconstrained Logistic Meta-Learner (H1/H2):** Meta-logistic regression assigns negative weights to noisy inputs ($\beta_{\text{video}} \approx -0.60$), attempting to subtract noise rather than combine signal. In clinical AI, assigning negative weights to positive risk indicators is clinically hazardous and uninterpretable.

### 3. Superiority of Constrained Non-Negative Stacking (H4)
When stacking is constrained to non-negative weights summing to $1.0$ ($\mathbf{w} \ge 0, \sum w_i = 1$), the optimizer automatically allocates:
- **Clinical:** **$97.98\%$** average weight across folds.
- **Text:** **$1.78\%$** average weight across folds.
- **Audio:** **$0.23\%$** average weight across folds.
- **Video:** **$0.00\%$** average weight across folds.

This preserves clinical integrity ($ROC-AUC = 0.8360$, Brier $= 0.1650$) while providing an interpretable, monotonic combination rule.

---

## 6. Phase 4: Holdout Protection Audit

- **Canonical Split Isolation:** The 160-participant holdout partition (`data/processed/Numerical/train_test_split_manifest.csv`) was **strictly protected**.
- **Zero Contamination:** No holdout rows, features, labels, or test predictions were accessed, inspected, or tuned against during this benchmark.
- **Existing Production Assets:** Models in `models/clinical_numerical/`, `models/audio_model/`, `models/text_model/`, and `artifacts/video_model/` were untouched.

---

## 7. Phase 5: Architecture & Backend Integration

We engineered the late fusion service and registered it with FastAPI:

### Integration Components

```
Client / Frontend (React)
           |
           v
POST /api/fusion/screen
           |
           +---> MultimodalScreeningRequest
                    ├── eligibility_confirmed: bool (MANDATORY GATE)
                    ├── clinical_prob: Optional[float]
                    ├── text_prob: Optional[float]
                    ├── audio_prob: Optional[float]
                    └── video_prob: Optional[float]
           |
           v
backend.services.fusion_service.MultimodalFusionService
           ├── 1. Eligibility Check (Raises HTTP 403 if False)
           ├── 2. Dynamic Missing Modality Re-normalization
           ├── 3. Non-Negative Stacking Computation
           └── 4. Non-Diagnostic Risk Categorization & Explainability Metadata
           |
           v
MultimodalScreeningResponse
    ├── screening_id: "SCR-..."
    ├── fusion_risk_score: float [0.0, 1.0]
    ├── screening_category: "Low Risk" | "Moderate Risk" | "Elevated Screening Risk"
    ├── modality_breakdown:
    │     ├── clinical: { origin: "REAL_CLINICAL_TABULAR", weight: 0.98 }
    │     ├── text:     { origin: "SYNTHETIC_RESEARCH_DEMO", weight: 0.02 }
    │     ├── audio:    { origin: "SYNTHETIC_RESEARCH_DEMO", weight: 0.00 }
    │     └── video:    { origin: "SYNTHETIC_RESEARCH_DEMO", weight: 0.00 }
    ├── is_diagnostic: False
    └── disclaimer: "Investigational research prototype only..."
```

### Safety & Explainability Principles
1. **Eligibility Enforcement:** Unconfirmed requests fail with HTTP 403 Forbidden.
2. **Graceful Missingness:** If a participant lacks video or audio, the engine re-normalizes weights across available modalities without fabricating synthetic default probabilities.
3. **Data Provenance Disclosure:** Every API response explicitly flags clinical data as `REAL_CLINICAL_TABULAR` and sensory data as `SYNTHETIC_RESEARCH_DEMO`.
4. **Non-Diagnostic Framing:** Results are strictly labeled as risk indicators for physician triage, never as clinical diagnoses.

---

## 8. Phase 6: Automated Test Suite Verification

We executed automated test suites covering all integration and safety requirements:

| Test Suite | File | Tests Run | Result | Duration | Scope |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Fusion Integration** | `tests/test_fusion_integration.py` | 7 | **7 PASSED** | 3.52s | Alignment, fold isolation, leakage checks, missing modality handling, eligibility gate rejection (403), schema, reproducibility. |
| **Existing Fusion Core** | `tests/test_fusion.py` | 7 | **7 PASSED** | 3.55s | Core artifact existence, partition disjointness, probability bounds. |
| **Backend API Suite** | `tests/test_backend_questionnaire.py` & `text_ner.py` | 23 | **21 PASSED, 2 SKIPPED** | 3.86s | EPDS scoring safety, Item 10 crisis escalation, biomedical entity extraction, error handling. |

---

## 9. Hackathon Demonstration Strategy

For the upcoming hackathon presentation:
1. **Showcase Technical Completeness:** Demonstrate that Moment AI successfully ingests 4 distinct data types (tabular questionnaire, speech audio, clinical text narrative, and OpenFace facial kinematics) through a unified, fault-tolerant backend.
2. **Highlight Scientific Honesty:** Present our audit openly. Explain that our team caught second-level CV leakage and rejected naive multimodal claims, opting for calibrated non-negative stacking that respects clinical evidence.
3. **Emphasize Privacy & Safety:** Highlight the self-declared participant eligibility gate (rejecting automated biometric gender classification) and the non-diagnostic clinical triage framing.

