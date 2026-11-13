"""Configurable training and model selection pipeline for Text Named Entity Recognition.

Executes data validation, document-isolated splitting, feature generation,
validation-based model selection, checkpoint serialization, and test evaluation.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import time
from typing import List, Tuple

from pipelines.text_ner.config import (
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    MODELS_DIR,
    RANDOM_SEED,
    PreprocessingConfig,
    SplitConfig,
    TrainingConfig,
)
from pipelines.text_ner.evaluate import (
    evaluate_documents_strict,
    save_evaluation_report,
)
from pipelines.text_ner.features import (
    align_spans_to_bio,
    extract_document_features,
    tokenize_with_offsets,
)
from pipelines.text_ner.models import TextNERModel
from pipelines.text_ner.parser import Document, load_corpus_from_zips
from pipelines.text_ner.splitter import ThreadDatasetSplitter
from pipelines.text_ner.validator import DatasetValidator


def extract_features_from_docs(
    docs: List[Document],
    window: int = 2,
    max_docs: int = -1,
) -> Tuple[List[dict], List[str]]:
    """Convert documents into flattened token feature dictionaries and BIO ground-truth labels."""
    X_dicts: List[dict] = []
    y_tags: List[str] = []

    target_docs = docs[:max_docs] if max_docs > 0 else docs
    for doc in target_docs:
        tokens = tokenize_with_offsets(doc.text)
        if not tokens:
            continue
        bio_tags = align_spans_to_bio(tokens, doc.spans)
        doc_features = extract_document_features(tokens, window=window)

        X_dicts.extend(doc_features)
        y_tags.extend(bio_tags)

    return X_dicts, y_tags


def run_training_pipeline(
    raw_data_dir: Path = DATA_RAW_DIR,
    output_model_path: Path = MODELS_DIR / "text_ner_model.joblib",
    metrics_path: Path = DATA_PROCESSED_DIR / "evaluation_metrics.json",
    seed: int = RANDOM_SEED,
    max_train_samples: int = 1500,
) -> dict:
    """Run full reproducible training, validation, and evaluation pipeline."""
    start_time = time.time()
    print("=" * 70)
    print("STARTING TEXT NER TRAINING PIPELINE")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Random seed: {seed}")
    print(f"Raw data path: {raw_data_dir}")
    print("=" * 70)

    # 1. Ingestion
    print("\n[Step 1/6] Ingesting raw corpus...")
    corpus = load_corpus_from_zips(raw_data_dir)
    if not corpus:
        raise FileNotFoundError(
            f"No valid documents loaded from {raw_data_dir}. Ensure dataset is present."
        )
    print(f"Loaded {len(corpus)} total raw document pairs from corpus archives.")

    # 2. Validation & Preprocessing
    print("\n[Step 2/6] Validating annotations and reconciling offsets...")
    validator = DatasetValidator(PreprocessingConfig())
    cleaned_corpus, val_summary = validator.validate_corpus(corpus)
    print(f"Total raw annotations: {val_summary.total_raw_annotations}")
    print(f"Retained non-overlapping valid annotations: {val_summary.final_retained_annotations}")
    print(f"Exact matches: {val_summary.valid_exact_annotations}")
    print(f"Reconciled offsets: {val_summary.reconciled_annotations}")
    print(f"Invalid text mismatches: {val_summary.invalid_text_mismatch}")
    print(f"Overlapping spans resolved: {val_summary.overlapping_spans_resolved}")

    # 3. Thread-isolated Splitting
    print("\n[Step 3/6] Splitting dataset into train (70%), val (15%), test (15%)...")
    splitter = ThreadDatasetSplitter(SplitConfig(seed=seed))
    split_manifest_path = DATA_PROCESSED_DIR / "dataset_splits.json"
    train_docs, val_docs, test_docs, split_report = splitter.split(
        cleaned_corpus,
        output_manifest_path=split_manifest_path,
    )
    print(f"Train documents: {len(train_docs)} ({split_report.train.num_annotations} entities)")
    print(f"Val documents:   {len(val_docs)} ({split_report.val.num_annotations} entities)")
    print(f"Test documents:  {len(test_docs)} ({split_report.test.num_annotations} entities)")

    # 4. Feature Extraction
    print(f"\n[Step 4/6] Extracting token features (max_train_samples={max_train_samples})...")
    X_train, y_train = extract_features_from_docs(train_docs, max_docs=max_train_samples)
    print(f"Training tokens: {len(X_train)} tokens extracted.")

    # 5. Model Training & Validation Tuning
    print("\n[Step 5/6] Tuning and training candidate models on validation set...")
    candidates = [
        {"name": "Baseline (log_loss, C=1.0)", "loss": "log_loss", "c_param": 1.0},
        {"name": "Candidate 1 (modified_huber, C=0.5)", "loss": "modified_huber", "c_param": 0.5},
        {"name": "Candidate 2 (modified_huber, C=1.0)", "loss": "modified_huber", "c_param": 1.0},
        {"name": "Candidate 3 (modified_huber, C=2.0)", "loss": "modified_huber", "c_param": 2.0},
    ]
    best_model: TextNERModel = None
    best_val_f1 = -1.0
    best_config_name = ""

    # Validation subset for rapid selection
    val_sub = val_docs[:150]

    for cand in candidates:
        candidate_model = TextNERModel(
            classifier_type="sgd",
            loss=cand["loss"],
            c_param=cand["c_param"],
            max_iter=500,
            random_state=seed,
            class_weight="balanced",
        )
        candidate_model.fit(X_train, y_train)

        # Evaluate on validation partition
        val_eval = evaluate_documents_strict(candidate_model, val_sub)
        print(f"  [{cand['name']}] -> Val Micro F1: {val_eval.micro_f1:.4f} (P: {val_eval.micro_precision:.4f}, R: {val_eval.micro_recall:.4f})")

        if val_eval.micro_f1 > best_val_f1:
            best_val_f1 = val_eval.micro_f1
            best_model = candidate_model
            best_config_name = cand["name"]

    print(f"Selected Best Model: {best_config_name} with Validation Micro F1: {best_val_f1:.4f}")

    # Save Model Checkpoint
    best_model.save(output_model_path)
    model_size = output_model_path.stat().st_size
    print(f"Saved model checkpoint to: {output_model_path} ({model_size / 1024:.1f} KB)")

    # 6. Evaluation on Held-Out Test Set
    print("\n[Step 6/6] Evaluating best model ONCE on held-out test partition...")
    test_sub = test_docs[:150]  # Representative evaluation partition
    test_eval_start = time.time()
    test_eval = evaluate_documents_strict(
        best_model,
        test_sub,
        runtime_seconds=time.time() - start_time,
        model_size_bytes=model_size,
    )
    save_evaluation_report(test_eval, metrics_path)

    print("\n" + "=" * 70)
    print("TEST EVALUATION RESULTS (STRICT ENTITY-SPAN MATCHING):")
    print(f"  Total Test Documents:        {test_eval.total_documents_evaluated}")
    print(f"  Total Gold Entities:         {test_eval.total_gold_entities}")
    print(f"  Total Predicted Entities:    {test_eval.total_predicted_entities}")
    print(f"  Entity-level Micro Precision: {test_eval.micro_precision:.4f}")
    print(f"  Entity-level Micro Recall:    {test_eval.micro_recall:.4f}")
    print(f"  Entity-level Micro F1:        {test_eval.micro_f1:.4f}")
    print(f"  Entity-level Macro F1:        {test_eval.macro_f1:.4f}")
    print("\nPer-Label Metrics:")
    for lbl, m in test_eval.per_label_metrics.items():
        print(f"  [{lbl}] Support: {m.support} | Prec: {m.precision:.4f} | Rec: {m.recall:.4f} | F1: {m.f1_score:.4f} | Reliable: {m.is_reliable_estimate}")
    print(f"\nError Analysis: {test_eval.error_analysis}")
    print(f"Total Runtime: {time.time() - start_time:.2f} seconds")
    print("=" * 70)

    return {
        "micro_precision": test_eval.micro_precision,
        "micro_recall": test_eval.micro_recall,
        "micro_f1": test_eval.micro_f1,
        "macro_f1": test_eval.macro_f1,
        "model_artifact": str(output_model_path),
        "metrics_artifact": str(metrics_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train text NER baseline model.")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--max_train", type=int, default=1500)
    parser.add_argument("--raw_data", type=Path, default=DATA_RAW_DIR)
    parser.add_argument("--model_output", type=Path, default=MODELS_DIR / "text_ner_model.joblib")
    args = parser.parse_args()

    run_training_pipeline(
        raw_data_dir=args.raw_data,
        output_model_path=args.model_output,
        seed=args.seed,
        max_train_samples=args.max_train,
    )


if __name__ == "__main__":
    main()

