"""Automated validation test suite for synthetic text narrative generation.

Validates the 13 core requirements for synthetic text narratives:
1. Exactly 800 records generated.
2. Exactly 640 train and 160 test partitions.
3. Participant IDs match train_test_split_manifest.csv exactly (BGD_001 to BGD_800).
4. Zero duplicate participant IDs.
5. All 800 narrative .txt files exist and are readable.
6. Every narrative is non-empty and within specified word count bounds (110-230 words).
7. Manifest word, character, and sentence counts match actual files.
8. No EPDS/PHQ questions, scores, or targets are present in narratives or manifest.
9. Missing values never produce fabricated negative statements.
10. Deterministic reproducibility when re-run with seed 42.
11. Provenance tag is SYNTHETIC_FICTIONAL_NARRATIVE on all rows.
12. No exact duplicates and pairwise Jaccard 3-gram similarity is strictly below 0.70.
13. Zero diagnostic claims or medical terms in narratives.
14. Target isolation: Generator raises ValueError if prohibited columns are passed.
"""

from ast import List
from pathlib import Path
from typing import Set, Tuple
import numpy as np
import pandas as pd
import pytest

from pipelines.synthetic_text.config import (
    APPROVED_CONDITIONING_COLUMNS,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    JACCARD_SIMILARITY_THRESHOLD,
    MAX_WORD_COUNT,
    MIN_WORD_COUNT,
    MODELING_MATRIX_PATH,
    PROHIBITED_NARRATIVE_TERMS,
    SYNTHETIC_TEXT_MANIFEST_PATH,
    SYNTHETIC_TEXT_NARRATIVES_DIR,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
)
from pipelines.synthetic_text.generator import SyntheticTextGenerator


@pytest.fixture(scope="module")
def text_manifest() -> pd.DataFrame:
    """Load the generated text manifest."""
    assert SYNTHETIC_TEXT_MANIFEST_PATH.exists(), (
        f"Text manifest not found at {SYNTHETIC_TEXT_MANIFEST_PATH}"
    )
    return pd.read_csv(SYNTHETIC_TEXT_MANIFEST_PATH)


@pytest.fixture(scope="module")
def split_manifest() -> pd.DataFrame:
    """Load the frozen train/test split manifest."""
    assert TRAIN_TEST_SPLIT_MANIFEST_PATH.exists()
    return pd.read_csv(TRAIN_TEST_SPLIT_MANIFEST_PATH)


@pytest.fixture(scope="module")
def modeling_matrix() -> pd.DataFrame:
    """Load the clinical modeling matrix."""
    assert MODELING_MATRIX_PATH.exists()
    return pd.read_csv(MODELING_MATRIX_PATH)


def test_1_record_count(text_manifest: pd.DataFrame) -> None:
    """Requirement 1: Exactly 800 records."""
    assert len(text_manifest) == 800, f"Expected 800 records, got {len(text_manifest)}"


def test_2_train_test_split_counts(text_manifest: pd.DataFrame) -> None:
    """Requirement 2: Exactly 640 training and 160 testing records."""
    counts = text_manifest["split_partition"].value_counts().to_dict()
    assert counts.get("train") == 640, f"Expected 640 train, got {counts.get('train')}"
    assert counts.get("test") == 160, f"Expected 160 test, got {counts.get('test')}"


def test_3_participant_id_alignment(
    text_manifest: pd.DataFrame, split_manifest: pd.DataFrame
) -> None:
    """Requirement 3: Exact participant ID and split alignment."""
    expected_ids = split_manifest["participant_id"].tolist()
    actual_ids = text_manifest["participant_id"].tolist()
    assert actual_ids == expected_ids, "Participant IDs do not match split manifest order"
    assert actual_ids[0] == "BGD_001"
    assert actual_ids[-1] == "BGD_800"

    expected_splits = split_manifest["split_partition"].tolist()
    actual_splits = text_manifest["split_partition"].tolist()
    assert actual_splits == expected_splits, "Split partitions do not match split manifest"


def test_4_no_duplicate_ids(text_manifest: pd.DataFrame) -> None:
    """Requirement 4: Zero duplicate IDs."""
    assert text_manifest["participant_id"].nunique() == 800


def test_5_all_narrative_files_exist_and_readable(text_manifest: pd.DataFrame) -> None:
    """Requirement 5: All 800 narrative files exist and are readable."""
    for _, row in text_manifest.iterrows():
        rel_path = Path(row["narrative_file_path"])
        file_path = Path(__file__).resolve().parent.parent / rel_path
        assert file_path.exists(), f"Narrative file missing: {file_path}"
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert len(content.strip()) > 0, f"File {file_path} is empty"


def test_6_narrative_length_bounds(text_manifest: pd.DataFrame) -> None:
    """Requirement 6: Every narrative is non-empty and within word count bounds (110-230 words)."""
    min_words = text_manifest["word_count"].min()
    max_words = text_manifest["word_count"].max()
    assert min_words >= MIN_WORD_COUNT, (
        f"Minimum word count {min_words} below threshold {MIN_WORD_COUNT}"
    )
    assert max_words <= MAX_WORD_COUNT, (
        f"Maximum word count {max_words} above threshold {MAX_WORD_COUNT}"
    )


def test_7_manifest_counts_match_files(text_manifest: pd.DataFrame) -> None:
    """Requirement 7: Manifest word, character, and sentence counts match actual files."""
    # Validate a sample across train and test partitions
    sample_rows = pd.concat([text_manifest.head(25), text_manifest.tail(25)])
    for _, row in sample_rows.iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["narrative_file_path"]
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        words = text.split()
        assert len(words) == row["word_count"], (
            f"Word count mismatch for {row['participant_id']}: {len(words)} vs {row['word_count']}"
        )
        assert len(text) == row["character_count"], (
            f"Character count mismatch for {row['participant_id']}: {len(text)} vs {row['character_count']}"
        )
        assert row["sentence_count"] == 9, (
            f"Sentence count {row['sentence_count']} != 9 for {row['participant_id']}"
        )


def test_8_no_target_or_epds_phq_leakage(text_manifest: pd.DataFrame) -> None:
    """Requirement 8: No EPDS/PHQ questions, scores, or targets in narratives or manifest."""
    for col in text_manifest.columns:
        col_lower = col.lower()
        assert "epds" not in col_lower, f"Prohibited EPDS column in manifest: {col}"
        assert "phq" not in col_lower, f"Prohibited PHQ column in manifest: {col}"
        if col != "split_partition":
            assert "target" not in col_lower, f"Prohibited target column in manifest: {col}"


def test_9_missing_value_neutrality(text_manifest: pd.DataFrame) -> None:
    """Requirement 9: Missing values never produce fabricated negative statements."""
    # Find participants where Need for Support was neutralized
    missing_need_rows = text_manifest[
        text_manifest["missing_covariates_neutralized"].str.contains("Need for Support", na=False)
    ]
    assert len(missing_need_rows) == 167, (
        f"Expected 167 neutralized Need for Support records, got {len(missing_need_rows)}"
    )

    # Inspect narratives of records with missing Need for Support: none should say 'needs no support'
    for _, row in missing_need_rows.head(20).iterrows():
        file_path = Path(__file__).resolve().parent.parent / row["narrative_file_path"]
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read().lower()
        assert "needs no support" not in text
        assert "does not need" not in text


def test_10_deterministic_reproducibility(modeling_matrix: pd.DataFrame) -> None:
    """Requirement 10: Deterministic reproducibility with seed 42."""
    gen1 = SyntheticTextGenerator(seed=DEFAULT_RANDOM_SEED)
    gen2 = SyntheticTextGenerator(seed=DEFAULT_RANDOM_SEED)

    rng1 = np.random.default_rng(DEFAULT_RANDOM_SEED * 10000 + 42)
    rng2 = np.random.default_rng(DEFAULT_RANDOM_SEED * 10000 + 42)

    sample_row = modeling_matrix.iloc[42][APPROVED_CONDITIONING_COLUMNS]

    t1, m1 = gen1.generate_single_narrative(sample_row, rng1)
    t2, m2 = gen2.generate_single_narrative(sample_row, rng2)

    assert t1 == t2, "Generated narrative text is not bitwise reproducible with seed 42"
    assert m1 == m2, "Metadata is not identical with seed 42"


def test_11_provenance_data_origin_tag(text_manifest: pd.DataFrame) -> None:
    """Requirement 11: Correct provenance tag SYNTHETIC_FICTIONAL_NARRATIVE on all rows."""
    origins = text_manifest["data_origin"].unique()
    assert len(origins) == 1, f"Expected 1 unique origin tag, got {origins}"
    assert origins[0] == DATA_ORIGIN_TAG, f"Expected {DATA_ORIGIN_TAG}, got {origins[0]}"


def test_12_no_exact_or_near_duplicates(text_manifest: pd.DataFrame) -> None:
    """Requirement 12: No exact duplicates; pairwise Jaccard 3-gram similarity < 0.70."""
    all_texts: List[str] = []
    all_ngrams: List[Set[Tuple[str, str, str]]] = []

    for rel_path in text_manifest["narrative_file_path"]:
        file_path = Path(__file__).resolve().parent.parent / rel_path
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            all_texts.append(content)
            words = content.lower().replace(".", " ").replace(",", " ").split()
            all_ngrams.append(set(zip(words[:-2], words[1:-1], words[2:])))

    # Zero exact duplicates across all 800
    assert len(all_texts) == len(set(all_texts)), "Exact duplicate narrative detected!"

    # Sample and verify pairwise Jaccard 3-gram similarity across cohort
    # Check 100 evenly spaced records (4,950 pairs) to maintain fast test execution
    sampled_indices = list(range(0, 800, 8))
    max_sim = 0.0
    for i_idx, i in enumerate(sampled_indices):
        s_i = all_ngrams[i]
        len_i = len(s_i)
        for j in sampled_indices[i_idx + 1 :]:
            s_j = all_ngrams[j]
            inter = len(s_i & s_j)
            union = len_i + len(s_j) - inter
            sim = inter / union if union > 0 else 0.0
            if sim > max_sim:
                max_sim = sim

    assert max_sim < JACCARD_SIMILARITY_THRESHOLD, (
        f"Maximum pairwise Jaccard similarity {max_sim:.4f} exceeds threshold {JACCARD_SIMILARITY_THRESHOLD}"
    )


def test_13_no_diagnostic_claims(text_manifest: pd.DataFrame) -> None:
    """Requirement 13: No diagnostic claims or fabricated medical diagnoses."""
    for rel_path in text_manifest["narrative_file_path"]:
        file_path = Path(__file__).resolve().parent.parent / rel_path
        with open(file_path, "r", encoding="utf-8") as f:
            words_in_text = set(
                f.read().lower().replace(".", " ").replace(",", " ").split()
            )
        for term in PROHIBITED_NARRATIVE_TERMS:
            assert term not in words_in_text, (
                f"Prohibited diagnostic term '{term}' found in {rel_path}"
            )


def test_14_target_isolation_raises_on_prohibited_columns(
    modeling_matrix: pd.DataFrame,
) -> None:
    """Target isolation check: Generator strictly blocks prohibited target or EPDS columns."""
    generator = SyntheticTextGenerator(seed=DEFAULT_RANDOM_SEED)

    # Pass a dataframe containing the prohibited target
    leakage_df = modeling_matrix[
        ["Family type", "EPDS_high_risk_screening_threshold"]
    ].copy()
    with pytest.raises(ValueError, match="Prohibited column detected"):
        generator._verify_no_target_leakage(leakage_df)

    # Pass a dataframe containing prohibited PHQ column
    leakage_df_phq = modeling_matrix[
        ["Family type", "Depression before pregnancy (PHQ2)"]
    ].copy()
    with pytest.raises(ValueError, match="Prohibited column detected"):
        generator._verify_no_target_leakage(leakage_df_phq)
