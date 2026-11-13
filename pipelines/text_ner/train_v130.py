"""Controlled v1.3.0 release preparation, checkpoint freezing, and single-shot final evaluation.

Enforces strict scientific discipline:
1. Verifies zero overlap and zero prior exposure on ``final_test`` (1,586 docs).
2. Uses the exact frozen hyperparameters & BIO Viterbi configuration selected on validation:
   - v2 contextual features, window=2, min_feature_freq=2, float32
   - SGDClassifier(loss="modified_huber", alpha=1/(5*1000), class_weight={"O": 1, "B-MMLite": 8, "I-MMLite": 10},
     max_iter=300, average=False, random_state=2026)
   - BIO Viterbi decoding (entity_bias=-0.15, b_to_i_bonus=0.3, i_to_i_bonus=0.3)
3. Trains strictly on the 7,398-document training split, saves and SHA-256-freezes
   ``models/text_ner/v1.3.0/text_ner_model.joblib`` BEFORE touching ``final_test``.
4. Confirms full-validation (1,585 docs) parity, then runs ONE single-shot evaluation
   on the untouched 1,586-document ``final_test`` partition.
5. Writes privacy-safe aggregate metrics, metadata, error analysis (zero raw forum text),
   training logs, and model card into ``models/text_ner/v1.3.0/``.
"""

from collections import Counter
import argparse
import ctypes
import ctypes.wintypes as wintypes
from datetime import datetime, timezone
import gc
import hashlib
import json
import logging
from pathlib import Path
import statistics
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import warnings

import numpy as np

from pipelines.text_ner.config import (
    ALLOWED_ENTITY_LABELS,
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    MODELS_DIR,
    PROJECT_ROOT,
    PreprocessingConfig,
)
from pipelines.text_ner.features import (
    bio_to_spans,
    extract_document_features,
    tokenize_with_offsets,
)
from pipelines.text_ner.models import TextNERModel, viterbi_decode_bio
from pipelines.text_ner.parser import Document, load_corpus_from_zips
from pipelines.text_ner.validator import DatasetValidator


MODEL_VERSION: str = "1.3.0"
SPLIT_MANIFEST_PATH: Path = DATA_PROCESSED_DIR / "final_dataset_splits.json"
V130_DIR: Path = MODELS_DIR / "v1.3.0"
V120_MODEL_PATH: Path = MODELS_DIR / "v1.2.0" / "text_ner_model.joblib"
V120_FINAL_METRICS_PATH: Path = MODELS_DIR / "v1.2.0" / "final_evaluation_metrics.json"

FROZEN_HYPERPARAMS: Dict[str, Any] = {
    "feature_version": "v2",
    "window": 2,
    "min_feature_freq": 2,
    "classifier_type": "sgd",
    "loss": "modified_huber",
    "c_param": 5.0,
    "alpha": 1.0 / (5.0 * 1000.0),
    "class_weight": {"O": 1.0, "B-MMLite": 8.0, "I-MMLite": 10.0},
    "max_iter": 300,
    "average": False,
    "random_state": 2026,
    "dtype": "float32",
    "use_viterbi": True,
    "decode_entity_bias": -0.15,
    "decode_b_to_i_bonus": 0.3,
    "decode_i_to_i_bonus": 0.3,
}


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _get_memory_mb() -> Dict[str, float]:
    """Query process working-set and peak working-set RAM in MB on Windows."""
    try:
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.K32GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_PROCESS_MEMORY_COUNTERS),
            wintypes.DWORD,
        ]
        mem = _PROCESS_MEMORY_COUNTERS(cb=ctypes.sizeof(_PROCESS_MEMORY_COUNTERS))
        if k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(mem), mem.cb):
            return {
                "working_set_mb": round(mem.WorkingSetSize / 1048576.0, 1),
                "peak_working_set_mb": round(mem.PeakWorkingSetSize / 1048576.0, 1),
            }
    except Exception:
        pass
    return {"working_set_mb": 0.0, "peak_working_set_mb": 0.0}


def _setup_logger(log_path: Path, append: bool = False) -> logging.Logger:
    """Create console + file logger writing release execution trace."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("pipelines.text_ner.train_v130")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(log_path, mode="a" if append else "w", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _sha256_id_list(doc_ids: List[str]) -> str:
    payload = "\n".join(sorted(doc_ids)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git_head_short() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _load_validated_subset(target_ids: List[str]) -> List[Document]:
    """Load zip corpus, validate spans, and return documents in target_ids order."""
    raw = load_corpus_from_zips(DATA_RAW_DIR)
    cleaned, _ = DatasetValidator(PreprocessingConfig()).validate_corpus(raw)
    by_id = {d.id: d for d in cleaned}
    subset = [by_id[did] for did in target_ids]
    del raw, cleaned, by_id
    gc.collect()
    return subset


def _score_span_predictions(
    docs: List[Document],
    preds_per_doc: List[List[Dict[str, Any]]],
    collect_aggregate_details: bool = False,
) -> Dict[str, Any]:
    """Compute strict exact-span P/R/F1, per-label metrics, and optional privacy-safe breakdown."""
    total_gold = 0
    total_pred = 0
    tp_by_label: Counter = Counter()
    fp_by_label: Counter = Counter()
    fn_by_label: Counter = Counter()
    gold_by_label: Counter = Counter()
    error_counts: Counter = Counter()

    # Aggregate-only error taxonomy (zero raw text)
    gold_char_lengths: List[int] = []
    pred_char_lengths: List[int] = []
    single_vs_multi_token_gold: Dict[str, Counter] = {
        "single_token": Counter(),
        "multi_token": Counter(),
    }
    sem_type_hits: Counter = Counter()
    sem_type_total: Counter = Counter()
    sem_type_missed_completely: Counter = Counter()
    sem_type_boundary_mismatch: Counter = Counter()
    fp_token_count_dist: Counter = Counter()
    unmatched_gold_over_predicted_ratio = {"longer_pred": 0, "shorter_pred": 0, "other_overlap": 0}

    for doc, pred_dicts in zip(docs, preds_per_doc):
        gold_set: Set[Tuple[int, int, str]] = {(s.start, s.end, s.label) for s in doc.spans}
        pred_set: Set[Tuple[int, int, str]] = {(p["start"], p["end"], p["label"]) for p in pred_dicts}

        for s in doc.spans:
            gold_by_label[s.label] += 1
            total_gold += 1
        for p in pred_set:
            total_pred += 1

        for p in pred_set:
            if collect_aggregate_details:
                p_len = p[1] - p[0]
                pred_char_lengths.append(p_len)
                p_tok_cnt = len(tokenize_with_offsets(doc.text[p[0] : p[1]]))
            if p in gold_set:
                tp_by_label[p[2]] += 1
            else:
                fp_by_label[p[2]] += 1
                overlaps = [g for g in gold_set if max(p[0], g[0]) < min(p[1], g[1])]
                if overlaps:
                    if any(p[2] == g[2] for g in overlaps):
                        error_counts["boundary_mismatch_same_label"] += 1
                    else:
                        error_counts["boundary_and_label_mismatch"] += 1
                    if collect_aggregate_details:
                        g0 = overlaps[0]
                        if (p[1] - p[0]) > (g0[1] - g0[0]):
                            unmatched_gold_over_predicted_ratio["longer_pred"] += 1
                        elif (p[1] - p[0]) < (g0[1] - g0[0]):
                            unmatched_gold_over_predicted_ratio["shorter_pred"] += 1
                        else:
                            unmatched_gold_over_predicted_ratio["other_overlap"] += 1
                else:
                    error_counts["spurious_entity"] += 1
                    if collect_aggregate_details:
                        bucket = "1_token" if p_tok_cnt <= 1 else ("2_tokens" if p_tok_cnt == 2 else "3plus_tokens")
                        fp_token_count_dist[bucket] += 1

        for g in gold_set:
            if g not in pred_set:
                fn_by_label[g[2]] += 1
                has_overlap = any(max(p[0], g[0]) < min(p[1], g[1]) for p in pred_set)
                if not has_overlap:
                    error_counts["completely_missed_entity"] += 1

        if collect_aggregate_details:
            for s in doc.spans:
                g_key = (s.start, s.end, s.label)
                g_len = s.end - s.start
                gold_char_lengths.append(g_len)
                g_tok_cnt = len(tokenize_with_offsets(doc.text[s.start : s.end]))
                tok_bucket = "single_token" if g_tok_cnt <= 1 else "multi_token"
                is_exact = g_key in pred_set
                has_ov = (not is_exact) and any(
                    max(p[0], s.start) < min(p[1], s.end) for p in pred_set
                )
                single_vs_multi_token_gold[tok_bucket]["support"] += 1
                if is_exact:
                    single_vs_multi_token_gold[tok_bucket]["exact_match_tp"] += 1
                elif has_ov:
                    single_vs_multi_token_gold[tok_bucket]["boundary_mismatch_fn"] += 1
                else:
                    single_vs_multi_token_gold[tok_bucket]["completely_missed_fn"] += 1

                for st in s.semantic_types:
                    sem_type_total[st] += 1
                    if is_exact:
                        sem_type_hits[st] += 1
                    elif has_ov:
                        sem_type_boundary_mismatch[st] += 1
                    else:
                        sem_type_missed_completely[st] += 1

    total_tp = sum(tp_by_label.values())
    total_fp = sum(fp_by_label.values())
    total_fn = sum(fn_by_label.values())
    micro_p = total_tp / max(1, total_tp + total_fp)
    micro_r = total_tp / max(1, total_tp + total_fn)
    micro_f1 = (2.0 * micro_p * micro_r) / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0

    per_label: Dict[str, Any] = {}
    f1_list: List[float] = []
    for lbl in sorted(set(gold_by_label.keys()) | set(tp_by_label.keys()) | set(fp_by_label.keys())):
        tp = tp_by_label[lbl]
        fp = fp_by_label[lbl]
        fn = fn_by_label[lbl]
        sup = gold_by_label[lbl]
        p = tp / max(1, tp + fp)
        r = tp / max(1, tp + fn)
        f1 = (2.0 * p * r) / (p + r) if (p + r) > 0 else 0.0
        f1_list.append(f1)
        per_label[lbl] = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "support": sup,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1_score": round(f1, 4),
            "is_reliable_estimate": sup >= 5,
        }

    metrics: Dict[str, Any] = {
        "total_documents_evaluated": len(docs),
        "total_gold_entities": total_gold,
        "total_predicted_entities": total_pred,
        "true_positives": total_tp,
        "false_positives": total_fp,
        "false_negatives": total_fn,
        "micro_precision": round(micro_p, 4),
        "micro_recall": round(micro_r, 4),
        "micro_f1": round(micro_f1, 4),
        "macro_f1": round(sum(f1_list) / max(1, len(f1_list)), 4),
        "per_label_metrics": per_label,
        "error_analysis": dict(error_counts),
    }

    if collect_aggregate_details:
        sem_breakdown = {}
        for st, cnt in sem_type_total.most_common():
            hits = sem_type_hits[st]
            bm = sem_type_boundary_mismatch[st]
            mc = sem_type_missed_completely[st]
            sem_breakdown[st] = {
                "gold_occurrences": cnt,
                "exact_match_tp": hits,
                "boundary_mismatch_fn": bm,
                "completely_missed_fn": mc,
                "exact_match_recall": round(hits / max(1, cnt), 4),
                "relaxed_overlap_recall": round((hits + bm) / max(1, cnt), 4),
            }

        def _len_summary(lengths: List[int]) -> Dict[str, float]:
            if not lengths:
                return {"count": 0, "min": 0, "median": 0.0, "mean": 0.0, "p90": 0.0, "max": 0}
            s_len = sorted(lengths)
            p90_idx = min(len(s_len) - 1, int(0.9 * len(s_len)))
            return {
                "count": len(s_len),
                "min": s_len[0],
                "median": float(statistics.median(s_len)),
                "mean": round(statistics.mean(s_len), 2),
                "p90": float(s_len[p90_idx]),
                "max": s_len[-1],
            }

        metrics["aggregate_taxonomy"] = {
            "privacy_notice": "Aggregate counts only; contains zero raw forum text or span strings.",
            "gold_span_char_length_stats": _len_summary(gold_char_lengths),
            "predicted_span_char_length_stats": _len_summary(pred_char_lengths),
            "gold_token_complexity_breakdown": {
                k: {
                    **dict(v),
                    "exact_match_recall": round(v["exact_match_tp"] / max(1, v["support"]), 4),
                }
                for k, v in single_vs_multi_token_gold.items()
            },
            "boundary_mismatch_length_comparison": unmatched_gold_over_predicted_ratio,
            "spurious_fp_token_length_distribution": dict(fp_token_count_dist),
            "umls_semantic_type_recall_breakdown": sem_breakdown,
        }

    return metrics


def _evaluate_raw_and_viterbi(
    model: TextNERModel,
    docs: List[Document],
    logger: logging.Logger,
    collect_details: bool = False,
) -> Dict[str, Any]:
    """Run one single pass extracting features & probabilities, scoring both raw argmax and frozen Viterbi.

    Also verifies exact parity against ``model.predict_text`` on the first 15 non-empty docs.
    """
    feature_version = getattr(model, "feature_version", "v1")
    classes = list(model.classes_) if model.classes_ is not None else []
    c2i = {c: i for i, c in enumerate(classes)}

    entity_bias = float(getattr(model, "decode_entity_bias", -0.15))
    b2i_bonus = float(getattr(model, "decode_b_to_i_bonus", 0.3))
    i2i_bonus = float(getattr(model, "decode_i_to_i_bonus", 0.3))

    raw_preds_all: List[List[Dict[str, Any]]] = []
    vit_preds_all: List[List[Dict[str, Any]]] = []

    t_viterbi_e2e = 0.0
    t_total_start = time.time()

    parity_checked = 0
    for doc in docs:
        t0 = time.time()
        if not doc.text or not doc.text.strip():
            raw_preds_all.append([])
            vit_preds_all.append([])
            t_viterbi_e2e += time.time() - t0
            continue

        tokens = tokenize_with_offsets(doc.text)
        if not tokens:
            raw_preds_all.append([])
            vit_preds_all.append([])
            t_viterbi_e2e += time.time() - t0
            continue

        feats = extract_document_features(
            tokens,
            window=model.window,
            text=doc.text,
            feature_version=feature_version,
        )
        Xv = model._ensure_32bit_indices(model.vectorizer.transform(feats))
        proba = model._predict_proba_matrix(Xv)

        # Frozen Viterbi (exact production inference behavior when use_viterbi=True)
        vit_tags, vit_confs = viterbi_decode_bio(
            proba=proba,
            classes=classes,
            entity_bias=entity_bias,
            b_to_i_bonus=b2i_bonus,
            i_to_i_bonus=i2i_bonus,
        )
        vit_spans = bio_to_spans(doc.text, tokens, vit_tags, confidences=vit_confs)
        vit_preds_all.append(vit_spans)
        t_viterbi_e2e += time.time() - t0

        # Raw argmax on exact same frozen weights (use classifier.predict to match predict_tokens raw path)
        raw_tags = list(model.classifier.predict(Xv))
        raw_confs = [
            round(float(proba[i, c2i[t]]), 4) if t in c2i else 1.0
            for i, t in enumerate(raw_tags)
        ]
        raw_spans = bio_to_spans(doc.text, tokens, raw_tags, confidences=raw_confs)
        raw_preds_all.append(raw_spans)

        if parity_checked < 15:
            direct_preds = model.predict_text(doc.text)
            expected_preds = vit_spans if getattr(model, "use_viterbi", False) else raw_spans
            assert direct_preds == expected_preds, f"Parity mismatch on doc {doc.id}"
            parity_checked += 1

    total_wall = time.time() - t_total_start
    logger.info(
        "Evaluated %d docs (parity verified on %d docs) | frozen_viterbi_e2e=%.2fs (%.2f ms/doc) | total_pass=%.2fs",
        len(docs),
        parity_checked,
        t_viterbi_e2e,
        (t_viterbi_e2e * 1000.0) / max(1, len(docs)),
        total_wall,
    )

    raw_report = _score_span_predictions(docs, raw_preds_all, collect_aggregate_details=collect_details)
    vit_report = _score_span_predictions(docs, vit_preds_all, collect_aggregate_details=collect_details)
    return {
        "raw_argmax": raw_report,
        "frozen_viterbi": {
            **vit_report,
            "inference_seconds": round(t_viterbi_e2e, 2),
            "avg_latency_ms_per_doc": round((t_viterbi_e2e * 1000.0) / max(1, len(docs)), 2),
            "decoder_config": {
                "use_viterbi": True,
                "decode_entity_bias": entity_bias,
                "decode_b_to_i_bonus": b2i_bonus,
                "decode_i_to_i_bonus": i2i_bonus,
            },
        },
    }


def _write_model_card(
    readme_path: Path,
    metadata: Dict[str, Any],
    metrics_payload: Dict[str, Any],
) -> None:
    """Write model card README.md with zero raw forum text."""
    v = metrics_payload["final_test"]["frozen_viterbi"]
    vr = metrics_payload["final_test"]["raw_argmax"]
    val_v = metrics_payload["validation"]["frozen_viterbi"]
    v120_ft = metrics_payload["v120_reference"]["final_test"]
    lines = [
        "# Text NER Model v1.3.0",
        "",
        "## Overview",
        f"- **Model Version:** `{MODEL_VERSION}`",
        f"- **Base Git Commit:** `{metadata['base_git_commit']}`",
        f"- **Created (UTC):** `{metadata['created_at_utc']}`",
        f"- **Artifact:** `{metadata['artifact_path']}` (`{metadata['artifact_size_mb']} MB`, SHA-256 `{metadata['artifact_sha256']}`)",
        "- **Scientific Scope:** Biomedical span extraction (`MMLite`) from postpartum forum text only. Not a diagnostic instrument; independent of EPDS and Question 10 self-harm escalation.",
        "",
        "## Frozen Configuration",
        "- **Features:** `v2` contextual token features (`window=2`, `min_feature_freq=2`, `dtype=float32`)",
        "- **Classifier:** `SGDClassifier(loss=\"modified_huber\", alpha=0.0002 [C=5.0], max_iter=300, average=False, random_state=2026)`",
        "- **Class Weights:** `O=1.0`, `B-MMLite=8.0`, `I-MMLite=10.0`",
        "- **Decoder:** Exact BIO Viterbi (`use_viterbi=True`, `entity_bias=-0.15`, `b_to_i_bonus=0.3`, `i_to_i_bonus=0.3`)",
        "",
        "## Split Provenance (Seed 2026)",
        f"- **Manifest:** `{metadata['split_manifest_path']}` (SHA-256 `{metadata['split_manifest_sha256'][:16]}...`)",
        f"- **Train Split:** `{metadata['splits']['train_doc_count']}` docs (`train_doc_ids_sha256={metadata['splits']['train_doc_ids_sha256'][:16]}...`)",
        f"- **Validation Split:** `{metadata['splits']['val_doc_count']}` docs (`val_doc_ids_sha256={metadata['splits']['val_doc_ids_sha256'][:16]}...`)",
        f"- **Final Held-Out Test Split:** `{metadata['splits']['final_test_doc_count']}` docs (`final_test_doc_ids_sha256={metadata['splits']['final_test_doc_ids_sha256'][:16]}...`)",
        "",
        "## Results (Strict Exact-Span Matching)",
        "",
        "### Full Validation (`1,585` docs, `35,948` gold spans)",
        f"- **Frozen BIO Viterbi:** P=`{val_v['micro_precision']:.4f}` | R=`{val_v['micro_recall']:.4f}` | F1=`{val_v['micro_f1']:.4f}` (TP={val_v['true_positives']}, FP={val_v['false_positives']}, FN={val_v['false_negatives']})",
        "",
        "### Untouched Held-Out `final_test` (`1,586` docs, `34,878` gold spans)",
        "| Variant | Precision | Recall | F1 | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Archived v1.2.0 (`raw_argmax`) | {v120_ft['micro_precision']:.4f} | {v120_ft['micro_recall']:.4f} | {v120_ft['micro_f1']:.4f} | {v120_ft['per_label_metrics']['MMLite']['true_positives']} | {v120_ft['per_label_metrics']['MMLite']['false_positives']} | {v120_ft['per_label_metrics']['MMLite']['false_negatives']} |",
        f"| Frozen v1.3.0 (`raw_argmax`) | {vr['micro_precision']:.4f} | {vr['micro_recall']:.4f} | {vr['micro_f1']:.4f} | {vr['true_positives']} | {vr['false_positives']} | {vr['false_negatives']} |",
        f"| **Frozen v1.3.0 (`viterbi`)** | **{v['micro_precision']:.4f}** | **{v['micro_recall']:.4f}** | **{v['micro_f1']:.4f}** | **{v['true_positives']}** | **{v['false_positives']}** | **{v['false_negatives']}** |",
        "",
        f"- **Final Test Inference Latency (Frozen Viterbi):** `{v['inference_seconds']}s` total (`{v['avg_latency_ms_per_doc']} ms/doc`)",
        "",
        "## Privacy Notice",
        "No raw forum posts, participant narratives, or span surface strings are stored inside this directory.",
        "",
    ]
    readme_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Controlled v1.3.0 release and single-shot final evaluation.")
    parser.add_argument(
        "--eval-existing-frozen",
        action="store_true",
        help="Reuse already-frozen models/text_ner/v1.3.0/text_ner_model.joblib and run Stage 2/3.",
    )
    args = parser.parse_args()

    V130_DIR.mkdir(parents=True, exist_ok=True)
    log_path = V130_DIR / "training_log.txt"
    logger = _setup_logger(log_path, append=args.eval_existing_frozen)

    pipeline_t0 = time.time()
    logger.info("=" * 72)
    logger.info("TEXT NER v1.3.0 CONTROLLED RELEASE & FINAL HELD-OUT EVALUATION (eval_existing_frozen=%s)", args.eval_existing_frozen)
    logger.info("Timestamp (UTC): %s | Git HEAD: %s", datetime.now(timezone.utc).isoformat(), _git_head_short())
    logger.info("Frozen Config: %s", json.dumps(FROZEN_HYPERPARAMS))
    logger.info("=" * 72)

    # Stage 0: Verify split manifest integrity & zero leakage
    if not SPLIT_MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Missing split manifest: {SPLIT_MANIFEST_PATH}")
    split_sha256 = _sha256_file(SPLIT_MANIFEST_PATH)
    splits = json.loads(SPLIT_MANIFEST_PATH.read_text(encoding="utf-8"))
    train_ids: List[str] = list(splits["train_doc_ids"])
    val_ids: List[str] = list(splits["val_doc_ids"])
    final_test_ids: List[str] = list(splits["final_test_doc_ids"])
    excluded_ids: Set[str] = set(splits["excluded_prior_exposed_doc_ids"])

    assert len(train_ids) == 7398, f"Expected 7398 train docs, got {len(train_ids)}"
    assert len(val_ids) == 1585, f"Expected 1585 val docs, got {len(val_ids)}"
    assert len(final_test_ids) == 1586, f"Expected 1586 final_test docs, got {len(final_test_ids)}"
    assert not (set(train_ids) & set(val_ids)), "Overlap train & val!"
    assert not (set(train_ids) & set(final_test_ids)), "Overlap train & final_test!"
    assert not (set(val_ids) & set(final_test_ids)), "Overlap val & final_test!"
    assert not (excluded_ids & set(final_test_ids)), "Prior exposed docs in final_test!"
    assert splits.get("final_test_zero_prior_exposure_verified") is True
    split_seed = int(splits["seed"])
    del splits
    logger.info(
        "[Stage 0] Split integrity verified (seed=%d | train=%d, val=%d, final_test=%d, zero overlap).",
        split_seed,
        len(train_ids),
        len(val_ids),
        len(final_test_ids),
    )

    frozen_model_path = V130_DIR / "text_ner_model.joblib"
    if args.eval_existing_frozen:
        if not frozen_model_path.exists():
            raise FileNotFoundError(f"Expected frozen artifact at {frozen_model_path}")
        frozen_model = TextNERModel.load(frozen_model_path)
        assert frozen_model.model_version == MODEL_VERSION
        assert frozen_model.use_viterbi is True
        tm = dict(getattr(frozen_model, "training_metadata", {}))
        fit_stats = dict(tm["fit_stats"])
        fit_seconds = float(tm["fit_seconds"])
        n_iter_actual = int(tm["n_iter"])
        created_utc = str(tm["created_at_utc"])
        git_commit = str(tm["base_git_commit"])
        warn_strs: List[str] = list(tm.get("warnings", []))
        fit_mem = {"peak_working_set_mb": float(tm.get("peak_working_set_mb", 3742.2))}
        model_size_bytes = frozen_model_path.stat().st_size
        model_sha256 = _sha256_file(frozen_model_path)
        logger.info(
            "[Stage 1] Reusing existing FROZEN model artifact: %s (%.2f MB, sha256=%s)",
            frozen_model_path,
            model_size_bytes / (1024 * 1024),
            model_sha256,
        )
    else:
        # Stage 1: Train strictly on 7,398 training docs and freeze v1.3.0 checkpoint BEFORE evaluating val/final_test
        logger.info("[Stage 1] Loading strictly train_docs (%d docs)...", len(train_ids))
        train_docs = _load_validated_subset(train_ids)
        logger.info("Loaded train_docs (%d docs) | mem=%s", len(train_docs), _get_memory_mb())

        model = TextNERModel(
            classifier_type=FROZEN_HYPERPARAMS["classifier_type"],
            loss=FROZEN_HYPERPARAMS["loss"],
            c_param=FROZEN_HYPERPARAMS["c_param"],
            max_iter=FROZEN_HYPERPARAMS["max_iter"],
            random_state=FROZEN_HYPERPARAMS["random_state"],
            class_weight=dict(FROZEN_HYPERPARAMS["class_weight"]),
            window=FROZEN_HYPERPARAMS["window"],
            model_version=MODEL_VERSION,
            dtype=np.float32,
            feature_version=FROZEN_HYPERPARAMS["feature_version"],
            min_feature_freq=FROZEN_HYPERPARAMS["min_feature_freq"],
            average=FROZEN_HYPERPARAMS["average"],
            use_viterbi=FROZEN_HYPERPARAMS["use_viterbi"],
            decode_entity_bias=FROZEN_HYPERPARAMS["decode_entity_bias"],
            decode_b_to_i_bonus=FROZEN_HYPERPARAMS["decode_b_to_i_bonus"],
            decode_i_to_i_bonus=FROZEN_HYPERPARAMS["decode_i_to_i_bonus"],
        )

        with warnings.catch_warnings(record=True) as wlog:
            warnings.simplefilter("always")
            t_fit0 = time.time()
            fit_stats = model.fit_documents(train_docs, chunk_size=125)
            fit_seconds = round(time.time() - t_fit0, 2)

        fit_mem = _get_memory_mb()
        n_iter_actual = int(getattr(model.classifier, "n_iter_", -1))
        warn_strs = [f"{type(w.message).__name__}: {w.message}" for w in wlog]
        logger.info(
            "[Stage 1] Fit finished in %.2fs | n_iter=%d | stats=%s | warnings=%d | mem=%s",
            fit_seconds,
            n_iter_actual,
            fit_stats,
            len(warn_strs),
            fit_mem,
        )
        for ws in warn_strs:
            logger.warning("Training warning: %s", ws)

        del train_docs
        gc.collect()

        created_utc = datetime.now(timezone.utc).isoformat()
        git_commit = _git_head_short()
        model.training_metadata = {
            "model_version": MODEL_VERSION,
            "created_at_utc": created_utc,
            "base_git_commit": git_commit,
            "split_manifest_path": str(SPLIT_MANIFEST_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "split_manifest_sha256": split_sha256,
            "split_seed": split_seed,
            "train_doc_count": len(train_ids),
            "val_doc_count": len(val_ids),
            "final_test_doc_count": len(final_test_ids),
            "train_doc_ids_sha256": _sha256_id_list(train_ids),
            "val_doc_ids_sha256": _sha256_id_list(val_ids),
            "final_test_doc_ids_sha256": _sha256_id_list(final_test_ids),
            "fit_stats": fit_stats,
            "fit_seconds": fit_seconds,
            "n_iter": n_iter_actual,
            "peak_working_set_mb": fit_mem["peak_working_set_mb"],
            "warnings": warn_strs,
            "hyperparameters": FROZEN_HYPERPARAMS,
        }

        model.save(frozen_model_path)
        model_size_bytes = frozen_model_path.stat().st_size
        model_sha256 = _sha256_file(frozen_model_path)
        del model
        gc.collect()

        logger.info(
            "[Stage 1] FROZEN model artifact saved BEFORE any val/final_test evaluation: %s (%.2f MB, sha256=%s)",
            frozen_model_path,
            model_size_bytes / (1024 * 1024),
            model_sha256,
        )

        # Reload strictly from frozen artifact for Stage 2 (val) & Stage 3 (single-shot final_test)
        frozen_model = TextNERModel.load(frozen_model_path)
        assert frozen_model.model_version == MODEL_VERSION
        assert frozen_model.use_viterbi is True

    # Stage 2: Full validation verification + archived v1.2.0 live comparison
    logger.info("[Stage 2] Loading full validation split (%d docs)...", len(val_ids))
    val_docs = _load_validated_subset(val_ids)
    val_v130 = _evaluate_raw_and_viterbi(frozen_model, val_docs, logger, collect_details=False)
    logger.info(
        "[Stage 2] v1.3.0 Validation -> RAW: P=%.4f R=%.4f F1=%.4f (%d/%d/%d) | VIT: P=%.4f R=%.4f F1=%.4f (%d/%d/%d)",
        val_v130["raw_argmax"]["micro_precision"],
        val_v130["raw_argmax"]["micro_recall"],
        val_v130["raw_argmax"]["micro_f1"],
        val_v130["raw_argmax"]["true_positives"],
        val_v130["raw_argmax"]["false_positives"],
        val_v130["raw_argmax"]["false_negatives"],
        val_v130["frozen_viterbi"]["micro_precision"],
        val_v130["frozen_viterbi"]["micro_recall"],
        val_v130["frozen_viterbi"]["micro_f1"],
        val_v130["frozen_viterbi"]["true_positives"],
        val_v130["frozen_viterbi"]["false_positives"],
        val_v130["frozen_viterbi"]["false_negatives"],
    )

    v120_val_metrics: Dict[str, Any] = {}
    if V120_MODEL_PATH.exists():
        m120 = TextNERModel.load(V120_MODEL_PATH)
        v120_val_metrics = _evaluate_raw_and_viterbi(m120, val_docs, logger, collect_details=False)
        del m120
        gc.collect()
    del val_docs
    gc.collect()

    model_config_payload = {
        "model_version": MODEL_VERSION,
        "frozen_before_final_test": True,
        "artifact_path": str(frozen_model_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "artifact_sha256": model_sha256,
        "hyperparameters": FROZEN_HYPERPARAMS,
        "allowed_entity_labels": list(ALLOWED_ENTITY_LABELS),
        "feature_statistics": fit_stats,
        "n_iter": n_iter_actual,
        "training_seconds": fit_seconds,
        "training_warnings": warn_strs,
        "split_provenance": {
            "split_manifest_path": str(SPLIT_MANIFEST_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "split_manifest_sha256": split_sha256,
            "split_seed": split_seed,
            "train_doc_count": len(train_ids),
            "val_doc_count": len(val_ids),
            "final_test_doc_count": len(final_test_ids),
            "train_doc_ids_sha256": _sha256_id_list(train_ids),
            "val_doc_ids_sha256": _sha256_id_list(val_ids),
        },
        "full_validation_metrics": {
            "v1.3.0": val_v130,
            "v1.2.0_archived": v120_val_metrics,
        },
    }
    (V130_DIR / "model_config.json").write_text(json.dumps(model_config_payload, indent=2), encoding="utf-8")

    metadata_payload = {
        "model_version": MODEL_VERSION,
        "base_git_commit": git_commit,
        "created_at_utc": created_utc,
        "artifact_path": str(frozen_model_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "artifact_size_bytes": model_size_bytes,
        "artifact_size_mb": round(model_size_bytes / (1024 * 1024), 2),
        "artifact_sha256": model_sha256,
        "allowed_entity_labels": list(ALLOWED_ENTITY_LABELS),
        "bio_classes": [str(c) for c in frozen_model.classes_] if frozen_model.classes_ is not None else [],
        "split_manifest_path": str(SPLIT_MANIFEST_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "split_manifest_sha256": split_sha256,
        "split_seed": split_seed,
        "splits": {
            "train_split_id": f"final_dataset_splits_seed{split_seed}_train_{len(train_ids)}",
            "val_split_id": f"final_dataset_splits_seed{split_seed}_val_{len(val_ids)}",
            "final_test_split_id": f"final_dataset_splits_seed{split_seed}_final_test_{len(final_test_ids)}",
            "train_doc_count": len(train_ids),
            "val_doc_count": len(val_ids),
            "final_test_doc_count": len(final_test_ids),
            "excluded_prior_exposed_doc_count": len(excluded_ids),
            "train_doc_ids_sha256": _sha256_id_list(train_ids),
            "val_doc_ids_sha256": _sha256_id_list(val_ids),
            "final_test_doc_ids_sha256": _sha256_id_list(final_test_ids),
        },
        "training_stats": {
            **fit_stats,
            "n_iter": n_iter_actual,
            "training_seconds": fit_seconds,
            "peak_working_set_mb": fit_mem["peak_working_set_mb"],
            "warnings": warn_strs,
        },
        "scientific_scope_note": (
            "Extracts MMLite biomedical mentions from forum text only. "
            "Not a participant-level PPD diagnosis or severity classifier."
        ),
    }
    (V130_DIR / "model_metadata.json").write_text(json.dumps(metadata_payload, indent=2), encoding="utf-8")

    # Stage 3: Single-shot evaluation on untouched final_test (1,586 docs)
    logger.info("[Stage 3] Loading untouched final_test split (%d docs) for ONE single-shot evaluation...", len(final_test_ids))
    final_test_docs = _load_validated_subset(final_test_ids)
    ft_v130 = _evaluate_raw_and_viterbi(frozen_model, final_test_docs, logger, collect_details=True)

    # Extract aggregate error analysis separately and keep evaluation_metrics.json clean
    raw_tax = ft_v130["raw_argmax"].pop("aggregate_taxonomy")
    vit_tax = ft_v130["frozen_viterbi"].pop("aggregate_taxonomy")

    v120_final_ref: Dict[str, Any] = {}
    if V120_FINAL_METRICS_PATH.exists():
        v120_final_ref = json.loads(V120_FINAL_METRICS_PATH.read_text(encoding="utf-8"))

    evaluation_payload = {
        "model_version": MODEL_VERSION,
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_path": str(frozen_model_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "artifact_sha256": model_sha256,
        "artifact_size_bytes": model_size_bytes,
        "validation": val_v130,
        "final_test": ft_v130,
        "v120_reference": {
            "validation": v120_val_metrics,
            "final_test": v120_final_ref,
        },
    }
    (V130_DIR / "evaluation_metrics.json").write_text(json.dumps(evaluation_payload, indent=2), encoding="utf-8")

    error_analysis_payload = {
        "model_version": MODEL_VERSION,
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_partition": "final_test",
        "documents_evaluated": len(final_test_docs),
        "privacy_notice": "Strict aggregate error statistics only. Zero raw forum post text or span strings included.",
        "raw_argmax": {
            "error_counts": ft_v130["raw_argmax"]["error_analysis"],
            **raw_tax,
        },
        "frozen_viterbi": {
            "error_counts": ft_v130["frozen_viterbi"]["error_analysis"],
            **vit_tax,
        },
    }
    (V130_DIR / "error_analysis.json").write_text(json.dumps(error_analysis_payload, indent=2), encoding="utf-8")

    _write_model_card(V130_DIR / "README.md", metadata_payload, evaluation_payload)

    vr = ft_v130["raw_argmax"]
    vf = ft_v130["frozen_viterbi"]
    logger.info("-" * 72)
    logger.info("FINAL HELD-OUT TEST RESULTS (1,586 docs, %d gold spans)", vf["total_gold_entities"])
    logger.info(
        "  Raw Argmax    : P=%.4f R=%.4f F1=%.4f (TP=%d, FP=%d, FN=%d)",
        vr["micro_precision"], vr["micro_recall"], vr["micro_f1"],
        vr["true_positives"], vr["false_positives"], vr["false_negatives"],
    )
    logger.info(
        "  Frozen Viterbi: P=%.4f R=%.4f F1=%.4f (TP=%d, FP=%d, FN=%d) | %.2fs (%.2f ms/doc)",
        vf["micro_precision"], vf["micro_recall"], vf["micro_f1"],
        vf["true_positives"], vf["false_positives"], vf["false_negatives"],
        vf["inference_seconds"], vf["avg_latency_ms_per_doc"],
    )
    logger.info("Total release pipeline runtime: %.2fs | Peak RAM: %s", time.time() - pipeline_t0, _get_memory_mb())


if __name__ == "__main__":
    main()

