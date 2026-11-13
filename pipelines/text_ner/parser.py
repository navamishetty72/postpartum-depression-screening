"""Brat annotation parser for Postpartum Depression (PPD) Named Entity Dataset.

Parses .ann and .txt pairs into strongly typed Document and EntitySpan dataclasses.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import zipfile


@dataclass
class EntitySpan:
    """Represents a text-bound entity span parsed from Brat .ann format."""

    id: str
    label: str
    start: int
    end: int
    text: str
    semantic_types: List[str] = field(default_factory=list)
    concept_ids: List[str] = field(default_factory=list)

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass
class Document:
    """Represents an annotated forum thread document."""

    id: str
    group: str
    text: str
    spans: List[EntitySpan] = field(default_factory=list)


def parse_ann_content(ann_text: str) -> List[EntitySpan]:
    """Parse raw Brat .ann text into a list of EntitySpan objects.

    Handles T-lines (text-bound entity spans) and N-lines (normalizations/attributes).
    """
    spans_by_id: Dict[str, EntitySpan] = {}
    n_refs: Dict[str, Dict[str, List[str]]] = {}

    for line in ann_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if not parts:
            continue

        tag = parts[0]
        # Text-bound entity: T1 \t MMLite 8740 8761 \t postpartum depression
        if tag.startswith("T"):
            if len(parts) < 3:
                continue
            tid = tag
            meta_parts = parts[1].split()
            if len(meta_parts) < 3:
                continue
            label = meta_parts[0]
            try:
                start = int(meta_parts[1])
                # In case of semicolon-separated discontinuous spans, take first end
                end_str = meta_parts[2].split(";")[0]
                end = int(end_str)
            except ValueError:
                continue

            span_text = parts[2]
            spans_by_id[tid] = EntitySpan(
                id=tid,
                label=label,
                start=start,
                end=end,
                text=span_text,
                semantic_types=[],
                concept_ids=[],
            )

        # Normalization / reference line: N1 \t Reference T1 SemanticType:mobd \t mobd
        elif tag.startswith("N") or tag.startswith("n"):
            if len(parts) < 2:
                continue
            ref_info = parts[1].split()
            # Expecting: Reference T<id> Key:Value
            if len(ref_info) >= 3 and ref_info[0].lower() == "reference":
                target_tid = ref_info[1]
                for item in ref_info[2:]:
                    if ":" in item:
                        k, v = item.split(":", 1)
                        if target_tid not in n_refs:
                            n_refs[target_tid] = {"SemanticType": [], "ConceptId": []}
                        if k in n_refs[target_tid]:
                            n_refs[target_tid][k].append(v)

    # Attach normalizations to spans
    for tid, span in spans_by_id.items():
        if tid in n_refs:
            span.semantic_types = n_refs[tid].get("SemanticType", [])
            span.concept_ids = n_refs[tid].get("ConceptId", [])

    return list(spans_by_id.values())


def load_corpus_from_zips(corpus_root: Path) -> List[Document]:
    """Iterate over all subdirectories and zip archives to load the full corpus."""
    docs: List[Document] = []
    if not corpus_root.exists():
        return docs

    for group_dir in sorted(corpus_root.iterdir()):
        if not group_dir.is_dir():
            continue
        group_name = group_dir.name

        text_zips = [f for f in group_dir.iterdir() if "text" in f.name.lower() and f.suffix == ".zip"]
        ann_zips = [f for f in group_dir.iterdir() if "ann" in f.name.lower() and f.suffix == ".zip"]

        if not text_zips or not ann_zips:
            continue

        with zipfile.ZipFile(text_zips[0]) as zt, zipfile.ZipFile(ann_zips[0]) as za:
            txt_map = {
                Path(name).stem: name
                for name in zt.namelist()
                if name.endswith(".txt") and not Path(name).name.startswith("~$")
            }
            ann_map = {
                Path(name).stem: name
                for name in za.namelist()
                if name.endswith(".ann") and not Path(name).name.startswith("~$")
            }

            common_ids = sorted(set(txt_map.keys()) & set(ann_map.keys()))
            for doc_id in common_ids:
                try:
                    raw_txt = zt.read(txt_map[doc_id]).decode("utf-8", errors="replace")
                    raw_ann = za.read(ann_map[doc_id]).decode("utf-8", errors="replace")
                    spans = parse_ann_content(raw_ann)
                    docs.append(Document(id=doc_id, group=group_name, text=raw_txt, spans=spans))
                except Exception:
                    continue

    return docs

