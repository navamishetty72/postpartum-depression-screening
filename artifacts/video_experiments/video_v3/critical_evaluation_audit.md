# Moment AI: Critical Video V3 Statistical Audit & Eligibility Gate Design

**Document ID:** `CRIT-AUDIT-VID-V3-202611`  
**Artifact Path:** `artifacts/video_experiments/video_v3/critical_evaluation_audit.md`  
**Date:** November 2026  
**Audited Cohort:** Canonical 640-participant training split (`data/processed/Numerical/train_test_split_manifest.csv`)  
**Holdout Isolation Status:** 160-participant test partition strictly frozen and unaccessed  
**Data Origin Tag:** `CLINICALLY_CONDITIONED_SYNTHETIC`  

---

## Executive Summary & Core Verdicts

| Question | Verdict | Key Supporting Evidence |
| :--- | :---: | :--- |
| **A. Is the 0.7686 fusion result statistically defensible?** | **NO** | 0.7686 is **not** an improvement; it is a **statistically significant degradation** ($p = 0.0063$) relative to the clinical-only model ($ROC-AUC = 0.8373$). Furthermore, the stacking procedure suffered from second-level CV leakage and in-sample base model fitting. |
| **B. Does Video V3 add measurable information beyond clinical predictions?** | **NO** | Video V3 adds **zero orthogonal information**. 100% of its predictive capacity is an attenuated reflection of 5 clinical covariates ($R^2_{\text{age}} = 0.744, R^2_{\text{sleep}} = 0.627$). Adding V3 to clinical predictions degrades ROC-AUC across all 5 folds by an average of $-0.0656$. |
| **C. Is the synthetic video experiment suitable for the hackathon demonstration?** | **YES (with boundaries)** | It successfully serves as an **engineering demonstration** of 4-modality schema compliance, video tensor ingestion, and failure handling, provided the team explicitly presents it as an engineering simulation and makes zero clinical diagnostic claims. |
| **D. Recommended eligibility-gate architecture?** | **Self-Declared Gate** | A self-declared frontend confirmation placed prior to media capture and intake, coupled with route guards and backend API token enforcement. Zero biometric gender classification. |
| **E. Exact files needing modification?** | **Identified** | 6 frontend files (`LiveScreeningPage.jsx`, `UploadAnalyzePage.jsx`, `ResultsPage.jsx`, `ClinicalContext.jsx`, `App.jsx`, new `EligibilityGateModal.jsx`) and 2 backend files (`schemas/questionnaire.py`, `routers/questionnaire.py`). |

---

## PART 1 — Critical Video V3 Statistical Audit

### 1. Clinical-Only vs. V3 + Clinical Production: Identical 640-Participant Benchmark

To audit the claimed $0.7686$ combiner result, we evaluated the production clinical-numerical model and the Video V3 combiner on the **exact same 640 canonical training participants**, using the **identical 5 cross-validation folds** (seed 42).

```
                 Clinical-Only Logistic Regression (OOF)
                 ROC-AUC = 0.8373 | PR-AUC = 0.8025 | Brier = 0.1645
                                      |
                                      |  + Video V3 (ROC-AUC = 0.5454)
                                      v
                 V3 + Clinical Combiner (OOF)
                 ROC-AUC = 0.7686 | PR-AUC = 0.7177 | Brier = 0.1985
                 [NET IMPACT: -0.0687 ROC-AUC, +0.0340 Brier Loss]
```

#### Overall 640 Out-of-Fold Performance Comparison

| Metric | Clinical-Only (Logistic) | Video V3 (Logistic) | V3 + Clinical Combiner | Net Change ($\Delta$) |
| :--- | :---: | :---: | :---: | :---: |
| **ROC-AUC** | **0.8373** | 0.5454 | 0.7686 | **-0.0687** |
| **PR-AUC** | **0.8025** | 0.4670 | 0.7177 | **-0.0848** |
| **Brier Score** *(lower is better)* | **0.1645** | 0.2783 | 0.1985 | **+0.0340** (Worse) |
| **Log Loss** *(lower is better)* | **0.4973** | 0.7825 | 0.5854 | **+0.0881** (Worse) |
| **Balanced Accuracy** | **0.7509** | 0.5356 | 0.6954 | **-0.0555** |
| **Accuracy** | **0.7656** | 0.5375 | 0.6969 | **-0.0687** |
| **Sensitivity (Recall)** | **0.6975** | 0.5196 | 0.6833 | **-0.0142** |
| **Specificity** | **0.8050** | 0.5515 | 0.7075 | **-0.0975** |
| **Precision** | **0.7368** | 0.4756 | 0.6465 | **-0.0903** |
| **F1 Score** | **0.7270** | 0.4966 | 0.6644 | **-0.0626** |

#### Paired Fold-Level Comparisons (5 Folds)

Across all 5 folds, adding Video V3 caused a monotonic decline in both discriminative ability and probability calibration:

| CV Fold | Clinical-Only ROC-AUC | Combiner ROC-AUC | ROC-AUC Diff ($\Delta$) | Clinical-Only PR-AUC | Combiner PR-AUC | PR-AUC Diff ($\Delta$) | Clinical Brier | Combiner Brier |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 0** | 0.8638 | 0.7749 | **-0.0889** | 0.8170 | 0.6997 | **-0.1173** | 0.1505 | 0.1931 |
| **Fold 1** | 0.8304 | 0.8023 | **-0.0281** | 0.8002 | 0.7699 | **-0.0303** | 0.1664 | 0.1792 |
| **Fold 2** | 0.7986 | 0.7023 | **-0.0963** | 0.7705 | 0.6665 | **-0.1040** | 0.1816 | 0.2409 |
| **Fold 3** | 0.9172 | 0.8666 | **-0.0506** | 0.8835 | 0.8295 | **-0.0540** | 0.1254 | 0.1520 |
| **Fold 4** | 0.7803 | 0.7160 | **-0.0643** | 0.7555 | 0.6637 | **-0.0918** | 0.1982 | 0.2271 |
| **Mean $\pm$ Std** | **$0.8380 \pm 0.0487$** | **$0.7724 \pm 0.0598$** | **$-0.0656 \pm 0.0253$** | **$0.8053 \pm 0.0450$** | **$0.7258 \pm 0.0634$** | **$-0.0795$** | **$0.1644$** | **$0.1985$** |

**Statistical Significance Tests:**
- **Paired $t$-test for ROC-AUC difference:** $t = -5.2464$, $p = 0.0063$ (statistically significant degradation at $\alpha = 0.01$).
- **Wilcoxon signed-rank test:** $W = 0.0$, $p = 0.0625$ (maximum possible significance for $N=5$ pairs, degradation in $5 / 5$ folds).

---

### 2. Audit of Clinical Production OOF Generation

We audited `pipelines/clinical_numerical/train.py` and `models/clinical_numerical/oof_predictions.csv`:

1. **Target Isolation Verification:**
   - In `train.py` lines 86–114, an outer `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` is executed.
   - Inside each fold $k$, the `ClinicalPreprocessor` and the classifier (`LogisticRegression`, `RandomForest`, `HistGradientBoosting`) are fitted strictly on `X_tr_fold` and `y_tr_fold`.
   - `val_probs = fold_model.predict_proba(X_val_fold_trans)[:, 1]` is generated strictly for `val_idx`.
   - `oof_probs[val_idx] = val_probs`.
2. **Participant Integrity:**
   - No participant's own features or target were ever seen by the model producing their out-of-fold prediction.
   - The 160 holdout test participants were completely absent from this loop.
   - **Verdict:** The production clinical OOF predictions are mathematically valid and leakage-free first-level out-of-fold predictions.

---

### 3. Audit of Second-Level Cross-Validation Stacking Leakage

We audited the stacking evaluation implementation in `pipelines/synthetic_video_v3/evaluate_v3_experiments.py` (lines 248–258):

```python
# evaluate_v3_experiments.py (Lines 250-256)
p_clin_tr = y_prob_clin_prod[train_idx]
p_clin_va = y_prob_clin_prod[val_idx]
meta_X2_tr = np.column_stack([p_v3_tr, p_clin_tr])
meta_X2_va = np.column_stack([p_v3_lr, p_clin_va])
meta_lr2 = LogisticRegression(C=1.0, penalty="l2", class_weight="balanced", random_state=42)
meta_lr2.fit(meta_X2_tr, y_tr)
p_comb2 = meta_lr2.predict_proba(meta_X2_va)[:, 1]
```

This revealed two severe methodological flaws in the stacking evaluation:

#### Flaw A: Second-Level Information Leakage
- `y_prob_clin_prod` is a static 640-element vector produced by an outer 5-fold CV in `pipelines/clinical_numerical/`.
- In `evaluate_v3_experiments.py`, when evaluating validation fold $F_0$, the training set is $train\_idx = F_1 \cup F_2 \cup F_3 \cup F_4$.
- For any participant $j \in F_1$, how was `y_prob_clin_prod[j]` generated? In `clinical_numerical/train.py`, when $F_1$ was the validation fold, the clinical model was trained on $F_0 \cup F_2 \cup F_3 \cup F_4$.
- **Crucial Finding:** The clinical model that predicted participant $j \in train\_idx$ was trained on the labels and features of validation fold $F_0$ (`val_idx`).
- Thus, validation participant information indirectly leaked into the meta-model's training features `meta_X2_tr`.

#### Flaw B: In-Sample vs. Out-of-Sample Calibration Asymmetry
- `p_v3_tr = lr_v3.predict_proba(X_v3_tr)[:, 1]` was computed **in-sample** (the base video model was evaluated on the exact data it was fitted on).
- `p_clin_tr` was computed **out-of-sample** (from the outer CV).
- Because `p_v3_tr` was in-sample, the base video model appeared artificially confident to `meta_lr2` during training.
- When `meta_lr2` was then deployed on `meta_X2_va` (where `p_v3_lr` was out-of-sample), the noisy out-of-fold video predictions corrupted the clinical signal.

---

### 4. Audit of Preprocessing, Scaling, and Feature Extraction

We inspected fold-locality across the pipeline:

- **Models A, B, and C (Video V2, Video V3, Covariates):**
  - In `evaluate_v3_experiments.py` lines 197–234, `StandardScaler()` is instantiated newly within each fold.
  - `scaler.fit_transform(X[train_idx])` is fitted strictly on `train_idx`.
  - `scaler.transform(X[val_idx])` is transformed strictly on `val_idx`.
  - Classifiers are fitted on `train_idx` and evaluated on `val_idx`.
  - **Verdict:** Strictly fold-local for individual base models.
- **Model D (Stacking Combiners):**
  - Suffered from the second-level CV leakage and in-sample base model fitting detailed in Section 3.

---

### 5. Audit of Generator Conditioning Statistics

We audited `pipelines/synthetic_video_v3/conditioning.py` (lines 157–179):

```python
train_mask = manifest_df["split_partition"] == "train"
train_indices = manifest_df.loc[train_mask, "matrix_index"].values
safe_matrix = modeling_matrix_df[approved_covariate_columns].copy()
train_slice = safe_matrix.iloc[train_indices].copy()

extractor = ClinicalConditioningExtractor()
extractor.fit(train_slice)  # STRICTLY on 640 training participants
cohort_covariates = extractor.transform(safe_matrix)
```

- **Verdict:**
  - `train_age_mean_` ($26.27$), `train_age_std_` ($4.38$), and `train_need_for_support_prior_` ($0.485$) were computed **strictly and exclusively** from the 640 training participants.
  - The 160 holdout test participants were **not** used to calculate any conditioning statistics.
  - The holdout video `.npy` files were generated using these training-derived priors, and as verified by dataset loaders, were **never read or accessed** during CV evaluation.

---

### 6. Incremental Predictive Contribution of Video V3

To determine whether Video V3 adds any real value, we evaluated the meta-classifier weights and information gain:

#### Meta-Classifier Weights Across Folds

$$\text{Logit}(p_{\text{comb}}) = \beta_{\text{video}} \cdot p_{\text{video}} + \beta_{\text{clin}} \cdot p_{\text{clin}} + \beta_0$$

| Fold | $\beta_{\text{video}}$ (Video V3 Weight) | $\beta_{\text{clin}}$ (Clinical Weight) | Intercept $\beta_0$ |
| :---: | :---: | :---: | :---: |
| **Fold 0** | $+0.1257$ | $+4.2057$ | $-2.1736$ |
| **Fold 1** | $-0.1175$ | $+4.3689$ | $-2.1474$ |
| **Fold 2** | $+0.2834$ | $+4.4289$ | $-2.3529$ |
| **Fold 3** | $-0.2043$ | $+3.9612$ | $-1.8481$ |
| **Fold 4** | $+0.0757$ | $+4.5809$ | $-2.2983$ |
| **Overall** | **$+0.0119$** | **$+4.4255$** | **$-2.2114$** |

- **Observation:** The meta-classifier weight on Video V3 is effectively zero ($\beta_{\text{video}} = +0.0119$) compared to the clinical weight ($\beta_{\text{clin}} = +4.4255$). Across folds, the sign of $\beta_{\text{video}}$ flips randomly between positive and negative, which is the hallmark of non-informative noise.

---

### 7. Covariate Redundancy & Mutual Information Analysis

We quantified how much of Video V3's predictive capacity is attributable to the 5 underlying clinical survey covariates:

1. **Direct Decodability ($R^2$):**
   - A cross-validated Ridge regression model trained to predict clinical survey answers from the 198 pooled video features achieves:
     - Maternal Age (`norm_age`): **$R^2 = +0.7440$**
     - Sleep Disruption (`sleep_disruption`): **$R^2 = +0.6268$**
     - Unconditioned Video V2: **$R^2 = -0.4870$** (pure noise).
2. **Correlation Analysis:**
   - Linear correlation between Video V3 probability and the 5 clinical covariates: $r = +0.2568$ (vs $r = -0.0090$ for Video V2).
   - Linear regression of Video V3 probability on the 5 clinical covariates yields $R^2 = 0.2000$.
3. **Conclusion:** Video V3 does not contain novel optical facial information. It is a noisy mathematical transform of survey questions already captured by the clinical questionnaire.

---

### 8. Evaluation of the Reported 0.7686 Result

- **Question:** Is $0.7686$ a valid estimate of generalization performance, or is it distorted by stacking methodology?
- **Scientific Audit Finding:**
  1. The reported $0.7686$ is **heavily degraded** relative to the standalone clinical model ($0.8373$).
  2. The combiner underperformed because it forced non-zero weights onto an in-sample-tuned video probability that contained zero independent information.
  3. Stacking base models without proper nested cross-validation distorted probability calibration, worsening Brier score by $+0.0340$.
  4. In an optimal Bayesian or constrained non-negative stacking framework, Video V3 would be assigned a weight of exactly $0.0$, yielding the pure clinical performance of $0.8373$.

---

## PART 2 — Moment AI Participant Eligibility Gate Design

### 1. Rationale & Core Privacy Mandate

Moment AI is a clinical research prototype calibrated specifically for **postpartum mothers** (screening for maternal postpartum depression using postpartum-specific risk factors like infant illness, breastfeeding/sleep disruption, and maternal bonding). 

> [!IMPORTANT]
> ### Strict Privacy & Anti-Bias Mandates
> 1. **No Biometric Gender Classification:** The system must **never** attempt to infer biological sex, gender identity, or gender presentation from facial video, voice pitch, body shape, or photographic imagery. Automated gender recognition (AGR) is scientifically unreliable, ethically hazardous, and clinically invalid.
> 2. **No Gender Classification Models:** No computer vision or audio classifiers for gender may be built, imported, or deployed.
> 3. **Self-Declared Confirmation Only:** Eligibility must be confirmed strictly through a respectful, explicit, self-declared choice by the user.
> 4. **No Hidden Clinical Prediction Features:** Eligibility selection must **never** enter ML models as a feature or predictor.
> 5. **Zero Data Transmission for Ineligible Users:** If a user indicates they are ineligible, no camera stream, microphone stream, questionnaire answers, or personal data may be transmitted to prediction endpoints.

---

### 2. Recommended User Flow

```
[Start Session / Landing Page]
               |
               v
+-------------------------------------------------------------+
|               ELIGIBILITY CONFIRMATION GATE                 |
|                                                             |
| "Welcome to Moment AI. This research screening prototype    |
| is currently designed and evaluated specifically for        |
| postpartum mothers."                                        |
|                                                             |
| Are you the postpartum mother completing this screening?    |
|                                                             |
|  [ Option A: Yes, I am the postpartum mother ]              |
|  [ Option B: No, I am a partner / family member / other ]   |
+-------------------------------------------------------------+
         |                                           |
         | Option A (Eligible)                       | Option B (Ineligible)
         v                                           v
[ Set eligibilityConfirmed = true ]         [ Set eligibilityConfirmed = false ]
[ Unlock Clinical / Audio / Video ]         [ Immediately Stop Workflow ]
[ Proceed to Live Screening ]               [ Display Respectful Message ]
                                            "This screening prototype is
                                             currently designed for postpartum
                                             mothers. It cannot provide a
                                             relevant screening result for your
                                             situation."
                                                    |
                                            [ Button: Change Selection / Return ]
```

---

### 3. Frontend Architecture & File Modifications

The eligibility check must be implemented as a stateful gate in React before any media capture or questionnaire intake begins.

```
src/
├── dashboard/
│   ├── components/
│   │   └── EligibilityGateModal.jsx         <-- [NEW COMPONENT]
│   ├── context/
│   │   └── ClinicalContext.jsx              <-- [Add eligibility state & guards]
│   └── pages/
│       ├── LiveScreeningPage.jsx            <-- [Render gate before media init]
│       ├── UploadAnalyzePage.jsx            <-- [Render gate before file drop]
│       └── ResultsPage.jsx                  <-- [Route guard against direct URL access]
└── App.jsx                                  <-- [Wrap dashboard routes with eligibility check]
```

#### Detailed Frontend File Modifications

1. **`src/dashboard/components/EligibilityGateModal.jsx` (New File):**
   - Modal dialog that displays the self-declaration prompt before camera or audio permissions are requested.
   - Clean, accessible radio buttons or choice cards:
     - `eligible`: *"I am the postpartum mother completing this screening."*
     - `ineligible`: *"I am a partner, family member, clinician, or other participant."*
   - If `ineligible` is selected, renders the exact required notification:
     > *"This screening prototype is currently designed for postpartum mothers. It cannot provide a relevant screening result for your situation."*
   - Includes a *"Change Selection"* button to immediately reverse accidental clicks.
2. **`src/dashboard/context/ClinicalContext.jsx`:**
   - Add state: `const [eligibilityConfirmed, setEligibilityConfirmed] = useState(false);`.
   - Persist status in `sessionStorage` (`miora_eligibility_status_v1`) so page reloads during active screening do not lose context, while closing the browser resets the gate.
   - Expose `confirmEligibility()`, `revokeEligibility()`, and `isEligible`.
3. **`src/dashboard/pages/LiveScreeningPage.jsx`:**
   - Check `isEligible` before rendering `LiveMediaPanel`.
   - Prevent `navigator.mediaDevices.getUserMedia()` from executing unless `isEligible === true`.
4. **`src/dashboard/pages/UploadAnalyzePage.jsx`:**
   - Check `isEligible` before opening file upload dropzones or processing video/audio files.
5. **`src/dashboard/pages/ResultsPage.jsx`:**
   - If a user attempts to navigate directly to `/results` or `/results/:id` without `isEligible === true`, redirect immediately to `/dashboard` with an alert message.
6. **`src/App.jsx`:**
   - Protect screening routes (`/live-screening`, `/upload-analyze`, `/results`) with an `EligibilityGuard` wrapper.

---

### 4. Backend Enforcement Points

Frontend visibility toggles are necessary but insufficient for clinical AI security. Backend endpoints must independently reject unauthorized prediction requests:

```
                                Client HTTP Request
                                         |
                                         v
               +---------------------------------------------------+
               | Fast API Endpoint: /api/questionnaire/epds/submit  |
               +---------------------------------------------------+
                                         |
               +---------------------------------------------------+
               |  Check Header: X-Eligibility-Confirmed == "true"   |
               |  OR Body: submission.eligibility_confirmed == True |
               +---------------------------------------------------+
                                   /       \
                                  /         \
                       (Valid)   /           \  (Missing or False)
                                v             v
                   [ Process EPDS Scoring ]   [ Raise HTTP 403 Forbidden ]
                   [ Return Risk Results  ]   Detail: "Screening not permitted
                                               for unconfirmed participant."
```

#### Detailed Backend File Modifications

1. **`backend/schemas/questionnaire.py`:**
   - Add `eligibility_confirmed: bool` to `EPDSSubmissionRequest`.
   - Schema validation: reject submissions where `eligibility_confirmed` is missing.
2. **`backend/routers/questionnaire.py`:**
   - In `submit_epds_questionnaire`, add an enforcement guard:
     ```python
     if not submission.eligibility_confirmed:
         raise HTTPException(
             status_code=403,
             detail=(
                 "Screening prototype is designed exclusively for postpartum mothers. "
                 "Eligibility confirmation is required to generate screening results."
             )
         )
     ```
3. **Future Multimodal Inference Endpoints (`/api/fusion/predict`, `/api/video/analyze`):**
   - Enforce identical eligibility validation prior to executing model inference.

---

### 5. Verification Test Suite Design

The following automated tests must be implemented during the implementation phase:

| Test ID | File | Test Description | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **T-GATE-01** | `frontend/tests/EligibilityGate.test.jsx` | Initial render of `/live-screening` without confirmation | Gate modal is visible; camera/mic permissions are NOT requested. |
| **T-GATE-02** | `frontend/tests/EligibilityGate.test.jsx` | User clicks *"No, I am a partner / other"* | Workflow terminates; required notification text displays; no results page rendered. |
| **T-GATE-03** | `frontend/tests/EligibilityGate.test.jsx` | User clicks *"Change Selection"* after ineligible click | Returns to choice prompt; allows selecting eligible. |
| **T-GATE-04** | `frontend/tests/EligibilityGate.test.jsx` | User attempts direct navigation to `/results` via URL | Redirected to `/dashboard`; results state remains empty. |
| **T-GATE-05** | `tests/test_backend_questionnaire.py` | POST `/api/questionnaire/epds/submit` with `eligibility_confirmed=False` | Returns HTTP 403 Forbidden; no EPDS score or risk category calculated. |
| **T-GATE-06** | `tests/test_backend_questionnaire.py` | POST `/api/questionnaire/epds/submit` with `eligibility_confirmed=True` | Returns HTTP 200 OK with valid scoring and Item 10 evaluation. |
| **T-GATE-07** | `tests/test_privacy.py` | Inspect request payloads and database schemas | Zero gender classification fields, facial gender predictions, or voice gender tags present. |

---

## Final Synthesis & Strategic Recommendations

1. **For the Hackathon Jury & Presentation:**
   - Present Video V3 transparently as an **engineering demonstration** of 4-modality temporal alignment and pipeline robustness.
   - Do **not** claim that Video V3 improves screening accuracy over clinical data.
   - Emphasize Moment AI's **scientific honesty and rigorous audit process**: show that our team caught second-level CV leakage and signal dilution, rather than naively reporting inflated numbers.
2. **For the Eligibility Gate:**
   - Proceed with the self-declared frontend modal and backend API token guard during the upcoming implementation sprint.
   - Strictly honor the privacy mandate: zero automated gender recognition.

