"""Thread-level isolated dataset splitter for reproducible train/val/test partitions.

Guarantees zero leakage across splits by strictly isolating entire documents/threads.
"""

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random
from typing import Dict, List, Optional, Tuple

from pipelines.text_ner.config import SplitConfig
from pipelines.text_ner.parser import Document


@dataclass
class SplitPartitionMetadata:
    """Statistics for an individual dataset split partition."""

    num_documents: int
    num_annotations: int
    label_counts: Dict[str, int]
    semantic_type_counts: Dict[str, int]
    document_ids: List[str]


@dataclass
class DatasetSplitReport:
    """Full split metadata report covering train, val, and test splits."""

    random_seed: int
    train_ratio: float
    val_ratio: float
    test_ratio: float
    train: SplitPartitionMetadata
    val: SplitPartitionMetadata
    test: SplitPartitionMetadata
    rare_labels_in_test: List[str]


def compute_partition_metadata(docs: List[Document]) -> SplitPartitionMetadata:
    """Compute document and label count statistics for a set of documents."""
    label_counter: Counter = Counter()
    sem_counter: Counter = Counter()
    total_spans = 0

    for doc in docs:
        total_spans += len(doc.spans)
        for s in doc.spans:
            label_counter[s.label] += 1
            for st in s.semantic_types:
                sem_counter[st] += 1

    return SplitPartitionMetadata(
        num_documents=len(docs),
        num_annotations=total_spans,
        label_counts=dict(label_counter),
        semantic_type_counts=dict(sem_counter),
        document_ids=[doc.id for doc in docs],
    )


class ThreadDatasetSplitter:
    """Splits corpus by original thread/document with strict isolation."""

    def __init__(self, config: Optional[SplitConfig] = None) -> None:
        self.config = config or SplitConfig()

    def split(
        self,
        docs: List[Document],
        output_manifest_path: Optional[Path] = None,
    ) -> Tuple[List[Document], List[Document], List[Document], DatasetSplitReport]:
        """Perform document-isolated 70/15/15 train/val/test splitting."""
        if not docs:
            raise ValueError("Cannot split an empty document corpus.")

        # Ensure determinism: sort by doc ID before fixed-seed shuffle
        sorted_docs = sorted(docs, key=lambda d: d.id)
        rng = random.Random(self.config.seed)
        shuffled_docs = list(sorted_docs)
        rng.shuffle(shuffled_docs)

        n_total = len(shuffled_docs)
        n_train = int(n_total * self.config.train_ratio)
        n_val = int(n_total * self.config.val_ratio)

        train_docs = shuffled_docs[:n_train]
        val_docs = shuffled_docs[n_train : n_train + n_val]
        test_docs = shuffled_docs[n_train + n_val :]

        train_meta = compute_partition_metadata(train_docs)
        val_meta = compute_partition_metadata(val_docs)
        test_meta = compute_partition_metadata(test_docs)

        # Detect labels that have < 5 occurrences in test set
        rare_in_test = [
            label
            for label, count in test_meta.label_counts.items()
            if count < 5
        ]

        report = DatasetSplitReport(
            random_seed=self.config.seed,
            train_ratio=self.config.train_ratio,
            val_ratio=self.config.val_ratio,
            test_ratio=self.config.test_ratio,
            train=train_meta,
            val=val_meta,
            test=test_meta,
            rare_labels_in_test=rare_in_test,
        )

        if output_manifest_path is not None:
            output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_manifest_path, "w", encoding="utf-8") as f:
                json.dump(asdict(report), f, indent=2)

        return train_docs, val_docs, test_docs, report

    def split_leak_free_final(
        self,
        docs: List[Document],
        excluded_from_test_ids: List[str],
        exclude_from_val_ids: Optional[List[str]] = None,
        final_seed: int = 2026,
        output_manifest_path: Optional[Path] = None,
    ) -> Tuple[List[Document], List[Document], List[Document], "LeakFreeSplitReport"]:
        """Create a leak-free final train/val/final_test split.

        Guarantees zero document ID or thread URL overlap across partitions and
        guarantees zero prior exposure of ``final_test`` documents in the
        supplied ``excluded_from_test_ids`` (e.g. docs used previously for
        training, validation tuning, or test error analysis).
        """
        if not docs:
            raise ValueError("Cannot split an empty document corpus.")

        sorted_docs = sorted(docs, key=lambda d: d.id)
        n_total = len(sorted_docs)
        n_train = int(n_total * self.config.train_ratio)
        n_val = int(n_total * self.config.val_ratio)
        n_test = n_total - n_train - n_val

        excluded_test_set = set(excluded_from_test_ids)
        eligible_for_test = [d for d in sorted_docs if d.id not in excluded_test_set]
        if len(eligible_for_test) < n_test:
            raise ValueError(
                f"Only {len(eligible_for_test)} untouched docs remain, fewer than requested final_test={n_test}."
            )

        rng_test = random.Random(final_seed)
        shuffled_test_pool = list(eligible_for_test)
        rng_test.shuffle(shuffled_test_pool)
        final_test_docs = shuffled_test_pool[:n_test]
        final_test_ids = {d.id for d in final_test_docs}

        dev_docs = [d for d in sorted_docs if d.id not in final_test_ids]
        excluded_val_set = set(exclude_from_val_ids or [])
        eligible_for_val = [d for d in dev_docs if d.id not in excluded_val_set]

        rng_dev = random.Random(final_seed + 1)
        if len(eligible_for_val) >= n_val and excluded_val_set:
            shuffled_val_pool = list(eligible_for_val)
            rng_dev.shuffle(shuffled_val_pool)
            val_docs = shuffled_val_pool[:n_val]
            val_ids = {d.id for d in val_docs}
            train_docs = [d for d in dev_docs if d.id not in val_ids]
            rng_train = random.Random(final_seed + 2)
            rng_train.shuffle(train_docs)
        else:
            shuffled_dev = list(dev_docs)
            rng_dev.shuffle(shuffled_dev)
            train_docs = shuffled_dev[:n_train]
            val_docs = shuffled_dev[n_train:]

        # Hard disjointness & URL overlap assertions
        train_ids = {d.id for d in train_docs}
        val_ids = {d.id for d in val_docs}
        test_ids = {d.id for d in final_test_docs}

        if (train_ids & val_ids) or (train_ids & test_ids) or (val_ids & test_ids):
            raise RuntimeError("Critical overlap detected across leak-free partitions!")
        if test_ids & excluded_test_set:
            raise RuntimeError("Final test partition contains previously exposed documents!")

        def _extract_urls(partition: List[Document]) -> set[str]:
            urls: set[str] = set()
            for doc in partition:
                if doc.text.startswith("# URL: "):
                    first_line = doc.text.split("\n", 1)[0].strip()
                    urls.add(first_line[7:].strip())
            return urls

        train_urls = _extract_urls(train_docs)
        val_urls = _extract_urls(val_docs)
        test_urls = _extract_urls(final_test_docs)
        zero_url_overlap = not (
            (train_urls & val_urls) or (train_urls & test_urls) or (val_urls & test_urls)
        )
        if not zero_url_overlap:
            raise RuntimeError("Thread URL overlap detected across leak-free partitions!")

        present_excluded = sorted(excluded_test_set & {d.id for d in sorted_docs})
        report = LeakFreeSplitReport(
            seed=final_seed,
            total_documents=n_total,
            total_retained_annotations=sum(len(d.spans) for d in sorted_docs),
            excluded_prior_exposed_count=len(present_excluded),
            excluded_prior_exposed_doc_ids=present_excluded,
            eligible_fresh_test_pool_count=len(eligible_for_test),
            overlap_verified_zero_doc_ids=True,
            overlap_verified_zero_thread_urls=zero_url_overlap,
            final_test_zero_prior_exposure_verified=True,
            train=compute_partition_metadata(train_docs),
            val=compute_partition_metadata(val_docs),
            final_test=compute_partition_metadata(final_test_docs),
            train_doc_ids=[d.id for d in train_docs],
            val_doc_ids=[d.id for d in val_docs],
            final_test_doc_ids=[d.id for d in final_test_docs],
        )

        if output_manifest_path is not None:
            output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_manifest_path, "w", encoding="utf-8") as f:
                json.dump(asdict(report), f, indent=2)

        return train_docs, val_docs, final_test_docs, report


from dataclasses import dataclass as _dataclass


@_dataclass
class LeakFreeSplitReport:
    """Audit report and document manifest for a leak-free final evaluation split."""

    seed: int
    total_documents: int
    total_retained_annotations: int
    excluded_prior_exposed_count: int
    excluded_prior_exposed_doc_ids: List[str]
    eligible_fresh_test_pool_count: int
    overlap_verified_zero_doc_ids: bool
    overlap_verified_zero_thread_urls: bool
    final_test_zero_prior_exposure_verified: bool
    train: SplitPartitionMetadata
    val: SplitPartitionMetadata
    final_test: SplitPartitionMetadata
    train_doc_ids: List[str]
    val_doc_ids: List[str]
    final_test_doc_ids: List[str]

