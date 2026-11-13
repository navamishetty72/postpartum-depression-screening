"""Reproducible leak-free model selection, checkpoint freezing, and complete final evaluation.

Constructs a fresh thread/document-isolated evaluation partition excluding all
documents previously used in training, validation tuning, or error analysis
(prior commit ``ec27965``), performs candidate selection strictly on permitted
training and validation partitions, freezes the selected model and all metadata
artifacts, and evaluates once on the complete fresh final test partition."""

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import gc
import hashlib
import json
import logging
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from pipelines.text_ner.config import (
    ALLOWED_ENTITY_LABELS,
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    MODELS_DIR,
    PROJECT_ROOT,
    RANDOM_SEED,
    PreprocessingConfig,
    SplitConfig,
)
from pipelines.text_ner.evaluate import (
    evaluate_documents_strict,
    save_evaluation_report,
)
from pipelines.text_ner.models import TextNERModel
from pipelines.text_ner.parser import Document, load_corpus_from_zips
from pipelines.text_ner.splitter import ThreadDatasetSplitter
from pipelines.text_ner.validator import DatasetValidator


FINAL_SPLIT_SEED: int = 2026
FINAL_MODEL_VERSION: str = "1.2.0"
DOCS_SUMMARY_PATH: Path = PROJECT_ROOT / "docs" / "text_ner_final_evaluation_summary.json"


def _setup_logger(log_path: Path) -> logging.Logger:
    """Configure console + file logger for final training and evaluation."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("pipelines.text_ner.final_eval")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def _get_git_commit_short() -> str:
    """Return current HEAD short commit hash when available."""
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


def _sha256_file(filepath: Path) -> str:
    """Compute SHA-256 hex digest of an artifact file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def collect_prior_exposed_ids(
    cleaned_corpus: List[Document],
    legacy_splits_path: Path = DATA_PROCESSED_DIR / "dataset_splits.json",
    legacy_seed: int = RANDOM_SEED,
    legacy_max_train: int = 1500,
    legacy_val_used: int = 150,
    legacy_test_used: int = 150,
) -> Dict[str, List[str]]:
    """Deterministically reconstruct exact document IDs exposed in prior development.

    Replays the seed=42 split logic and cross-checks against ``dataset_splits.json``
    when present on disk.
    """
    legacy_splitter = ThreadDatasetSplitter(SplitConfig(seed=legacy_seed))
    old_train, old_val, old_test, _ = legacy_splitter.split(cleaned_corpus)

    old_train_used = [d.id for d in old_train[:legacy_max_train]]
    old_val_used = [d.id for d in old_val[:legacy_val_used]]
    old_test_used = [d.id for d in old_test[:legacy_test_used]]

    if legacy_splits_path.exists():
        with open(legacy_splits_path, "r", encoding="utf-8") as f:
            legacy_manifest = json.load(f)
        saved_train = legacy_manifest.get("train", {}).get("document_ids", [])
        saved_val = legacy_manifest.get("val", {}).get("document_ids", [])
        saved_test = legacy_manifest.get("test", {}).get("document_ids", [])
        if saved_train and saved_train[:legacy_max_train] != old_train_used:
            raise RuntimeError("Legacy train IDs diverge from dataset_splits.json!")
        if saved_val and saved_val[:legacy_val_used] != old_val_used:
            raise RuntimeError("Legacy val IDs diverge from dataset_splits.json!")
        if saved_test and saved_test[:legacy_test_used] != old_test_used:
            raise RuntimeError("Legacy test IDs diverge from dataset_splits.json!")

    union_exposed = sorted(set(old_train_used) | set(old_val_used) | set(old_test_used))
    return {
        "old_train_used": old_train_used,
        "old_val_used": old_val_used,
        "old_test_evaluated_and_error_analyzed": old_test_used,
        "all_exposed_union": union_exposed,
    }


def summarize_semantic_types(cleaned_corpus: List[Document]) -> Dict[str, Any]:
    """Compute validated UMLS SemanticType support and multi-label ambiguity statistics."""
    type_counts: Counter = Counter()
    single_label_counts: Counter = Counter()
    multi_label_combos: Counter = Counter()
    types_per_span_hist: Counter = Counter()
    total_spans = 0
    spans_with_multiple = 0

    for doc in cleaned_corpus:
        for span in doc.spans:
            total_spans += 1
            unique_sem = sorted(set(span.semantic_types))
            types_per_span_hist[str(len(unique_sem))] += 1
            for st in unique_sem:
                type_counts[st] += 1
            if len(unique_sem) == 1:
                single_label_counts[unique_sem[0]] += 1
            elif len(unique_sem) > 1:
                spans_with_multiple += 1
                multi_label_combos["+".join(unique_sem)] += 1

    return {
        "total_validated_spans": total_spans,
        "distinct_semantic_types_observed": len(type_counts),
        "spans_with_single_semantic_type": total_spans - spans_with_multiple,
        "spans_with_multiple_semantic_types": spans_with_multiple,
        "multi_label_ambiguity_rate": round(spans_with_multiple / max(1, total_spans), 4),
        "types_per_span_histogram": dict(types_per_span_hist),
        "semantic_type_counts": dict(type_counts.most_common()),
        "single_label_only_counts": dict(single_label_counts.most_common()),
        "top_multi_label_combinations": dict(multi_label_combos.most_common(15)),
    }


def run_final_evaluation_pipeline(
    raw_data_dir: Path = DATA_RAW_DIR,
    output_model_path: Path = MODELS_DIR / "text_ner_model.joblib",
    config_path: Path = MODELS_DIR / "model_config.json",
    version_path: Path = MODELS_DIR / "model_version.json",
    log_path: Path = MODELS_DIR / "training_final.log",
    split_manifest_path: Path = DATA_PROCESSED_DIR / "final_dataset_splits.json",
    metrics_path: Path = DATA_PROCESSED_DIR / "final_evaluation_metrics.json",
    docs_summary_path: Path = DOCS_SUMMARY_PATH,
    final_seed: int = FINAL_SPLIT_SEED,
    val_eval_docs_limit: int = 400,
) -> Dict[str, Any]:
    """Execute leak-free splitting, validation selection, freezing, and final test eval."""
    pipeline_start = time.time()
    logger = _setup_logger(log_path)

    logger.info("=" * 72)
    logger.info("TEXT NER FINAL LEAK-FREE EVALUATION PIPELINE")
    logger.info("Timestamp (UTC): %s", datetime.now(timezone.utc).isoformat())
    logger.info("Final Split Seed: %d | Model Version: %s", final_seed, FINAL_MODEL_VERSION)
    logger.info("=" * 72)

    # 1. Ingest and validate corpus
    logger.info("[Step 1/5] Ingesting and validating raw corpus from %s...", raw_data_dir)
    corpus = load_corpus_from_zips(raw_data_dir)
    if not corpus:
        raise FileNotFoundError(f"No valid documents loaded from {raw_data_dir}")

    validator = DatasetValidator(PreprocessingConfig())
    cleaned_corpus, val_summary = validator.validate_corpus(corpus)
    logger.info(
        "Validated %d docs | Raw spans: %d | Retained valid non-overlapping spans: %d",
        len(cleaned_corpus),
        val_summary.total_raw_annotations,
        val_summary.final_retained_annotations,
    )
    semantic_summary = summarize_semantic_types(cleaned_corpus)

    # 2. Identify previously touched documents and build fresh leak-free final split
    logger.info("[Step 2/5] Reconstructing prior exposed doc IDs and creating clean split...")
    prior_exposed = collect_prior_exposed_ids(cleaned_corpus)
    splitter = ThreadDatasetSplitter(SplitConfig(seed=final_seed))
    train_docs, val_docs, final_test_docs, split_report = splitter.split_leak_free_final(
        cleaned_corpus,
        excluded_from_test_ids=prior_exposed["all_exposed_union"],
        exclude_from_val_ids=prior_exposed["old_test_evaluated_and_error_analyzed"],
        final_seed=final_seed,
        output_manifest_path=split_manifest_path,
    )
    logger.info(
        "Clean split created -> Train: %d docs (%d spans) | Val: %d docs (%d spans) | Final Test: %d docs (%d spans)",
        split_report.train.num_documents,
        split_report.train.num_annotations,
        split_report.val.num_documents,
        split_report.val.num_annotations,
        split_report.final_test.num_documents,
        split_report.final_test.num_annotations,
    )
    logger.info(
        "Isolation verified -> zero doc overlap=%s | zero URL overlap=%s | zero test prior exposure=%s | excluded_from_test=%d",
        split_report.overlap_verified_zero_doc_ids,
        split_report.overlap_verified_zero_thread_urls,
        split_report.final_test_zero_prior_exposure_verified,
        split_report.excluded_prior_exposed_count,
    )

    # 3. Validation-only model selection (NEVER touch final_test_docs here!)
    val_eval_slice = val_docs[:val_eval_docs_limit] if val_eval_docs_limit > 0 else val_docs
    logger.info(
        "[Step 3/5] Running validation-only model comparison on %d clean validation docs...",
        len(val_eval_slice),
    )

    candidates: List[Dict[str, Any]] = [
        {
            "name": "Enhanced_ModifiedHuber_C2.0_Train1500",
            "loss": "modified_huber",
            "c_param": 2.0,
            "max_train_docs": 1500,
        },
        {
            "name": "Enhanced_ModifiedHuber_C2.0_Train3500",
            "loss": "modified_huber",
            "c_param": 2.0,
            "max_train_docs": 3500,
        },
        {
            "name": "Enhanced_ModifiedHuber_C1.0_TrainAll",
            "loss": "modified_huber",
            "c_param": 1.0,
            "max_train_docs": len(train_docs),
        },
        {
            "name": "Enhanced_ModifiedHuber_C2.0_TrainAll",
            "loss": "modified_huber",
            "c_param": 2.0,
            "max_train_docs": len(train_docs),
        },
    ]

    selection_results: List[Dict[str, Any]] = []
    best_model: Optional[TextNERModel] = None
    best_candidate_info: Dict[str, Any] = {}
    best_val_f1 = -1.0

    for cand in candidates:
        cand_start = time.time()
        subset = train_docs[: cand["max_train_docs"]]
        model = TextNERModel(
            classifier_type="sgd",
            loss=cand["loss"],
            c_param=cand["c_param"],
            max_iter=500,
            random_state=final_seed,
            class_weight="balanced",
            window=2,
            model_version=FINAL_MODEL_VERSION,
            dtype=np.float32,
        )
        fit_stats = model.fit_documents(subset, chunk_size=250)
        fit_secs = time.time() - cand_start

        val_start = time.time()
        val_report = evaluate_documents_strict(model, val_eval_slice)
        val_secs = time.time() - val_start

        record = {
            "name": cand["name"],
            "loss": cand["loss"],
            "c_param": cand["c_param"],
            "train_docs_used": len(subset),
            "fit_stats": fit_stats,
            "fit_seconds": round(fit_secs, 2),
            "val_docs_evaluated": val_report.total_documents_evaluated,
            "val_gold_entities": val_report.total_gold_entities,
            "val_micro_precision": round(val_report.micro_precision, 4),
            "val_micro_recall": round(val_report.micro_recall, 4),
            "val_micro_f1": round(val_report.micro_f1, 4),
            "val_eval_seconds": round(val_secs, 2),
        }
        selection_results.append(record)
        logger.info(
            "  Candidate [%s] -> fit=%.1fs (%d tokens, %d feats) | Val P=%.4f R=%.4f F1=%.4f (eval=%.1fs)",
            cand["name"],
            fit_secs,
            fit_stats["total_tokens"],
            fit_stats["num_features"],
            val_report.micro_precision,
            val_report.micro_recall,
            val_report.micro_f1,
            val_secs,
        )

        if val_report.micro_f1 > best_val_f1:
            if best_model is not None:
                del best_model
            best_model = model
            best_val_f1 = val_report.micro_f1
            best_candidate_info = record
        else:
            del model
        gc.collect()

    assert best_model is not None
    logger.info(
        "Selected Best Model on Validation: %s (Val Micro F1=%.4f)",
        best_candidate_info["name"],
        best_val_f1,
    )

    # Confirm selected frozen model on FULL validation partition before freezing (still zero test exposure)
    full_val_start = time.time()
    full_val_report = evaluate_documents_strict(best_model, val_docs)
    full_val_secs = time.time() - full_val_start
    logger.info(
        "Full Validation Verification (%d docs, %d gold spans) -> P=%.4f R=%.4f F1=%.4f (%.1fs)",
        full_val_report.total_documents_evaluated,
        full_val_report.total_gold_entities,
        full_val_report.micro_precision,
        full_val_report.micro_recall,
        full_val_report.micro_f1,
        full_val_secs,
    )

    # 4. Freeze model checkpoint and persist config, version, and split metadata BEFORE touching final_test
    logger.info("[Step 4/5] Freezing winning model checkpoint and writing configuration/version artifacts...")
    best_model.save(output_model_path)
    model_size_bytes = output_model_path.stat().st_size
    model_sha256 = _sha256_file(output_model_path)
    created_utc = datetime.now(timezone.utc).isoformat()
    git_head = _get_git_commit_short()

    model_config_payload = {
        "selected_candidate": best_candidate_info["name"],
        "model_version": FINAL_MODEL_VERSION,
        "classifier_type": best_model.classifier_type,
        "loss": best_model.loss,
        "c_param": best_model.c_param,
        "alpha": best_model.classifier.alpha,
        "max_iter": best_model.max_iter,
        "class_weight": best_model.class_weight,
        "feature_window": best_model.window,
        "dtype": "float32",
        "allowed_entity_labels": list(ALLOWED_ENTITY_LABELS),
        "split_seed": final_seed,
        "train_docs_used": best_candidate_info["train_docs_used"],
        "feature_statistics": best_candidate_info["fit_stats"],
        "full_validation_metrics": {
            "documents": full_val_report.total_documents_evaluated,
            "gold_entities": full_val_report.total_gold_entities,
            "precision": round(full_val_report.micro_precision, 4),
            "recall": round(full_val_report.micro_recall, 4),
            "micro_f1": round(full_val_report.micro_f1, 4),
            "eval_seconds": round(full_val_secs, 2),
        },
        "validation_candidate_comparison": selection_results,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(model_config_payload, f, indent=2)

    version_payload = {
        "model_version": FINAL_MODEL_VERSION,
        "base_git_commit": git_head,
        "created_at_utc": created_utc,
        "artifact_path": str(output_model_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "artifact_size_bytes": model_size_bytes,
        "artifact_size_mb": round(model_size_bytes / (1024 * 1024), 2),
        "artifact_sha256": model_sha256,
        "allowed_entity_labels": list(ALLOWED_ENTITY_LABELS),
        "bio_classes": [str(c) for c in best_model.classes_] if best_model.classes_ is not None else [],
        "scientific_scope_note": (
            "Extracts MMLite biomedical mentions from forum text only. "
            "Not a participant-level PPD diagnosis or severity classifier."
        ),
    }
    version_path.parent.mkdir(parents=True, exist_ok=True)
    with open(version_path, "w", encoding="utf-8") as f:
        json.dump(version_payload, f, indent=2)

    logger.info(
        "Model frozen at %s (%.2f MB, sha256=%s...) BEFORE final test evaluation.",
        output_model_path,
        model_size_bytes / (1024 * 1024),
        model_sha256[:12],
    )

    # 5. Single-shot evaluation on COMPLETE fresh final_test partition
    logger.info(
        "[Step 5/5] Running single-shot final evaluation across ALL %d fresh final_test documents...",
        len(final_test_docs),
    )
    eval_start = time.time()
    final_eval_report = evaluate_documents_strict(
        best_model,
        final_test_docs,
        runtime_seconds=0.0,
        model_size_bytes=model_size_bytes,
    )
    eval_runtime = time.time() - eval_start
    final_eval_report.runtime_seconds = round(eval_runtime, 2)
    save_evaluation_report(final_eval_report, metrics_path)

    mmlite_metrics = final_eval_report.per_label_metrics["MMLite"]
    logger.info("-" * 72)
    logger.info("FINAL HELD-OUT TEST EVALUATION (STRICT ENTITY-SPAN MATCHING)")
    logger.info("  Documents Evaluated:        %d", final_eval_report.total_documents_evaluated)
    logger.info("  Gold Entity Support:        %d", final_eval_report.total_gold_entities)
    logger.info("  Predicted Entities:         %d", final_eval_report.total_predicted_entities)
    logger.info("  True Positives:             %d", mmlite_metrics.true_positives)
    logger.info("  False Positives:            %d", mmlite_metrics.false_positives)
    logger.info("  False Negatives:            %d", mmlite_metrics.false_negatives)
    logger.info("  Strict Micro Precision:     %.4f", final_eval_report.micro_precision)
    logger.info("  Strict Micro Recall:        %.4f", final_eval_report.micro_recall)
    logger.info("  Strict Micro F1:            %.4f", final_eval_report.micro_f1)
    logger.info("  Strict Macro F1:            %.4f", final_eval_report.macro_f1)
    logger.info("  Error Breakdown:            %s", final_eval_report.error_analysis)
    logger.info("  Final Test Runtime:         %.2fs", eval_runtime)
    logger.info("  Total Pipeline Runtime:     %.2fs", time.time() - pipeline_start)
    logger.info("  Model Artifact Size:        %d bytes (%.2f MB)", model_size_bytes, model_size_bytes / (1024 * 1024))
    logger.info("-" * 72)

    summary_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "prior_commit_reference": git_head,
        "legacy_evaluation_limitation": {
            "legacy_seed": RANDOM_SEED,
            "legacy_test_total_docs": 1586,
            "legacy_evaluated_subset_docs": 150,
            "legacy_reported_metrics_150_docs": {
                "precision": 0.5711,
                "recall": 0.8640,
                "f1": 0.6877,
            },
            "reason_for_refresh": (
                "Legacy 150-doc subset was reused for error analysis that informed "
                "hyperparameter/feature iteration; full 1,586-doc test partition had not been evaluated."
            ),
        },
        "clean_split_metadata": {
            "final_seed": split_report.seed,
            "total_documents": split_report.total_documents,
            "total_retained_annotations": split_report.total_retained_annotations,
            "excluded_prior_exposed_count": split_report.excluded_prior_exposed_count,
            "eligible_fresh_test_pool_count": split_report.eligible_fresh_test_pool_count,
            "overlap_verified_zero_doc_ids": split_report.overlap_verified_zero_doc_ids,
            "overlap_verified_zero_thread_urls": split_report.overlap_verified_zero_thread_urls,
            "final_test_zero_prior_exposure_verified": split_report.final_test_zero_prior_exposure_verified,
            "split_manifest_path": "data/processed/text_ner/final_dataset_splits.json",
            "partitions": {
                part_name: {
                    k: v
                    for k, v in asdict(part_meta).items()
                    if k != "document_ids"
                }
                for part_name, part_meta in (
                    ("train", split_report.train),
                    ("val", split_report.val),
                    ("final_test", split_report.final_test),
                )
            },
        },
        "frozen_model_config": model_config_payload,
        "model_version_info": version_payload,
        "final_test_metrics_complete": {
            "documents_evaluated": final_eval_report.total_documents_evaluated,
            "gold_entities_support": final_eval_report.total_gold_entities,
            "predicted_entities": final_eval_report.total_predicted_entities,
            "true_positives": mmlite_metrics.true_positives,
            "false_positives": mmlite_metrics.false_positives,
            "false_negatives": mmlite_metrics.false_negatives,
            "strict_micro_precision": round(final_eval_report.micro_precision, 4),
            "strict_micro_recall": round(final_eval_report.micro_recall, 4),
            "strict_micro_f1": round(final_eval_report.micro_f1, 4),
            "strict_macro_f1": round(final_eval_report.macro_f1, 4),
            "error_analysis": final_eval_report.error_analysis,
            "evaluation_runtime_seconds": round(eval_runtime, 2),
            "total_pipeline_runtime_seconds": round(time.time() - pipeline_start, 2),
            "model_artifact_size_bytes": model_size_bytes,
            "model_artifact_size_mb": round(model_size_bytes / (1024 * 1024), 2),
        },
        "semantic_type_audit": semantic_summary,
    }
    docs_summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(docs_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    return summary_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run leak-free final NER evaluation pipeline.")
    parser.add_argument("--seed", type=int, default=FINAL_SPLIT_SEED)
    parser.add_argument("--val_eval_limit", type=int, default=400)
    args = parser.parse_args()
    run_final_evaluation_pipeline(
        final_seed=args.seed,
        val_eval_docs_limit=args.val_eval_limit,
    )


if __name__ == "__main__":
    main()

