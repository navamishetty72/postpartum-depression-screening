# MIORA – Phase 6: Clinical Numerical Model Evaluation & Validation Report

**Research Component:** Clinical Numerical Screening Predictor (EPDS >= 13 Association)  
**Evaluation Cohort:** Independent Frozen Holdout Test Cohort ($N=160$, stratified $80/20$ split)  
**Primary Production Benchmark:** Balanced Random Forest Classifier  
**Evaluation Date:** November 2026  
**Clinical Status:** Research Screening-Support Prototype (Not a Medical Diagnostic Device)

---

## 1. Dataset Overview

The clinical numerical dataset consists of maternal survey responses gathered across clinical, obstetric, socioeconomic, and interpersonal lifestyle dimensions.

- **Total Cohort Size ($N$):** 800 participants
- **Training Partition ($N_{train}$):** 640 participants (80.0%)
- **Held-Out Test Partition ($N_{test}$):** 160 participants (20.0%)
- **Input Feature Count (Raw):** 46 features (2 numerical continuous/discrete, 44 categorical survey items)
- **Encoded Feature Count (Transformed):** 151 one-hot encoded binary features and scaled numeric streams
- **Partition Stratification:** Exact class-ratio preservation (43.91% positive in train, 43.75% positive in test)

---

## 2. Target Variable and Class Distribution

The target variable is defined canonically as:
$$\text{Target} = \mathbb{I}(\text{EPDS Score} \ge 13)$$

This binary threshold separates participants screening at high risk for major postpartum depression (EPDS $\ge 13$, a clinically standard triage threshold) from low/moderate-risk controls.

| Partition | Total Records | EPDS < 13 (Class 0, Negative) | EPDS >= 13 (Class 1, Positive) | Prevalence Rate |
|---|---|---|---|---|
| **Entire Dataset** | 800 | 449 | 351 | 43.88% |
| **Training Cohort** | 640 | 359 | 281 | 43.91% |
| **Held-Out Test Cohort** | 160 | 90 | 70 | 43.75% |

---

## 3. Data Leakage Audit Findings

A rigorous multi-layer leakage audit was executed across features, participants, and transformation pipelines:

| Audit Criterion | Verification Method | Result | Status |
|---|---|---|---|
| **Target Score Exclusion** | Checked 26 excluded columns (`EPDS Score`, `PHQ9 Score`, individual items 1–10) | 0 excluded columns present in feature matrix | **PASSED** |
| **Participant Disjointness** | Evaluated set intersection of train and test `participant_id` | 0 overlapping participants (640 vs 160) | **PASSED** |
| **Duplicate Record Isolation** | Checked identical feature rows across train and test partitions | 0 identical records across train/test boundary | **PASSED** |
| **Strict Pipeline Separation** | Verified preprocessor fitting exclusively on `X_train` | Medians and categorical sets fit only on train | **PASSED** |
| **Target Proxy / Leakage Screen** | Computed Cramér's V / Pearson correlation against target | Maximum association is $0.4287$ (< $0.60$ threshold) | **PASSED** |

### Top 5 Empirical Feature-Target Associations:
1. `Angry after latest child birth` (Cramér's V = 0.4287)
2. `Abuse` (Cramér's V = 0.3843)
3. `Relationship with the in-laws` (Cramér's V = 0.3322)
4. `Relationship with husband` (Cramér's V = 0.3264)
5. `Feeling about motherhood` (Cramér's V = 0.2881)

*Conclusion:* No mathematical target leakage or deterministic proxy exists. All predictors represent legitimate antecedent or concurrent clinical risk factors.

---

## 4. Train/Test Methodology and Pipeline Isolation

1. **Partitioning:** The dataset is split using a frozen manifest (`train_test_split_manifest.csv`) with random seed 42.
2. **Preprocessing:** 
   - Numerical features (`Age`, `Number of the latest pregnancy`) use median imputation with missing indicator flags, followed by standard scaling (zero mean, unit variance).
   - Categorical features use constant imputation (`'Missing'`) and one-hot encoding with `handle_unknown='ignore'`.
3. **Cross-Validation:** 5-fold Stratified Cross-Validation on the 640 training records with strict within-fold preprocessing.
4. **Final Evaluation:** Exactly ONE inference pass on the frozen 160 held-out test cohort.

---

## 5. Model Comparison Table (Test Set, Threshold = 0.5)

| Metric | Balanced Random Forest (Production) | HistGradientBoosting | Logistic Regression (Baseline) |
|---|---|---|---|
| **ROC-AUC** | **0.8187** (95% CI: [0.7518, 0.882]) | **0.8310** (95% CI: [0.77, 0.892]) | 0.8027 (95% CI: [0.7299, 0.867]) |
| **PR-AUC** | **0.8005** (95% CI: [0.7074, 0.8836]) | **0.8137** (95% CI: [0.7268, 0.8858]) | 0.7845 (95% CI: [0.6921, 0.872]) |
| **Sensitivity (Recall)** | **0.7714** (54 / 70) | 0.7000 (49 / 70) | 0.7286 (51 / 70) |
| **Specificity** | **0.7556** (68 / 90) | **0.7556** (68 / 90) | 0.7111 (64 / 90) |
| **Precision** | **0.7105** (54 / 76) | 0.6901 (49 / 71) | 0.6623 (51 / 77) |
| **F1-Score** | **0.7397** (95% CI: [0.6567, 0.8133]) | 0.6950 (95% CI: [0.6, 0.7832]) | 0.6939 (95% CI: [0.6069, 0.7808]) |
| **Accuracy** | **0.7625** (122 / 160) | 0.7312 (117 / 160) | 0.7188 (115 / 160) |
| **Balanced Accuracy** | **0.7635** | 0.7278 | 0.7198 |
| **Brier Score (MSE)** | 0.1796 | **0.1725** | 0.1820 |
| **False Negatives (Missed Cases)** | **16** | 21 (+31.2% missed) | 19 |
| **False Positives** | **22** | **22** | 26 |

---

## 6. Confusion Matrices (Threshold = 0.5)

```
Random Forest (Production):
                 Predicted Negative   Predicted Positive
Actual Negative         68 (TN)              22 (FP)
Actual Positive         16 (FN)              54 (TP)

HistGradientBoosting:
                 Predicted Negative   Predicted Positive
Actual Negative         68 (TN)              22 (FP)
Actual Positive         21 (FN)              49 (TP)

Logistic Regression:
                 Predicted Negative   Predicted Positive
Actual Negative         64 (TN)              26 (FP)
Actual Positive         19 (FN)              51 (TP)
```

---

## 7. Calibration Assessment & Brier Scores

Probability calibration was measured across 5 uniform bins:

| Model | Brier Score | Mean Predicted vs Empirical True Probabilities |
|---|---|---|
| **Random Forest** | 0.1796 | Bin 1: 0.162 -> 0.091; Bin 2: 0.282 -> 0.206; Bin 3: 0.484 -> 0.370; Bin 4: 0.689 -> 0.736; Bin 5: 0.826 -> 1.000 |
| **HistGradientBoosting** | 0.1725 | Bin 1: 0.096 -> 0.136; Bin 2: 0.299 -> 0.185; Bin 3: 0.474 -> 0.560; Bin 4: 0.728 -> 0.552; Bin 5: 0.885 -> 0.829 |
| **Logistic Regression** | 0.1820 | Bin 1: 0.103 -> 0.182; Bin 2: 0.299 -> 0.200; Bin 3: 0.507 -> 0.455; Bin 4: 0.691 -> 0.500; Bin 5: 0.892 -> 0.868 |

*Calibration Insight:* 
- Random Forest probabilities are monotonic across bins.
- Brier scores across all three models are between 0.172 and 0.182, confirming meaningful uncertainty estimation superior to an uninformative prior.

---

## 8. Exploratory Threshold Sweep (Random Forest)

*(Note: Alternative operating thresholds are strictly exploratory. The production threshold remains fixed at 0.50.)*

| Threshold | Sensitivity (Recall) | Specificity | Precision | F1-Score | Accuracy | TP | FP | FN | TN | Clinical Objective |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.30 | 0.9000 | 0.4222 | 0.5478 | 0.6811 | 0.6312 | 63 | 52 | 7 | 38 | Maximum Sensitivity Catch |
| 0.35 | 0.8857 | 0.4444 | 0.5536 | 0.6813 | 0.6375 | 62 | 50 | 8 | 40 | High Sensitivity Triage |
| 0.40 | 0.8714 | 0.5222 | 0.5865 | 0.7011 | 0.6750 | 61 | 43 | 9 | 47 | Enhanced Detection |
| 0.45 | 0.8286 | 0.6667 | 0.6591 | 0.7342 | 0.7375 | 58 | 30 | 12 | 60 | Balanced Clinical Triage |
| **0.50** | **0.7714** | **0.7556** | **0.7105** | **0.7397** | **0.7625** | **54** | **22** | **16** | **68** | **Production Baseline** |
| 0.55 | 0.6857 | 0.8000 | 0.7273 | 0.7059 | 0.7500 | 48 | 18 | 22 | 72 | Specificity Prioritized |
| 0.60 | 0.6286 | 0.8444 | 0.7586 | 0.6875 | 0.7500 | 44 | 14 | 26 | 76 | High Specificity |
| 0.70 | 0.3429 | 0.9889 | 0.9600 | 0.5053 | 0.7063 | 24 | 1 | 46 | 89 | Confirmation Gate |

---

## 9. Feature Importance Analysis (Random Forest)

### Top 15 Raw Feature Group Importances:
1. **Angry after latest child birth** (25.62%): Key indicator of postpartum emotional dysregulation, dysphoria, and irritability.
2. **Abuse** (10.62%): Strongly established risk factor across literature (domestic, verbal, emotional, physical adversity).
3. **Relationship with the in-laws** (6.66%): Significant social and family stressor in joint and extended household dynamics.
4. **Major changes or losses during pregnancy** (3.76%): Stressful life events and bereavement during gestation.
5. **Feeling about motherhood** (3.75%): Maternal adaptation difficulties and ambivalence.
6. **Recieved Support** (3.16%): Lack of practical postpartum childcare and recovery assistance.
7. **Need for Support** (3.15%): Subjective unmet psychological and social support needs.
8. **Relationship with husband** (2.96%): Marital conflict vs partner support.
9. **Feeling for regular activities** (2.88%): Energy levels, fatigue, and interest in daily activities.
10. **Fear of pregnancy** (2.39%): Antenatal anxiety and tokophobia.
11. **Relax/sleep when the newborn is asleep** (2.34%): Maternal insomnia and hyperarousal.
12. **Age of immediate older children** (1.68%): Short inter-pregnancy intervals and childcare burden.
13. **Education Level** (1.59%): Socioeconomic resilience factor.
14. **Depression during pregnancy (PHQ2)** (1.58%): History of antenatal depression symptoms.
15. **Trust and share feelings** (1.54%): Emotional confidant availability.

*Important Note on Feature Interpretability:* Feature importances denote Gini impurity reduction in tree decision splits and MUST NOT be construed as causal clinical pathways.

---

## 10. Limitations and Recommendations

1. **Screening Association vs Clinical Diagnosis:**
   - The ground truth target is defined by screening questionnaire cut-off (EPDS $\ge 13$), not a formal psychiatric diagnostic interview (e.g., SCID-5 or DSM-5 structured assessment).
   - Predictions identify mothers at heightened screening risk who warrant clinical assessment.
2. **Postpartum Irritability Weight:**
   - `Angry after latest child birth` represents 25.6% of model weight. While clinically relevant, models must be monitored to ensure irritability does not eclipse quieter depressive presentations (anhedonia, psychomotor slowing).
3. **Regional Demographics:**
   - Features like `Relationship with the in-laws` and `Family type` reflect cultural dynamics specific to South Asian cohorts; geographic retraining will be necessary before cross-cultural transfer.

---

## 11. Production Model Decision: Retain Balanced Random Forest

### Recommendation: **RETAIN BALANCED RANDOM FOREST**

**Clinical and Technical Justification:**
1. **Superior Sensitivity at Decision Threshold 0.5:**
   - Random Forest captures **77.14%** of at-risk mothers (54 / 70), missing only 16 cases.
   - HistGradientBoosting captures only **70.00%** (49 / 70), missing 21 cases (+31.2% false negatives).
   - In clinical screening, missing depressed mothers carries severe adverse maternal-infant consequences.
2. **Strongest F1-Score and Overall Accuracy:**
   - Random Forest achieves **F1 = 0.7397** and **Accuracy = 76.25%**, compared to HGB's **F1 = 0.6950** and **Accuracy = 73.12%**.
3. **Minimal ROC-AUC Difference:**
   - HGB's slight nominal lead in ROC-AUC (0.8310 vs 0.8187) is not statistically significant (95% bootstrap CIs heavily overlap: [0.770, 0.892] vs [0.752, 0.882]).
4. **Safety Escalation Guarantee:**
   - Random Forest model probabilities are strictly separated from EPDS Question 10 safety escalation. A low Random Forest probability ($p < 0.5$) NEVER suppresses an alert if Q10 suicide/self-harm ideation is endorsed.
