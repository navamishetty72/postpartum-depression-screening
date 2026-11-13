# Critical Scientific Review: Audio Generator Signal-to-Noise Calibration Audit

**Review Subject**: Audio Generator Signal-to-Noise Calibration Audit (Experiment 2 Planning)  
**Evaluator**: Antigravity Critical Science & Methodology Audit  
**Date**: 2026-11-13  
**Status**: **CONDITIONALLY APPROVED FOR RESEARCH SIMULATION ONLY**

---

## 1. Executive Summary & Review Scope

This document provides an independent, unsparing critical review of the **Audio Generator Signal-to-Noise Calibration Audit** documented in `generator_calibration_audit.md` and `proposed_scenarios.json`. 

The objective of this review is to evaluate:
1. The mathematical integrity of the noise variance and SNR formulations.
2. The accuracy and reproducibility of empirical and simulated Cohen's $d$ effect sizes.
3. The validity of literature citations, specifically auditing whether postpartum depression (PPD) studies provide direct numerical calibration.
4. Confounding and shared variance between synthetic acoustic conditioning covariates and the clinical numerical modality.
5. The true methodological nature of the proposed calibration scenarios.

---

## 2. Audit of Noise Variance Calculations

### 2.1 Clarification of "66% Noise Variance"
The calibration audit report stated that Scenario 2 *"retains substantial biological noise (66% noise variance)"*. This phrasing is mathematically ambiguous and requires immediate correction.

* **What the report actually measured**:
  In Scenario 2, residual Gaussian noise variance accounts for **$66.56\%$ of the total simulated feature variance** for `speech_rate` (and $63.56\%$ for `pause_ratio`). 
  $$\frac{\text{Var}(\text{Residual Noise})}{\text{Var}(\text{Total Feature Variance})} = \frac{\sigma_{\text{residual}}^2}{\sigma_{\Delta}^2 + \sigma_{\text{residual}}^2} = \frac{0.250^2}{0.1772^2 + 0.250^2} = \frac{0.06250}{0.03140 + 0.06250} = 66.56\%$$
  The clinical covariate shifts explain the remaining $33.44\%$ of total variance ($R^2 = 0.3344$).

* **Ratio of Scenario 2 Residual Variance to Baseline Residual Variance**:
  Relative to the existing baseline generator configuration, Scenario 2 represents a **drastic reduction in residual noise variance**, NOT a retention of 66% of baseline noise:
  - **`speech_rate_syllables_per_sec`**:
    - Baseline noise variance: $\sigma_{\text{base}}^2 = 0.550^2 = 0.30250$
    - Scenario 2 noise variance: $\sigma_{\text{scen2}}^2 = 0.250^2 = 0.06250$
    - Ratio ($\text{Scen2} / \text{Base}$): $\frac{0.06250}{0.30250} = \mathbf{0.2066}$ (**$20.66\%$**)
    - **Residual noise variance is reduced by $79.34\%$** relative to baseline.
  - **`pause_ratio`**:
    - Baseline noise variance: $\sigma_{\text{base}}^2 = 0.0600^2 = 0.00360$
    - Scenario 2 noise variance: $\sigma_{\text{scen2}}^2 = 0.0350^2 = 0.001225$
    - Ratio ($\text{Scen2} / \text{Base}$): $\frac{0.001225}{0.00360} = \mathbf{0.3403}$ (**$34.03\%$**)
    - **Residual noise variance is reduced by $65.97\%$** relative to baseline.

> [!IMPORTANT]
> **CORRECTION OF WORDING**:
> Scenario 2 does **not** retain $66\%$ of baseline noise variance. Rather, **within Scenario 2, residual noise constitutes $\approx 64\% - 67\%$ of total feature variance**, while reducing baseline noise variance by **$66\% - 79\%$**.

---

## 3. Independent Reproduction of Cohen's $d$ Calculations

We independently recalculated all effect sizes across the 640 canonical training participants ($n_1 = 281$ PPD+, $n_0 = 359$ PPD-). 

### 3.1 Mathematical Formulations
* **Group Ordering**: High Risk ($\text{PPD+}$, canonical $\text{EPDS} \ge 13$) minus Low Risk ($\text{PPD-}$, canonical $\text{EPDS} < 13$).
* **Pooled Sample Standard Deviation**:
  $$s_{\text{pooled}} = \sqrt{\frac{(n_1 - 1) s_1^2 + (n_0 - 1) s_0^2}{n_1 + n_0 - 2}}$$
* **Standardized Mean Difference**:
  $$d = \frac{\bar{y}_{\text{PPD+}} - \bar{y}_{\text{PPD-}}}{s_{\text{pooled}}}$$

### 3.2 Comparison of Observed Empirical vs. Simulated Values

```
1. Pure Clinical Covariate Shift Alone (Zero Noise Limit):
   - speech_rate shift       : Mean+ = -0.2877, Mean- = -0.1763, Diff = -0.1114, sp = 0.1686, Cohen d = -0.6608
   - pause_ratio shift       : Mean+ = +0.0426, Mean- = +0.0267, Diff = +0.0159, sp = 0.0253, Cohen d = +0.6299
   - speech_to_pause shift   : Mean+ = -3.2198, Mean- = -2.1036, Diff = -1.1162, sp = 1.7756, Cohen d = -0.6286

2. Observed Empirical Features (Actual data in audio_manifest.csv):
   - speech_rate_syllables_per_sec : Mean+ = 3.5082, Mean- = 3.6014, Diff = -0.0931, sp = 0.5992, Cohen d = -0.1554 (|d| = 0.155)
   - pause_ratio                   : Mean+ = 0.2779, Mean- = 0.2659, Diff = +0.0120, sp = 0.0665, Cohen d = +0.1803 (|d| = 0.180)
   - speech_to_pause_ratio         : Mean+ = 14.0952, Mean- = 14.7860, Diff = -0.6908, sp = 6.4831, Cohen d = -0.1066 (|d| = 0.107)

3. Simulated Calibration Scenarios (Identical participant covariates & labels, fixed seed 42):
   - Scenario 1 (Current: sigma = 0.550, 0.060):
     * speech_rate     : Diff = -0.1333, sp = 0.5683, Cohen d = -0.2345 (|d| = 0.235)
     * pause_ratio     : Diff = +0.0190, sp = 0.0597, Cohen d = +0.3189 (|d| = 0.319)
     * speech_to_pause : Diff = -1.5757, sp = 6.1519, Cohen d = -0.2561 (|d| = 0.256)
   - Scenario 2 (Conservative: sigma = 0.250, 0.035):
     * speech_rate     : Diff = -0.1213, sp = 0.2979, Cohen d = -0.4073 (|d| = 0.407)
     * pause_ratio     : Diff = +0.0178, sp = 0.0404, Cohen d = +0.4396 (|d| = 0.440)
     * speech_to_pause : Diff = -1.3083, sp = 3.0778, Cohen d = -0.4251 (|d| = 0.425)
   - Scenario 3 (Moderate: sigma = 0.170, 0.024):
     * speech_rate     : Diff = -0.1182, sp = 0.2369, Cohen d = -0.4988 (|d| = 0.499)
     * pause_ratio     : Diff = +0.0172, sp = 0.0332, Cohen d = +0.5174 (|d| = 0.517)
     * speech_to_pause : Diff = -1.2373, sp = 2.4112, Cohen d = -0.5132 (|d| = 0.513)
```

### 3.3 Verification Findings on Cohen's $d$
1. **Simulation Identity Verified**: We confirmed that the simulated scenario values were generated using the **exact same underlying participant covariates $x_i$, EPDS labels, and standard normal innovations $z_i \sim \mathcal{N}(0, I)$**, varying exclusively the diagonal residual scale matrix $D$.
2. **Empirical vs Simulated Separation**:
   - The observed data currently in `audio_manifest.csv` has $|d| \approx 0.155$ for `speech_rate` and $|d| \approx 0.180$ for `pause_ratio`.
   - The simulated Scenario 1 (re-generated with global seed 42) produces $|d| \approx 0.235$ and $|d| \approx 0.319$ due to individual realization noise in finite samples ($N=640$).
   - Both confirm that the current generator operates in a sub-clinical noise-dominated regime ($|d| < 0.25$).

---

## 4. Scientific Justification & Literature Grounding Audit

### 4.1 Do Any Postpartum Studies Provide Numerical Calibration for Rate or Pause?
**NO.**
* **Herrera et al. (2004)** ($N = 38$) assessed postpartum mothers via manual behavioral counts of affect-salient utterances during infant play. They reported an effect size on emotional prosody ($d \approx 0.76$), but **did not measure acoustic speech rate (syllables/sec) or pause proportion**.
* **Porritt et al. (2014)** ($N = 64$) measured acoustic pitch range ($\Delta F_0$) in infant-directed speech ($d \approx 0.55$), but **did not measure speech rate or pause ratio**.
* **Zero postpartum acoustic studies** in the published literature report quantitative pause fractions or syllable rates for clinical depression screening in rural or semi-urban South Asian cohorts.

### 4.2 Distinguishing Direct PPD Evidence from General Depression Evidence
* **Direct PPD Evidence Supports**:
  - The qualitative **direction of change**: depressed mothers display reduced vocal expressiveness, flatter affect, and slower response latencies during interactions.
* **General Adult Depression Evidence (Mundt 2007, Scherer 2013, Cummins 2015) Supports**:
  - The empirical finding that adult major depression produces temporal slowing with effect sizes typically between $d \approx 0.35$ and $d \approx 0.75$.
* **Critical Conclusion**:
  The numerical values in Scenario 2 ($\sigma_{\text{sr}} = 0.250\text{ syl/sec}$, $\sigma_{\text{pr}} = 0.0350$) are **NOT empirically calibrated from real postpartum recordings**. They are **engineering choices informed by adult depression literature**, designed to calibrate a synthetic benchmark fixture.

---

## 5. Potential Confounding & Shared Variance Audit

A critical methodological vulnerability exists in the conditioning architecture of `pipelines/synthetic_audio/conditioning.py`:

```
Covariate Correlations with EPDS Target (N = 640 Canonical Training Cohort):
  - maternal_affect   : Pearson r = +0.2829
  - support_deficit   : Pearson r = +0.2304
  - sleep_disruption  : Pearson r = +0.1804
  - infant_distress   : Pearson r = +0.1038
  - norm_age          : Pearson r = +0.0258
```

### 5.1 Mechanistic Implications
1. **The Generator Encodes Assumed Survey Relationships, NOT Physical Acoustics**:
   Because there are zero physical recordings in this cohort, acoustic features are generated as a linear combination of these 5 clinical survey covariates.
2. **Artificial Redundancy with the Clinical Numerical Modality**:
   The clinical numerical classifier already learns directly from `Relax/sleep`, `Support`, and `Feeling about motherhood`. When the synthetic audio generator creates `speech_rate` and `pause_ratio` from those same variables, **the audio modality becomes an imperfect, noisy linear proxy of the clinical numerical modality**.
3. **Risk of Circular Fusion Gains**:
   If we arbitrarily tune down residual noise in the generator, the downstream audio classifier's performance will increase simply because it is decoding the underlying clinical survey answers. In multimodal late fusion, this creates the **illusion of multimodal synergy** when in reality the models are learning from identical survey items.

---

## 6. What Real Data Would Be Required for True Empirical Calibration?

To transition the audio modality from a synthetic simulation fixture to an empirically grounded clinical pipeline, the following primary data would be required:

1. **Physical Acoustic Cohort**: Standardized uncompressed audio recordings ($16\text{ kHz}+$, $16\text{-bit PCM}$) of maternal speech from a representative South Asian postpartum cohort.
2. **Standardized Elicitation Protocol**:
   - Adult-directed clinical interview (measuring spontaneous narrative fluency and psychomotor latency).
   - Infant-directed interaction (measuring pitch range and emotional prosodic modification).
3. **Contemporaneous Diagnostic Assessment**: Gold-standard clinical psychiatric evaluation (SCID-5) administered simultaneously with the audio capture.
4. **Empirical Acoustic Feature Extraction**: Direct acoustic extraction (via Praat or openSMILE) to establish the true empirical covariance matrix $\Sigma$ and true group differences $(\bar{y}_+ - \bar{y}_-)$ without intermediate survey proxies.

---

## 7. Final Classification & Recommendation

### 7.1 Scenario Classification
* **Scenario 1 (Current Configuration)**: Uncalibrated high-noise engineering baseline ($\text{SNR}_{\text{var}} \approx 0.10$, Cohen's $d \approx 0.16 - 0.23$).
* **Scenario 2 (Proposed Calibration)**: **Exploratory engineering simulation scenario**, informed by general adult depression literature, but **uncalibrated against real postpartum speech**.
* **Scenario 3 (Moderate Calibration)**: Exploratory parity simulation ($\text{SNR}_{\text{var}} \approx 1.0$), assuming high acoustic separation ($d \approx 0.50$).

### 7.2 Strict Rule Against Target ROC-AUC Tuning
We explicitly reject setting noise parameters to achieve an arbitrary target ROC-AUC (e.g. "tuning noise until AUC = 0.65"). Noise should only be adjusted to test specific, documented architectural integration hypotheses under explicit simulation notices.

---

## 8. Verification & Approval Status

* **Files Modified**: **ZERO** production files were modified. `config.py`, `conditioning.py`, and `generator.py` remain untouched.
* **Holdout Set Isolation**: The 160-sample canonical holdout set was **never accessed, loaded, or inspected**.
* **Production Models**: Checkpoints in `models/audio_model/` and artifacts in `artifacts/audio_experiments/prosodic_pruning/` remain strictly frozen.

### Final Determination:
**CONDITIONALLY APPROVED FOR RESEARCH SIMULATION ONLY**

**Mandatory Conditions for Any Future Simulation Implementation**:
1. All generated audio datasets must retain the explicit metadata tag: `DATA_ORIGIN = "CLINICALLY_CONDITIONED_SYNTHETIC"`.
2. Any publication or technical report must explicitly state that Scenario 2 is an **exploratory engineering fixture**, NOT a clinically measured biomarker.
3. Multimodal fusion results must disclose that the synthetic audio modality shares mutual information with the clinical numerical modality due to conditioning on common survey covariates.
4. No generator modification may proceed without explicit user instruction.

---
*Critical review completed and certified on 2026-11-13.*

