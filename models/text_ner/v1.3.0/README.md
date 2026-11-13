# Text NER Model v1.3.0

## Overview
- **Model Version:** `1.3.0`
- **Base Git Commit:** `24c291b`
- **Created (UTC):** `2026-11-12T10:51:42.561044+00:00`
- **Artifact:** `models/text_ner/v1.3.0/text_ner_model.joblib` (`89.66 MB`, SHA-256 `9797a6058b8c5500cc989d917184a61a266c12d0335d82db9bc5f3128633d5ef`)
- **Scientific Scope:** Biomedical span extraction (`MMLite`) from postpartum forum text only. Not a diagnostic instrument; independent of EPDS and Question 10 self-harm escalation.

## Artifact Download
- **Release Asset URL:** `https://github.com/navamishetty72/postpartum-depression-screening/releases/download/v1.3.0/text_ner_model.joblib`
- **Automated Download Script:** Run `python scripts/download_text_ner_artifact.py` from repository root.
- **SHA-256 Checksum:** `9797a6058b8c5500cc989d917184a61a266c12d0335d82db9bc5f3128633d5ef`
- **File Size:** `94,014,515 bytes` (~89.66 MB)

## Frozen Configuration
- **Features:** `v2` contextual token features (`window=2`, `min_feature_freq=2`, `dtype=float32`)
- **Classifier:** `SGDClassifier(loss="modified_huber", alpha=0.0002 [C=5.0], max_iter=300, average=False, random_state=2026)`
- **Class Weights:** `O=1.0`, `B-MMLite=8.0`, `I-MMLite=10.0`
- **Decoder:** Exact BIO Viterbi (`use_viterbi=True`, `entity_bias=-0.15`, `b_to_i_bonus=0.3`, `i_to_i_bonus=0.3`)

## Split Provenance (Seed 2026)
- **Manifest:** `data/processed/text_ner/final_dataset_splits.json` (SHA-256 `d34767eac4583aa6...`)
- **Train Split:** `7398` docs (`train_doc_ids_sha256=ee7fc32b98894460...`)
- **Validation Split:** `1585` docs (`val_doc_ids_sha256=eb6a7c6a3e247301...`)
- **Final Held-Out Test Split:** `1586` docs (`final_test_doc_ids_sha256=3bd7d6f4157360fd...`)

## Results (Strict Exact-Span Matching)

### Full Validation (`1,585` docs, `35,948` gold spans)
- **Frozen BIO Viterbi:** P=`0.6524` | R=`0.8923` | F1=`0.7537` (TP=32078, FP=17094, FN=3870)

### Untouched Held-Out `final_test` (`1,586` docs, `34,878` gold spans)
| Variant | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| Archived v1.2.0 (`raw_argmax`) | 0.5932 | 0.8949 | 0.7134 | 31213 | 21408 | 3665 |
| Frozen v1.3.0 (`raw_argmax`) | 0.6369 | 0.9015 | 0.7464 | 31443 | 17929 | 3435 |
| **Frozen v1.3.0 (`viterbi`)** | **0.6513** | **0.8867** | **0.7510** | **30927** | **16555** | **3951** |

- **Final Test Inference Latency (Frozen Viterbi):** `191.96s` total (`121.03 ms/doc`)

## Privacy Notice
No raw forum posts, participant narratives, or span surface strings are stored inside this directory.
