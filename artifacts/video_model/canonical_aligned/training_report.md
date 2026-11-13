# Canonical-Aligned BiLSTM Video Model Training & Evaluation Report

> [!IMPORTANT]
> **SCIENTIFIC INTEGRITY NOTICE**:
> Synthetic Video V2 features are abstract numerical simulations generated as engineering fixtures
> for multimodal architecture verification. They do NOT represent authentic maternal facial recordings
> or clinically validated psychiatric biomarkers. Clinical target labels (EPDS >= 13) are strictly independent.
> Supervised video-only classification serves as an empirical negative-control experiment.

## 1. Executive Summary & Split Manifest Alignment

This training run resolves the historical Phase 4B split mismatch by strictly adhering to the canonical
split manifest (`data\processed\Numerical\train_test_split_manifest.csv`).

- **Authoritative Split Manifest**: `data/processed/Numerical/train_test_split_manifest.csv`
- **Target Column**: `target_canonical_epds_ge_13` (Positive Class: 1 = EPDS >= 13, Negative Class: 0 = EPDS < 13)
- **Training Cohort**: Exactly 640 canonical training participants (281 positive, 359 negative; prevalence = 43.91%).
- **Holdout Cohort**: Exactly 160 canonical holdout participants (70 positive, 90 negative; prevalence = 43.75%).
- **Train/Test Disjointness**: Confirmed 0 participant overlap.
- **Random Seed**: 42
- **Artifacts Directory**: `artifacts\video_model\canonical_aligned` (completely isolated from historical artifacts).

## 2. Model Architecture & Hyperparameters

- **Model Class**: `VideoBiLSTMModel` (`pipelines.video_model.models.bilstm_model.py`)
- **Input Dimension**: 24 continuous temporal channels
- **Hidden Dimension**: 64 per direction (128-dimensional bidirectional concatenated representation)
- **Temporal Pooling**: Masked Mean Pooling (`MaskedTemporalPooling(method='mean')`) respecting tracking confidence mask and padding mask
- **Participant Embedding Dimension**: 128 (projected via LayerNorm + ReLU)
- **Prediction Head**: Linear(128 -> 1) with logit output
- **Optimizer**: AdamW (learning_rate=0.001, weight_decay=0.0001, grad_clip=1.0)
- **Batch Size**: 32
- **Loss Function**: `BCEWithLogitsLoss` with positive class weighting dynamically computed per fold
- **Early Stopping**: Patience = 7 epochs on validation loss (maximum 30 epochs)

## 3. 5-Fold Stratified Cross-Validation Results

Normalization statistics (mean and scale) were fitted exclusively inside each fold on its training subset.
Validation subsets were never exposed during preprocessing or model fitting.

### Fold-by-Fold Performance Breakdown

| Fold | Train N | Val N | Best Epoch | Final Val Loss | ROC-AUC | PR-AUC | Balanced Acc. | F1-Score | Precision | Recall |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 512 | 128 | 1 | 0.7941 | 0.4707 | 0.4383 | 0.5500 | 0.5323 | 0.4925 | 0.5789 |
| 1 | 512 | 128 | 2 | 0.8151 | 0.4209 | 0.4000 | 0.4583 | 0.4930 | 0.4070 | 0.6250 |
| 2 | 512 | 128 | 1 | 0.7922 | 0.4630 | 0.4476 | 0.4891 | 0.3762 | 0.4222 | 0.3393 |
| 3 | 512 | 128 | 1 | 0.7943 | 0.4457 | 0.4268 | 0.4960 | 0.5405 | 0.4348 | 0.7143 |
| 4 | 512 | 128 | 1 | 0.7865 | 0.4839 | 0.4150 | 0.4921 | 0.4844 | 0.4306 | 0.5536 |

### Out-of-Fold (OOF) Aggregate Performance (N = 640)

| Metric | Mean ± Std Across Folds | Pooled OOF Metric |
| :--- | :---: | :---: |
| **ROC-AUC** | 0.4568 ± 0.0218 | **0.4604** |
| **PR-AUC** | 0.4255 ± 0.0168 | **0.4102** |
| **Balanced Accuracy** | 0.4971 ± 0.0297 | **0.4970** |
| **F1-Score** | 0.4853 ± 0.0587 | **0.4914** |
| **Precision** | 0.4374 ± 0.0292 | **0.4365** |
| **Recall** | 0.5622 ± 0.1242 | **0.5623** |

- **Optimal Epoch Count Derived**: 1 epochs (mean best epoch across folds rounded to nearest integer).

## 4. Final Model Training & Canonical Holdout Evaluation (N = 160)

The final BiLSTM model was trained on all 640 canonical training participants for exactly 1 epochs.
The trained model was evaluated strictly once on the frozen 160 holdout test participants.
Non-parametric bootstrap (1,000 resamples, seed 42) was used to construct 95% confidence intervals.

| Metric | Holdout Value | 95% Bootstrap Confidence Interval |
| :--- | :---: | :---: |
| **ROC-AUC** | **0.5129** | [0.4147, 0.6045] |
| **PR-AUC** | **0.4456** | [0.3886, 0.5471] |
| **Balanced Accuracy** | **0.5056** | [0.4595, 0.5540] |
| **F1-Score** | **0.1647** | [0.0714, 0.2729] |
| **Precision** | **0.4667** | - |
| **Recall** | **0.1000** | - |

### Holdout Confusion Matrix

```
                Predicted Negative (0)    Predicted Positive (1)
Actual Neg (0):         82                        8                        
Actual Pos (1):         63                        7                        
```

## 5. Methodological Comparison: Canonical vs. Historical Phase 4B

| Property | Historical Phase 4B Artifacts | Canonical-Aligned Artifacts (This Run) | Alignment Status |
| :--- | :--- | :--- | :---: |
| **Split Manifest** | Historical legacy split | `data/processed/Numerical/train_test_split_manifest.csv` | **Aligned** |
| **Training N** | 640 (historical IDs) | 640 (canonical IDs) | **Aligned** |
| **Holdout N** | 160 (historical IDs) | 160 (canonical IDs) | **Aligned** |
| **ID Misallocations** | 127 participants transposed | 0 misallocations (100% matched) | **Resolved** |
| **Label Mismatches** | 330 labels inverted/mismatched | 0 mismatches (100% matched) | **Resolved** |
| **Holdout ROC-AUC** | 0.5097 [0.421, 0.598] | 0.5129 [0.4147, 0.6045] | **Verified** |
| **Checkpoints Path** | `artifacts/video_model/recurrent/` | `artifacts/video_model/canonical_aligned/` | **Preserved** |

## 6. Scientific Negative-Control Findings

1. **Near-Chance Classification**: The holdout ROC-AUC 95% confidence interval spans 0.50, confirming that abstract synthetic video features cannot distinguish clinical depression targets.
2. **Target Isolation Confirmed**: Because synthetic video feature sequences were simulated independently from real EPDS questionnaires, this chance-level performance proves the pipeline does not suffer from synthetic data contamination or artificial label leaking.
3. **Zero Data Leakage**: Preprocessing normalization was strictly fold-isolated. Holdout data remained completely untouched until final single-shot inference.
4. **Full Fusion Readiness**: The out-of-fold predictions (`oof_predictions_bilstm.csv`) and holdout predictions (`holdout_predictions_bilstm.csv`) now match the exact participant IDs, fold assignments, and ground truth labels of the Clinical, Audio, and Text classification modalities.

## 7. Artifact Manifest

All artifacts are saved under `artifacts\video_model\canonical_aligned/`:

- `bilstm_fold_0.pt` through `bilstm_fold_4.pt`: 5-fold cross-validation model checkpoints.
- `bilstm_final.pt`: Final model checkpoint trained on all 640 training participants.
- `oof_predictions_bilstm.csv`: Out-of-fold predictions for all 640 training participants.
- `holdout_predictions_bilstm.csv`: Final model predictions for all 160 holdout participants.
- `video_embeddings_bilstm.npz`: 128-dimensional participant embeddings for all 800 participants.
- `video_embeddings_bilstm.csv`: Tabular embeddings metadata dataframe.
- `metrics_summary.json`: Machine-readable performance metrics and configuration.
- `training_report.md`: This comprehensive verification report.

---
*Report automatically generated by `pipelines.video_model.train_canonical_aligned`.*