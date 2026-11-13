# Multimodal Late Fusion Engine

## Overview
This module combines predictions from the four independent pipelines:
1. Clinical Numerical Pipeline (Real clinical survey records)
2. Synthetic Audio Feature Pipeline (Acoustic parameters)
3. Synthetic Text Pipeline (Clinical intake notes)
4. Synthetic Video Feature Pipeline (Facial AU dynamics)

## Responsibilities
- Validates cross-modality participant alignment (`BGD_xxx`).
- Enforces multi-provenance hybrid tracking (`REAL` vs. `CLINICALLY_CONDITIONED_SYNTHETIC`).
- Implements decision-level fusion strategies (constrained weighted average, meta-classification, conformal prediction sets).
- Evaluates missing-modality scenarios and provides composite screening risk scores.
