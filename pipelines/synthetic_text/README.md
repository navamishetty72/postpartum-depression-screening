# Synthetic Text Narrative Pipeline

## Scientific Framework & Modality Disclaimer
> [!IMPORTANT]
> **Architectural Benchmark Only:** The Bangladeshi clinical survey cohort contains **zero qualitative interview transcripts, clinical intake notes, or recorded patient dialogues**.
> The narratives generated in this pipeline are **fictional synthetic contextual vignettes** conditioned on non-target demographic and domestic survey covariates. They exist solely to benchmark text NLP feature extractors and downstream multimodal late fusion combiner architectures.
> - **Fictional Context:** All narratives are fictional and do not represent actual patient statements or authentic patient interviews.
> - **Computational Linkage:** Clinical linkage to participant IDs (`BGD_001`–`BGD_800`) is constructed computationally, not an observed multimodal record.
> - **Language Representation:** Narratives are generated in English for benchmark compatibility and do **not** represent validated Bengali postpartum language patterns.
> - **Zero Clinical Validity:** The output is intended strictly for architectural software testing and cannot validate real-world clinical diagnostic efficacy.

## Pipeline Architecture
- `config.py`: File paths, approved non-target conditioning columns, length boundaries, and strict target leakage rules.
- `templates.py`: High-entropy combinatorial template libraries organized into 3 thematic sections (Household & Daily Routine, Infant Care & Responsibilities, Sleep & Support).
- `generator.py`: `SyntheticTextGenerator` engine with deterministic seeding, missingness neutralization, diagnostic term validation, and file/manifest export.
- `__init__.py`: Package interface exports.

## Generated Outputs
Outputs are saved to `data/synthetic/text/` (excluded from Git tracking via `.gitignore`):
- `text_manifest.csv`: 800 participant records (640 train, 160 test) linked to `BGD_001`–`BGD_800`, containing:
  - `participant_id`
  - `split_partition` (`train` / `test`)
  - `data_origin` (`SYNTHETIC_FICTIONAL_NARRATIVE`)
  - `generator_version` (`1.0.0`)
  - `random_seed` (`42`)
  - `narrative_file_path` (`data/synthetic/text/narratives/BGD_xxx.txt`)
  - `word_count`, `character_count`, `sentence_count`
  - `language` (`en`)
  - `conditioning_variables_used`
  - `missing_covariates_neutralized`
- `narratives/`: 800 plain-text UTF-8 files (`BGD_001.txt` to `BGD_800.txt`).

## Execution & Verification
To regenerate the synthetic text cohort:
```bash
python -m pipelines.synthetic_text.generator
```

To run the automated validation test suite:
```bash
pytest tests/test_synthetic_text.py -v
```
All 14 automated checks verify participant ID alignment, split distribution, word count bounds (110–230 words), zero target leakage, missing value neutrality, zero exact duplicates, pairwise Jaccard 3-gram similarity $< 0.70$, zero diagnostic terms, and provenance integrity.
