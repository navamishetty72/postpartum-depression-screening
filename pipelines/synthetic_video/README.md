# Synthetic Video Feature Pipeline

## Scientific Framework & Modality Disclaimer
> [!IMPORTANT]
> **Architectural Benchmark Only:** The Bangladeshi clinical survey cohort contains **zero video recordings, camera footage, or facial imagery**.
> The features generated in this pipeline are **abstract synthetic temporal feature trajectories** (24-channel numerical `.npy` arrays). They exist solely as engineering fixtures to benchmark temporal sequence ingestion, dynamic temporal pooling (mean, max, attention), tracking dropout resilience, and multimodal late fusion combiner architectures.
> - **Zero Facial Imagery:** No actual video footage, facial pictures, or identifiable human faces are generated or processed.
> - **Zero Diagnostic Biomarkers:** Facial Action Units and head pose dynamics do **not** diagnose postpartum depression in this study and must not be treated as clinical evidence.
> - **Autonomous Fixtures:** Trajectories are generated independently of clinical survey targets to prevent encoding unsupported behavioral assumptions.
> - **Target Isolation:** Complete isolation from EPDS items, EPDS scores, PHQ-9 items, and canonical screening targets.
> - **Engineering Assumptions:** All distributions, covariance structures, and temporal dynamics are explicitly engineering assumptions, not observed biological or psychological traits.

## Exact Channel Schema (24 Channels per Frame)
Channels are structured into two distinct categories:

### A. OpenFace-Style Facial & Head Dynamics (Channels 0–18)
- **Channel 0:** `AU01_r` – Inner brow raiser intensity $[0.0, 5.0]$
- **Channel 1:** `AU02_r` – Outer brow raiser intensity $[0.0, 5.0]$
- **Channel 2:** `AU04_r` – Brow lowerer intensity $[0.0, 5.0]$
- **Channel 3:** `AU05_r` – Upper lid raiser intensity $[0.0, 5.0]$
- **Channel 4:** `AU06_r` – Cheek raiser intensity $[0.0, 5.0]$
- **Channel 5:** `AU07_r` – Lid tightener intensity $[0.0, 5.0]$
- **Channel 6:** `AU09_r` – Nose wrinkler intensity $[0.0, 5.0]$
- **Channel 7:** `AU10_r` – Upper lip raiser intensity $[0.0, 5.0]$
- **Channel 8:** `AU12_r` – Lip corner puller (zygomaticus) intensity $[0.0, 5.0]$
- **Channel 9:** `AU14_r` – Dimpler intensity $[0.0, 5.0]$
- **Channel 10:** `AU15_r` – Lip corner depressor intensity $[0.0, 5.0]$
- **Channel 11:** `AU17_r` – Chin raiser intensity $[0.0, 5.0]$
- **Channel 12:** `AU20_r` – Lip stretcher intensity $[0.0, 5.0]$
- **Channel 13:** `AU25_r` – Lips part intensity $[0.0, 5.0]$
- **Channel 14:** `pose_pitch` – 3D head pitch angle in radians $[-\pi/3, \pi/3]$
- **Channel 15:** `pose_yaw` – 3D head yaw angle in radians $[-\pi/3, \pi/3]$
- **Channel 16:** `pose_roll` – 3D head roll angle in radians $[-\pi/3, \pi/3]$
- **Channel 17:** `gaze_angle_x` – Horizontal gaze direction in radians $[-0.6, 0.6]$
- **Channel 18:** `gaze_angle_y` – Vertical gaze direction in radians $[-0.6, 0.6]$

### B. Custom Engineered Summary & Tracking Status Features (Channels 19–23)
*(Note: Channels 19–23 are custom engineering fixtures and not direct OpenFace outputs)*
- **Channel 19:** `gaze_stability` – Fixation consistency scalar $[0.0, 1.0]$
- **Channel 20:** `rigid_motion` – Head motion velocity summary $[0.0, 1.0]$
- **Channel 21:** `non_rigid_motion` – Facial landmark deformation dispersion $[0.0, 1.0]$
- **Channel 22:** `tracking_confidence` – Frame-level face tracker confidence score $[0.0, 1.0]$
- **Channel 23:** `success_flag` – Binary tracking success indicator ($\{0.0, 1.0\}$; $0.0$ indicates simulated tracking loss / occlusion)

## Generated Outputs

### Version 1 Outputs (`pipelines/synthetic_video/generator.py`)
Outputs are saved to `data/synthetic/video/` (excluded from Git version control via `.gitignore`):
- `video_manifest.csv`: 800 participant records (640 train, 160 test) linked to `BGD_001`–`BGD_800`.
- `features/`: 800 individual NumPy `.npy` files (`BGD_001.npy` to `BGD_800.npy`) of shape $(T_i, 24)$ and dtype `float32`.
- Provenance: `data_origin = SYNTHETIC_ABSTRACT_VIDEO_FEATURES`, `generator_version = 1.0.0`.

### Version 2 Outputs (`pipelines/synthetic_video/generator_v2.py`)
Improved physiological simulation outputs are saved separately to `data/synthetic/video_v2/`:
- `video_manifest.csv`: 800 participant records (640 train, 160 test) linked to `BGD_001`–`BGD_800`.
- `features/`: 800 individual NumPy `.npy` files (`BGD_001.npy` to `BGD_800.npy`) of shape $(T_i, 24)$ and dtype `float32`.
- Provenance: `data_origin = SYNTHETIC_ABSTRACT_VIDEO_FEATURES_V2`, `generator_version = 2.0.0`.
- Enhanced fields: `burst_count` (number of contiguous dropout bursts per participant).

## Key Improvements in Generator V2
1. **Physiological Action Unit Co-activation:** Replaces independent AR(1) Gaussian noise with a $14 \times 14$ covariance matrix modeling FACS synergies:
   - Duchenne smile cluster: AU06 + AU12 ($r = +0.58$)
   - Eyebrow elevation: AU01 + AU02 ($r = +0.60$)
   - Brow furrow / concentration: AU04 + AU07 ($r = +0.46$)
   - Nasolabial elevation: AU09 + AU10 ($r = +0.52$)
2. **Channel-Specific Baselines & Anatomical Diversity:** Each AU has differentiated resting means and standard deviations, plus participant-specific resting baseline offsets.
3. **Coupled Head Pose & Gaze Kinematics:** Natural cervical coupling between yaw and roll ($r = -0.22$) with smooth autoregressive trajectories.
4. **Analytically Derived Metrics:**
   - `gaze_stability`: $\exp(-\Delta \theta / (\omega_0 \cdot \Delta t)) \in (0, 1]$ where $\omega_0 = 3.0\text{ rad/s}$.
   - `rigid_motion`: $\tanh(\Delta \Omega / (v_0 \cdot \Delta t)) \in [0, 1)$ where $v_0 = 4.0\text{ rad/s}$.
   - `non_rigid_motion`: $\tanh(\Delta \text{AU} / (\alpha_0 \cdot \Delta t)) \in [0, 1)$ where $\alpha_0 = 4.0\text{ units/s}$.
5. **Temporally Clustered Dropout Bursts:** Models contiguous occlusions (mean burst length: 4.23 frames; 0% isolated drops) while strictly preserving the $3\%\text{--}10\%$ dropout bounds.
6. **Strict Target Isolation:** Zero conditioning on EPDS, PHQ-9, or clinical risk labels ($p > 0.05$ across all channels).

## Execution & Verification
To regenerate Version 1:
```bash
python -m pipelines.synthetic_video.generator
pytest tests/test_synthetic_video.py -v
```

To regenerate Version 2:
```bash
python -m pipelines.synthetic_video.generator_v2
pytest tests/test_synthetic_video_v2.py -v
```

To run comparative audit between V1 and V2:
```bash
python scripts/compare_v1_v2.py
```
