# Clinical Numerical Modeling Pipeline

**Modality:** Authentic Clinical Survey Records (Bangladesh Postpartum Cohort)  
**Status:** Complete, Validated, Evaluated, and Ready for Multimodal Fusion  
**Target Variable:** Canonical Edinburgh Postnatal Depression Scale $\ge 13$ (`target_canonical_epds_ge_13`)  
**Cohort Size:** 800 participants (640 Train / 160 Holdout Test)

---

## 1. Overview & Research Context

This pipeline implements preprocessing, leakage isolation, cross-validation, baseline modeling, artifact serialization, and runtime inference for the authentic clinical survey data collected from 800 postpartum mothers in Bangladesh.

Unlike the audio, text, and video branches (which are abstract synthetic engineering fixtures), the clinical numerical branch represents the **authentic empirical anchor** of the PPD Multimodal Research Prototype. All multimodal late-fusion combiners and ablation experiments must be benchmarked directly against this clinical baseline.

---

## 2. Feature Schema & Strict Leakage Isolation

The pipeline strictly isolates the target variable and prevents any form of data leakage:

### A. Non-Target Predictors (46 Features)
- **Numerical Features (2):** `Age`, `Number of the latest pregnancy`.
- **Categorical Features (44):** Obstetric history, household structure, socio-economic factors, newborn feeding, infant health, marital dynamics, and non-target psychosocial support (`Residence`, `Education Level`, `Marital status`, `Monthly income before latest pregnancy`, `Family type`, `Relationship with husband`, `Relationship with the newborn`, `Recieved Support`, `Breastfeed`, etc.).
- **Encoded Dimension:** 151 features following one-hot encoding with unknown category ignoring.

### B. Strictly Excluded Columns (26 Features)
The following columns are blacklisted and programmatically blocked from model training and preprocessing:
1. **Target psychometric items:** All 10 individual EPDS questionnaire items (`You have been able to laugh...`, `You have felt sad or miserable`, etc.).
2. **Intermediate scores & results:** `EPDS Score`, `EPDS Result`, `PHQ9 Score`, `PHQ9 Result`.
3. **PHQ-9 screening items:** All 9 individual PHQ-9 items (`Little interest or pleasure...`, `Feeling down...`, etc.).
4. **Primary ground truth labels:** `EPDS_high_risk_screening_threshold`, `target_canonical_epds_ge_13`.
5. **Tracking and partition metadata:** `sr`, `participant_id`, `matrix_index`, `split_partition`.

### C. Frozen Partitioning (Zero Overlap)
- **Training Set:** 640 participants (`split_partition == 'train'`; 359 negative, 281 positive).
- **Holdout Test Set:** 160 participants (`split_partition == 'test'`; 90 negative, 70 positive).
- Zero participant ID overlap between splits ($\text{Train} \cap \text{Test} = \emptyset$).
- Preprocessing transformations are fitted strictly on the 640 training participants.

---

## 3. Implemented Baseline Models

Three diverse classifiers are configured in `pipelines/clinical_numerical/models.py` with reproducible seed (42) and class weighting:

1. **Random Forest Classifier (Primary Baseline):**
   - $n_{\text{estimators}}=100$, $\text{max\_depth}=5$, $\text{min\_samples\_split}=5$, $\text{min\_samples\_leaf}=2$, `class_weight='balanced'`.
2. **Histogram-Based Gradient Boosting (`HistGradientBoostingClassifier`, Alternative Baseline):**
   - $\text{max\_iter}=100$, $\text{max\_depth}=4$, $\text{learning\_rate}=0.05$, `class_weight='balanced'`.
3. **Logistic Regression (Linear Baseline):**
   - Solver: `lbfgs`, $C=0.1$, penalty: `l2`, `class_weight='balanced'`.

---

## 4. Empirical Evaluation Results

### A. 5-Fold Stratified Cross-Validation (Training Partition, $n=640$)
*Evaluated with fold-level preprocessing on the training cohort to ensure zero out-of-fold leakage. Model selection is performed strictly on these cross-validation metrics.*

| Model | CV ROC-AUC (Mean $\pm$ Std) | CV PR-AUC (Mean $\pm$ Std) | CV Balanced Acc | CV Sensitivity | CV Specificity | CV F1-Score | CV Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random Forest** (Selected) | $\mathbf{0.8438 \pm 0.0457}$ | $\mathbf{0.8137 \pm 0.0531}$ | $\mathbf{0.7618 \pm 0.0644}$ | $\mathbf{0.7687 \pm 0.0666}$ | $\mathbf{0.7549 \pm 0.0748}$ | $\mathbf{0.7393 \pm 0.0677}$ | $0.1711 \pm 0.0151$ |
| **Logistic Regression** | $0.8381 \pm 0.0487$ | $0.8076 \pm 0.0443$ | $0.7510 \pm 0.0430$ | $0.7580 \pm 0.0366$ | $0.7439 \pm 0.0638$ | $0.7278 \pm 0.0423$ | $\mathbf{0.1644 \pm 0.0251}$ |
| **HistGradientBoosting** | $0.8297 \pm 0.0477$ | $0.7896 \pm 0.0461$ | $0.7549 \pm 0.0508$ | $0.7686 \pm 0.0466$ | $0.7411 \pm 0.0684$ | $0.7330 \pm 0.0513$ | $0.1674 \pm 0.0245$ |

### B. Unbiased Holdout Test Set ($n=160$, 90 Negative / 70 Positive)
*Evaluated with non-parametric bootstrap estimation (1,000 resamples, 95% Confidence Interval).*

> [!IMPORTANT]
> **Methodological Boundary:** Holdout test results are reported **strictly as final evaluation estimates** of generalization error. In accordance with rigorous machine learning standards, the holdout test set was sequestered and **never used for model selection**, hyperparameter tuning, or threshold search, preventing test-set snooping and optimization bias.

| Model | Test ROC-AUC [95% CI] | Test PR-AUC [95% CI] | Test Accuracy | Balanced Acc [95% CI] | Sensitivity | Specificity | Precision | Test F1 [95% CI] | Brier Score | Confusion Matrix [TN, FP, FN, TP] |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random Forest** (Selected) | 0.8187 [0.7518, 0.8820] | 0.8005 [0.7074, 0.8836] | **76.25%** | **0.7635 [0.7000, 0.8294]** | **77.14%** | 75.56% | **71.05%** | **0.7397 [0.6567, 0.8133]** | 0.1796 | [68, 22, 16, 54] |
| **HistGradientBoosting** | **0.8310 [0.7700, 0.8920]** | **0.8137 [0.7268, 0.8858]** | 73.12% | 0.7278 [0.6568, 0.8040] | 70.00% | 75.56% | 69.01% | 0.6950 [0.6000, 0.7832] | **0.1725** | [68, 22, 21, 49] |
| **Logistic Regression** | 0.8027 [0.7299, 0.8670] | 0.7845 [0.6921, 0.8720] | 71.88% | 0.7198 [0.6529, 0.7928] | 72.86% | 71.11% | 66.23% | 0.6939 [0.6069, 0.7808] | 0.1820 | [64, 26, 19, 51] |

---

## 5. Model Selection Methodology & Justification

### Selected Primary Baseline Model: `random_forest` (`RandomForestClassifier`)

### Selection Criteria Rationale:
1. **Highest Cross-Validation Discrimination:** Selected strictly on the 640 training participants based on achieving the highest mean 5-fold cross-validation ROC-AUC of **$0.8438 \pm 0.0457$** (compared to $0.8381 \pm 0.0487$ for Logistic Regression and $0.8297 \pm 0.0477$ for HistGradientBoosting).
2. **Superior Precision-Recall Trade-off:** Achieved the highest cross-validation PR-AUC of **$0.8137 \pm 0.0531$** across training folds, reflecting robust discrimination on the minority high-risk screening class.
3. **Balanced Diagnostic Profile:** Cross-validation out-of-fold predictions exhibited balanced clinical sensitivity ($76.87\%$) and specificity ($75.49\%$), yielding the highest CV balanced accuracy ($76.18\%$) and CV F1-score ($0.7393$).
4. **Prevention of Test-Set Snooping:** Model selection must never be based on holdout test set performance. Selecting models based on holdout metrics introduces circular optimization bias and renders holdout performance estimates over-optimistic.

### Status of Alternative Models:
- **`hist_gradient_boosting` (Alternative Gradient Boosting Baseline):** Retained as a strong non-linear gradient-boosted tree baseline. While it demonstrated higher holdout test discrimination (Test ROC-AUC: 0.8310) and lower test Brier score (0.1725), holdout test metrics serve strictly as final evaluation estimates and are not valid selection criteria.
- **Clarification on Brier Score & Calibration:** Brier score is an aggregate proper scoring rule measuring overall mean squared error between predicted probabilities and binary outcomes. A lower Brier score reflects improved probabilistic accuracy but **does not prove or establish probability calibration** without dedicated reliability diagrams and goodness-of-fit calibration testing.
- **`logistic_regression` (Calibrated Linear Baseline):** Retained as an interpretable linear comparator.

---

## 6. Serialized Artifacts Inventory

All artifacts are persisted in `models/clinical_numerical/`:

| Artifact File | Size | Purpose |
| :--- | :---: | :--- |
| `random_forest.joblib` | 418.6 KB | **Primary selected baseline estimator** (highest training CV ROC-AUC: 0.8438). |
| `hist_gradient_boosting.joblib` | 146.9 KB | Alternative gradient boosting estimator (CV ROC-AUC: 0.8297). |
| `logistic_regression.joblib` | 2.1 KB | Calibrated linear baseline estimator (CV ROC-AUC: 0.8381). |
| `preprocessor.joblib` | 25.6 KB | Fitted `ClinicalPreprocessor` with median/constant imputation and one-hot encoding. |
| `metrics_summary.json` | 16.6 KB | Comprehensive metrics JSON containing CV folds and test bootstrap CIs. |
| `oof_predictions.csv` | 26.8 KB | Out-of-fold prediction probabilities for 640 training participants (for stacking). |
| `test_predictions.csv` | 6.8 KB | Holdout prediction probabilities for 160 testing participants (for late fusion). |

---

## 7. Developer Instructions: Reproduction & Usage

### A. Run Automated Unit Tests
```bash
python -m pytest tests/test_clinical_numerical.py -v
```

### B. Reproduce Training & Evaluation
To retrain baseline models and re-evaluate holdout metrics from scratch:
```bash
python -m pipelines.clinical_numerical.train
```

### C. Load Primary Selected Model (Random Forest) for Inference (Python API)
```python
import pandas as pd
from pipelines.clinical_numerical.pipeline import ClinicalNumericalPipeline
from pipelines.clinical_numerical.data_loader import load_clinical_data

# 1. Load data splits
X_train, y_train, manifest_train, X_test, y_test, manifest_test = load_clinical_data()

# 2. Load primary selected model (Random Forest, highest CV ROC-AUC: 0.8438)
pipeline = ClinicalNumericalPipeline.load("models/clinical_numerical", model_name="random_forest")

# 3. Batch prediction on holdout test set
probabilities = pipeline.predict_proba(X_test)
binary_predictions = pipeline.predict(X_test)
print(f"Random Forest Test Set Mean Risk Probability: {probabilities.mean():.4f}")

# 4. Single participant intake prediction
sample_record = X_test.iloc[0].to_dict()
sample_record["participant_id"] = "BGD_TEST_001"
result = pipeline.predict_single(sample_record)
print("Single Prediction Result:", result)
# Output: {'participant_id': 'BGD_TEST_001', 'predicted_risk_probability': 0.7105, 'risk_category': 'HIGH_RISK', ...}
```

### D. Load Alternative Baselines (HistGradientBoosting or Logistic Regression)
```python
# Load alternative gradient boosting baseline
pipeline_hgb = ClinicalNumericalPipeline.load("models/clinical_numerical", model_name="hist_gradient_boosting")
hgb_probs = pipeline_hgb.predict_proba(X_test)

# Load linear baseline
pipeline_lr = ClinicalNumericalPipeline.load("models/clinical_numerical", model_name="logistic_regression")
lr_probs = pipeline_lr.predict_proba(X_test)
```

---

## 8. Handoff to Next Developer: Multimodal Late Fusion Instructions

For the incoming developer responsible for Multimodal Fusion (`fusion/`):

1. **Primary Clinical Predictions for Stacking Meta-Classifiers (`models/clinical_numerical/oof_predictions.csv`):**
   - Contains columns: `participant_id`, `sr`, `y_true`, `random_forest_prob` (primary), `hist_gradient_boosting_prob` (alternative), `logistic_regression_prob`.
   - **Primary Feature:** Use `random_forest_prob` as the primary clinical numerical input feature when fitting meta-classifiers (stacking) to prevent training-set leakage.
   - Alternatively, evaluate multi-model stacking by passing all three model OOF probabilities.
2. **Primary Clinical Predictions for Holdout Late Fusion Evaluation (`models/clinical_numerical/test_predictions.csv`):**
   - Contains columns: `participant_id`, `sr`, `y_true`, `random_forest_prob` (primary), `hist_gradient_boosting_prob` (alternative), `logistic_regression_prob`.
   - Use `random_forest_prob` as the primary clinical predictor in soft-voting, rank-averaging, and stacked combiners evaluated on the 160 holdout test participants.
3. **Modality Benchmark Comparison Anchor:**
   - Benchmark all multimodal fusion combiners against the primary clinical numerical baseline (Random Forest holdout test ROC-AUC = 0.8187 [95% CI: 0.7518, 0.8820]):
     $$\Delta \text{ROC-AUC} = \text{ROC-AUC}_{\text{fusion}} - 0.8187$$
   - If comparing against the alternative HistGradientBoosting baseline, state explicitly:
     $$\Delta \text{ROC-AUC}_{\text{alt}} = \text{ROC-AUC}_{\text{fusion}} - 0.8310$$
