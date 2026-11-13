"""Dataset validation, character-offset verification, and overlap resolution.

Validates annotations against annotation.conf, checks offset bounds, verifies
exact span text match against underlying document, detects duplicates/overlaps,
and generates a machine-readable validation report.
"""

from collections import Counter
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from pipelines.text_ner.config import ALLOWED_ENTITY_LABELS, PreprocessingConfig
from pipelines.text_ner.parser import Document, EntitySpan


@dataclass
class ValidationSummary:
    """Aggregated validation statistics across the corpus."""

    total_documents: int = 0
    documents_with_annotations: int = 0
    documents_without_annotations: int = 0
    total_raw_annotations: int = 0
    valid_exact_annotations: int = 0
    reconciled_annotations: int = 0
    ambiguous_reconciliations: int = 0
    failed_reconciliations: int = 0
    invalid_start_ge_end: int = 0
    invalid_out_of_bounds: int = 0
    invalid_unknown_label: int = 0
    invalid_text_mismatch: int = 0
    duplicate_annotations: int = 0
    overlapping_spans_detected: int = 0
    overlapping_spans_resolved: int = 0
    final_retained_annotations: int = 0
    label_distribution: Dict[str, int] = field(default_factory=dict)
    semantic_type_distribution: Dict[str, int] = field(default_factory=dict)


def resolve_overlaps(
    spans: List[EntitySpan],
    strategy: str = "longest",
) -> Tuple[List[EntitySpan], int]:
    """Explicitly resolve overlapping entity spans according to strategy.

    Strategies:
      'longest': Prioritize longer span; break ties by earliest start.
      'first': Prioritize earliest start; break ties by longest span.

    Returns:
      retained_spans: List of non-overlapping EntitySpan objects.
      discarded_count: Number of overlapping spans discarded.
    """
    if len(spans) <= 1:
        return spans, 0

    if strategy == "longest":
        # Sort by length descending, then start ascending
        sorted_spans = sorted(spans, key=lambda s: (-s.length, s.start))
    else:  # 'first'
        # Sort by start ascending, then length descending
        sorted_spans = sorted(spans, key=lambda s: (s.start, -s.length))

    retained: List[EntitySpan] = []
    discarded_count = 0

    for candidate in sorted_spans:
        # Check collision with already retained spans
        has_overlap = False
        for kept in retained:
            if not (candidate.end <= kept.start or candidate.start >= kept.end):
                has_overlap = True
                break

        if not has_overlap:
            retained.append(candidate)
        else:
            discarded_count += 1

    # Return retained spans in chronological start order
    retained.sort(key=lambda s: (s.start, s.end))
    return retained, discarded_count


class DatasetValidator:
    """Validates raw parsed documents and applies strict character-offset verification."""

    def __init__(self, config: Optional[PreprocessingConfig] = None) -> None:
        self.config = config or PreprocessingConfig()

    def validate_document(
        self,
        doc: Document,
    ) -> Tuple[List[EntitySpan], List[str]]:
        """Validate and clean annotations for a single document.

        Returns:
          valid_spans: Valid, deduplicated, non-overlapping EntitySpan objects.
          issues: List of diagnostic issue codes.
        """
        text = doc.text
        text_len = len(text)
        validated_spans: List[EntitySpan] = []
        issues: List[str] = []
        seen_keys: Set[Tuple[int, int, str]] = set()

        for span in doc.spans:
            # 1. Start < End
            if span.start >= span.end:
                issues.append("INVALID_START_GE_END")
                continue

            # 2. Within text bounds
            if span.start < 0 or span.end > text_len:
                issues.append("OUT_OF_BOUNDS")
                continue

            # 3. Label in allowed labels
            if span.label not in self.config.allowed_labels:
                issues.append(f"UNKNOWN_LABEL_{span.label}")
                continue

            # 4. Text matching check
            extracted = text[span.start : span.end]
            if extracted == span.text:
                # Exact match
                pass
            else:
                # Attempt local window reconciliation
                window_start = max(0, span.start - self.config.reconcile_window)
                window_end = min(text_len, span.end + self.config.reconcile_window)
                window_text = text[window_start:window_end]

                # Check if exact span text occurs unambiguously within local window
                occurrences = []
                idx = window_text.find(span.text)
                while idx != -1:
                    occurrences.append(window_start + idx)
                    idx = window_text.find(span.text, idx + 1)

                if len(occurrences) == 1:
                    # Unambiguous local match: reconcile offsets
                    new_start = occurrences[0]
                    new_end = new_start + len(span.text)
                    span.start = new_start
                    span.end = new_end
                    issues.append("RECONCILED_LOCAL_OFFSET")
                elif len(occurrences) > 1:
                    # Multiple possible matches detected in local window
                    issues.append("AMBIGUOUS_LOCAL_MATCH")
                    issues.append("TEXT_MISMATCH")
                    continue
                else:
                    # Zero occurrences found within local search window
                    issues.append("FAILED_RECONCILIATION_ZERO_MATCH")
                    issues.append("TEXT_MISMATCH")
                    continue

            # 5. Duplicate check
            span_key = (span.start, span.end, span.label)
            if span_key in seen_keys:
                issues.append("DUPLICATE_ANNOTATION")
                continue
            seen_keys.add(span_key)

            validated_spans.append(span)

        # 6. Explicit overlap handling
        # Count overlapping pairs before resolution
        validated_spans.sort(key=lambda s: (s.start, s.end))
        overlap_pairs = 0
        for i in range(len(validated_spans) - 1):
            if validated_spans[i].end > validated_spans[i + 1].start:
                overlap_pairs += 1

        if overlap_pairs > 0:
            issues.append(f"OVERLAPPING_SPANS_{overlap_pairs}")

        cleaned_spans, resolved_count = resolve_overlaps(
            validated_spans,
            strategy=self.config.overlap_strategy,
        )

        return cleaned_spans, issues

    def validate_corpus(
        self,
        docs: List[Document],
    ) -> Tuple[List[Document], ValidationSummary]:
        """Validate an entire corpus of documents, updating their span lists.

        Returns:
          cleaned_docs: Corpus with validated and non-overlapping spans.
          summary: Detailed validation report metrics.
        """
        summary = ValidationSummary()
        summary.total_documents = len(docs)
        cleaned_docs: List[Document] = []

        label_counter: Counter = Counter()
        sem_counter: Counter = Counter()

        for doc in docs:
            raw_count = len(doc.spans)
            summary.total_raw_annotations += raw_count
            if raw_count == 0:
                summary.documents_without_annotations += 1
            else:
                summary.documents_with_annotations += 1

            valid_spans, issues = self.validate_document(doc)

            for issue in issues:
                if issue == "INVALID_START_GE_END":
                    summary.invalid_start_ge_end += 1
                elif issue == "OUT_OF_BOUNDS":
                    summary.invalid_out_of_bounds += 1
                elif issue.startswith("UNKNOWN_LABEL"):
                    summary.invalid_unknown_label += 1
                elif issue == "TEXT_MISMATCH":
                    summary.invalid_text_mismatch += 1
                elif issue == "AMBIGUOUS_LOCAL_MATCH":
                    summary.ambiguous_reconciliations += 1
                elif issue == "FAILED_RECONCILIATION_ZERO_MATCH":
                    summary.failed_reconciliations += 1
                elif issue == "RECONCILED_LOCAL_OFFSET":
                    summary.reconciled_annotations += 1
                elif issue == "DUPLICATE_ANNOTATION":
                    summary.duplicate_annotations += 1
                elif issue.startswith("OVERLAPPING_SPANS_"):
                    summary.overlapping_spans_detected += int(issue.split("_")[-1])

            retained_count = len(valid_spans)
            summary.final_retained_annotations += retained_count
            summary.valid_exact_annotations += (
                retained_count - issues.count("RECONCILED_LOCAL_OFFSET")
            )

            for span in valid_spans:
                label_counter[span.label] += 1
                for st in span.semantic_types:
                    sem_counter[st] += 1

            cleaned_docs.append(
                Document(
                    id=doc.id,
                    group=doc.group,
                    text=doc.text,
                    spans=valid_spans,
                )
            )

        summary.overlapping_spans_resolved = (
            summary.overlapping_spans_detected
        )
        summary.label_distribution = dict(label_counter)
        summary.semantic_type_distribution = dict(sem_counter)

        # Save validation report
        self._save_report(summary)

        return cleaned_docs, summary

    def _save_report(self, summary: ValidationSummary) -> None:
        """Serialize validation statistics to machine-readable JSON."""
        output_path = self.config.validation_report_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report_data = asdict(summary)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

