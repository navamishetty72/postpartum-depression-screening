"""Strict entity-span evaluation protocol for Named Entity Recognition.

Computes exact boundary and label matching precision, recall, and F1 scores
without relying on token-level accuracy.
"""

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pipelines.text_ner.models import TextNERModel
from pipelines.text_ner.parser import Document, EntitySpan


@dataclass
class LabelMetrics:
    """Evaluation metrics for a specific entity label."""

    true_positives: int
    false_positives: int
    false_negatives: int
    support: int
    precision: float
    recall: float
    f1_score: float
    is_reliable_estimate: bool


@dataclass
class StrictEvaluationReport:
    """Strict entity-span evaluation report across a test partition."""

    total_documents_evaluated: int
    total_gold_entities: int
    total_predicted_entities: int
    micro_precision: float
    micro_recall: float
    micro_f1: float
    macro_f1: float
    per_label_metrics: Dict[str, LabelMetrics]
    error_analysis: Dict[str, int]
    runtime_seconds: float
    model_artifact_size_bytes: int
    unreliable_labels: List[str]


def evaluate_documents_strict(
    model: TextNERModel,
    docs: List[Document],
    runtime_seconds: float = 0.0,
    model_size_bytes: int = 0,
) -> StrictEvaluationReport:
    """Perform strict entity-span evaluation on a document corpus.

    An entity is counted as a true positive if and only if both its
    exact character boundaries (start, end) and entity label match the gold standard.
    """
    total_gold = 0
    total_pred = 0

    tp_by_label: Counter = Counter()
    fp_by_label: Counter = Counter()
    fn_by_label: Counter = Counter()
    gold_by_label: Counter = Counter()

    error_counts: Counter = Counter()

    for doc in docs:
        gold_spans = set()
        gold_map: Dict[Tuple[int, int], str] = {}
        for s in doc.spans:
            gold_spans.add((s.start, s.end, s.label))
            gold_map[(s.start, s.end)] = s.label
            gold_by_label[s.label] += 1
            total_gold += 1

        pred_spans_dicts = model.predict_text(doc.text)
        pred_spans = set()
        for p in pred_spans_dicts:
            pred_spans.add((p["start"], p["end"], p["label"]))
            total_pred += 1

        # Evaluate exact matches
        matched_gold = set()
        matched_pred = set()

        for pred in pred_spans:
            if pred in gold_spans:
                tp_by_label[pred[2]] += 1
                matched_gold.add(pred)
                matched_pred.add(pred)
            else:
                fp_by_label[pred[2]] += 1
                # Error analysis: check if it overlaps a gold entity (boundary mismatch)
                has_overlap = False
                for gold in gold_spans:
                    if max(pred[0], gold[0]) < min(pred[1], gold[1]):
                        has_overlap = True
                        if pred[2] == gold[2]:
                            error_counts["boundary_mismatch_same_label"] += 1
                        else:
                            error_counts["boundary_and_label_mismatch"] += 1
                        break
                if not has_overlap:
                    error_counts["spurious_entity"] += 1

        for gold in gold_spans:
            if gold not in matched_gold:
                fn_by_label[gold[2]] += 1
                # Check if it was overlapping any prediction
                has_overlap = False
                for pred in pred_spans:
                    if max(pred[0], gold[0]) < min(pred[1], gold[1]):
                        has_overlap = True
                        break
                if not has_overlap:
                    error_counts["completely_missed_entity"] += 1

    # Aggregate metrics
    all_labels = sorted(set(gold_by_label.keys()) | set(tp_by_label.keys()) | set(fp_by_label.keys()))
    per_label_metrics: Dict[str, LabelMetrics] = {}
    f1_list: List[float] = []
    unreliable_labels: List[str] = []

    total_tp = sum(tp_by_label.values())
    total_fp = sum(fp_by_label.values())
    total_fn = sum(fn_by_label.values())

    micro_prec = total_tp / max(1, total_tp + total_fp)
    micro_rec = total_tp / max(1, total_tp + total_fn)
    micro_f1 = (
        (2 * micro_prec * micro_rec) / (micro_prec + micro_rec)
        if (micro_prec + micro_rec) > 0
        else 0.0
    )

    for label in all_labels:
        tp = tp_by_label[label]
        fp = fp_by_label[label]
        fn = fn_by_label[label]
        support = gold_by_label[label]

        p = tp / max(1, tp + fp)
        r = tp / max(1, tp + fn)
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        f1_list.append(f1)

        is_reliable = support >= 5
        if not is_reliable:
            unreliable_labels.append(label)

        per_label_metrics[label] = LabelMetrics(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            support=support,
            precision=round(p, 4),
            recall=round(r, 4),
            f1_score=round(f1, 4),
            is_reliable_estimate=is_reliable,
        )

    macro_f1 = sum(f1_list) / max(1, len(f1_list))

    return StrictEvaluationReport(
        total_documents_evaluated=len(docs),
        total_gold_entities=total_gold,
        total_predicted_entities=total_pred,
        micro_precision=round(micro_prec, 4),
        micro_recall=round(micro_rec, 4),
        micro_f1=round(micro_f1, 4),
        macro_f1=round(macro_f1, 4),
        per_label_metrics=per_label_metrics,
        error_analysis=dict(error_counts),
        runtime_seconds=round(runtime_seconds, 2),
        model_artifact_size_bytes=model_size_bytes,
        unreliable_labels=unreliable_labels,
    )


def save_evaluation_report(
    report: StrictEvaluationReport,
    output_path: Path,
) -> None:
    """Save strict evaluation report as formatted JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_dict = asdict(report)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

