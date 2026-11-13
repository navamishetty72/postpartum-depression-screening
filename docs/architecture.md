# Multimodal PPD Recognition Prototype: System Architecture

**Document Version:** 1.1.0  
**Project:** Postpartum Depression (PPD) Recognition Research Prototype  
**Scope:** Architectural specification for 4-branch multimodal screening integration.

---

## 1. High-Level Architecture

The prototype integrates four specialized feature pipelines into a central late fusion combiner:

```
+-------------------------------------------------------------------------------------------------+
|                                 AUTHENTIC CLINICAL RECORDS (N=800)                              |
|                              (data/raw/ - Excluded from Git Tracking)                           |
+-------------------------------------------------------------------------------------------------+
                                                  |
                     +----------------------------+----------------------------+
                     | Non-Target Clinical Covariates (Age, Sleep, Support, etc.)|
                     v                                                         v
+---------------------------------------+    +---------------------------------------+    +---------------------------------------+
|    PIPELINE 2: SYNTHETIC AUDIO       |    |     PIPELINE 3: SYNTHETIC TEXT        |    |    PIPELINE 4: SYNTHETIC VIDEO        |
|  - 7 physiological summary scalars    |    |  - Semi-structured intake notes       |    |  - OpenFace AU dynamic trajectories   |
|  - (T, 128) float32 temporal tensors  |    |  - Sleep, infant care, domestic topics|    |  - AU04, AU12, AU15, gaze angles      |
+---------------------------------------+    +---------------------------------------+    +---------------------------------------+
                     |                                                         |                               |
                     +----------------------------+----------------------------+-------------------------------+
                                                  |
                                                  v
+-------------------------------------------------------------------------------------------------+
|                       PIPELINE 1: CLINICAL NUMERICAL PIPELINE                                   |
|  - Preprocessing, validation, and feature scaling                                               |
|  - 46 non-target clinical demographic & obstetric predictors                                    |
|  - Canonical EPDS >= 13 supervised classification (HistGradientBoosting baseline)              |
+-------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+-------------------------------------------------------------------------------------------------+
|                                 MULTIMODAL LATE FUSION COMBINER                                 |
|  - Participant ID verification (BGD_001 to BGD_800)                                             |
|  - Provenance lineage tracking (REAL vs. CLINICALLY_CONDITIONED_SYNTHETIC)                      |
|  - Decision-level fusion (Weighted averaging, meta-classification, conformal prediction sets)   |
+-------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+-------------------------------------------------------------------------------------------------+
|                                     FASTAPI BACKEND SERVICE                                     |
|  - POST /predict/clinical                                                                       |
|  - POST /predict/multimodal                                                                     |
+-------------------------------------------------------------------------------------------------+
```

---

## 2. Core Research Principles & Boundaries

1. **Architectural Integration Benchmark:** The system tests multi-branch software integration, contract compliance, and late fusion algorithms under controlled conditions.
2. **Zero Real Patient Media:** The clinical dataset contains numerical survey records only. Zero real patient audio, video, or conversational transcripts exist in the cohort.
3. **Constructed Linkage:** Participant IDs establish constructed computational linkage, not actual multimodal patient observations.
4. **No Real-World Clinical Claims:** The prototype is not clinically validated for medical diagnosis or clinical decision support.

---

## 3. Synthetic Audio Pipeline Specification (Implemented)

The synthetic audio pipeline generates dual-representation profiles linked computationally to `BGD_001` through `BGD_800`:

1. **Acoustic Summary Features (7 Scalars):**
   - Fundamental frequency: $F_0$ mean ($[130.0, 310.0]\text{ Hz}$), $F_0$ std ($[8.0, 75.0]\text{ Hz}$)
   - Perturbation & Voice Quality: Jitter local ($[0.2, 5.5]\%$), Shimmer local ($[1.0, 16.0]\%$), HNR ($[8.0, 30.0]\text{ dB}$)
   - Prosodic Timing: Speech rate ($[1.8, 6.2]\text{ syll/s}$), Pause ratio ($[0.08, 0.65]$)
   - Sampling Method: Conditioned Multivariate Normal sampling using empirical acoustic correlation matrix $\mathbf{R}$ with hard physiological clamping.

2. **Abstract Temporal Embedding Tensors:**
   - Shape: $(T_i, 128)$, dtype `float32`, where $T_i \in [30, 90]$.
   - Dynamics: Autoregressive AR(1) temporal walk ($\alpha = 0.85$) anchored to projected summary acoustic state $\mathbf{h}_0$.
   - Purpose: Validates downstream temporal pooling and multimodal fusion tensor ingestion.

3. **Train/Test Isolation & Conditioning:**
   - Conditioning Covariates: Standardized `Age`, Sleep disruption, Psychosocial support deficit, Infant illness/worry stress, Maternal attitude.
   - Isolation Protocol: All scalers and neutral missingness priors fitted strictly on the 640 training participants.
   - Prohibitions: Zero access to EPDS/PHQ items, scores, or canonical targets.

4. **Provenance & Manifest:**
   - `data/synthetic/audio/audio_manifest.csv`: 800 participant rows tagged with `data_origin: CLINICALLY_CONDITIONED_SYNTHETIC` and `generation_seed: 42`.
   - `data/synthetic/audio/features/BGD_xxx.npy`: 800 tensor fixtures.


---

## 4. Synthetic Text Pipeline Specification (Phase 3.3 Specification)

The synthetic text pipeline generates fictional contextual narratives computationally linked to `BGD_001` through `BGD_800` to benchmark text ingestion and NLP classification branches within multimodal fusion:

1. **Scientific Framework & Modality Boundaries:**
   - **Fictional Contextual Vignettes:** The original Bangladeshi clinical cohort contains **zero interview transcripts, free-text intake notes, or recorded patient dialogues**.
   - **Language:** Written in English as a standard NLP benchmark representation, whereas original cohort participants were Bengali speakers.
   - **Zero Diagnostic Meaning:** Narratives depict non-diagnostic postpartum daily routines, household circumstances, and practical care adjustments. They do not constitute clinical evidence or authentic patient quotations.

2. **Approved Non-Target Conditioning Covariates:**
   - Household & Family Context: `Family type`, `Number of household members`, `Total children`, `Occupation After Your Latest Childbirth`.
   - Infant Care & Feeding: `Age of newborn`, `Breastfeed`, `Newborn illness`, `Worry about newborn`.
   - Sleep Windows & Practical Support: `Relax/sleep when newborn is tended `, `Relax/sleep when the newborn is asleep`, `Recieved Support`, `Need for Support` (with neutral prior handling for missing values), `Trust and share feelings`.

3. **Strict Target Leakage Prohibitions:**
   - Zero access to or influence from EPDS items (Q1–Q10), EPDS scores, screening thresholds, PHQ-9 items, PHQ-2 columns, or canonical binary targets.
   - The canonical target never influences narrative length, sentiment, vocabulary, emotional intensity, or topic selection.
   - Strictly prohibits diagnostic terminology (`depression`, `anhedonia`, `PPD`, `diagnosed`, `mental illness`, `suicidal ideation`).

4. **Generation Methodology & Determinism:**
   - Target Length: 120–220 words (3 cohesive thematic paragraphs, ~7–11 sentences).
   - High-Entropy Combinatorial Engine: Combines verified template slots with diverse syntactic sentence structures, clause connectors, and vocabulary pools to ensure non-repetitive phrasing ($>10^6$ syntactic permutations).
   - Diversity Guarantee: Pairwise Jaccard 3-gram similarity strictly bounded below 0.70 across all pairs.
   - Deterministic Seeding: Seeded per participant via `np.random.default_rng(42 * 10000 + participant_sr)`.

5. **Train/Test Isolation & Output Structure:**
   - Split Preservation: Exactly 640 training narratives and 160 testing narratives matching `train_test_split_manifest.csv`.
   - Frozen Prior: All vocabulary pools, category distributions, and neutral priors are fitted strictly on the 640 training participants.
   - Files: Saved under `data/synthetic/text/` (excluded from Git tracking via `.gitignore`):
     - `text_manifest.csv`: 800 rows tagged with `data_origin: SYNTHETIC_FICTIONAL_NARRATIVE`.
     - `narratives/BGD_001.txt` ... `BGD_800.txt`.


---

## 5. Synthetic Video Feature Pipeline Specification (Phase 3.4 Specification)

The synthetic video feature pipeline generates abstract tabular temporal feature trajectories computationally linked to `BGD_001` through `BGD_800` to benchmark sequence ingestion, temporal pooling, and multimodal fusion:

1. **Scientific Framework & Modality Boundaries:**
   - **Zero Video / Facial Images:** The Bangladeshi clinical survey cohort contains **zero video recordings, camera footage, or facial imagery**.
   - **Abstract Engineering Fixtures:** Generates numeric temporal feature vectors only (`.npy` tensors), not visual pixel arrays or reconstructed faces.
   - **Zero Diagnostic Meaning:** Facial Action Units and head movements are not validated biomarkers for PPD diagnosis in this cohort. The tensors are designed solely to test temporal sequence ingestion, dropout resilience, and fusion layer mechanics.

2. **Feature Schema (24 Feature Channels per Frame):**
   - **Facial Action Units (14 Channels in $[0.0, 5.0]$):** OpenFace-compatible continuous intensities:
     `AU01_r` (Inner brow), `AU02_r` (Outer brow), `AU04_r` (Brow lowerer), `AU05_r` (Upper lid), `AU06_r` (Cheek raiser), `AU07_r` (Lid tightener), `AU09_r` (Nose wrinkler), `AU10_r` (Upper lip), `AU12_r` (Lip corner puller), `AU14_r` (Dimpler), `AU15_r` (Lip corner depressor), `AU17_r` (Chin raiser), `AU20_r` (Lip stretcher), `AU25_r` (Lips part).
   - **Head Pose (3 Channels in Radians $[-\pi/3, \pi/3]$):** `pose_pitch`, `pose_yaw`, `pose_roll`.
   - **Eye Gaze Dynamics (3 Channels):** `gaze_angle_x` ($[-0.6, 0.6]$ rad), `gaze_angle_y` ($[-0.6, 0.6]$ rad), `gaze_stability` ($[0.0, 1.0]$).
   - **Facial Motion Dynamics (2 Channels in $[0.0, 1.0]$):** `rigid_motion` (velocity), `non_rigid_motion` (expression dispersion).
   - **Tracking Quality & Frame Status (2 Channels):** `tracking_confidence` ($[0.0, 1.0]$), `success_flag` ($\{0.0, 1.0\}$).

3. **Conditioning Decision: Unconditioned Autonomous Fixtures:**
   - Generated **independently of clinical survey labels** to prevent encoding pseudoscientific facial behavioral assumptions into synthetic data.
   - Eliminates synthetic leakage where downstream classifiers learn artificial facial artifacts that mimic survey targets.
   - Seeded exclusively by participant random state: `np.random.default_rng(42 * 10000 + participant_sr)`.

4. **Temporal Dynamics & Sequence Ingestion:**
   - Sequence Length: $T_i \in [45, 120]$ frames per participant.
   - Autoregressive Continuity: Smooth AR(1) state transitions ($\alpha = 0.88$) to simulate continuous physical motion.
   - Realistic Dropout Simulation: 3%–10% stochastic frame dropout simulating tracking failure or occlusion (`confidence < 0.60`, `success_flag = 0.0`).

5. **Train/Test Isolation & Output Contract:**
   - Frozen Cohort: Exactly 640 training and 160 testing records matching `train_test_split_manifest.csv`.
   - Artifacts: Saved to `data/synthetic/video/` (excluded from Git version control via `.gitignore`):
     - `video_manifest.csv`: 800 rows with metadata, sequence length, missing frame count, and provenance tag `SYNTHETIC_ABSTRACT_VIDEO_FEATURES`.
     - `features/BGD_001.npy` ... `BGD_800.npy`: Arrays of shape $(T_i, 24)$ with dtype `float32`.
