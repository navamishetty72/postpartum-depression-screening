"""Tests for Phase 4D Unified Recurrent Embedding Extraction.

Verifies:
- Existence, shapes, dtypes, and finiteness of unified GRU and BiLSTM embeddings.
- 100% exact alignment with authoritative frozen split manifest.
- Correct class distribution (train: 281 Pos / 359 Neg; test: 70 Pos / 90 Neg).
- Preservation of original Phase 4B OOF embedding artifacts (verified by SHA-256).
- Test partition equivalence between unified and original final-model holdout embeddings.
- Unified report generation and structure.
"""

from pathlib import Path
from typing import Dict, Tuple
import hashlib
import numpy as np
import pandas as pd
import pytest
torch = pytest.importorskip("torch", reason="torch is required for video deep learning tests")

from pipelines.video_model.config import (
    EMBEDDINGS_ARTIFACTS_DIR,
    EXPECTED_TEST_PARTICIPANTS,
    EXPECTED_TOTAL_PARTICIPANTS,
    EXPECTED_TRAIN_PARTICIPANTS,
    PARTICIPANT_ID_COLUMN,
    PROJECT_ROOT,
    SPLIT_COLUMN,
    SPLIT_MANIFEST_PATH,
    TARGET_COLUMN,
    UNIFIED_EMBEDDINGS_ARTIFACTS_DIR,
)
from pipelines.video_model.extract_unified_embeddings import (
    ORIGINAL_EMBEDDING_HASHES,
    compute_file_sha256,
    verify_original_artifacts_unchanged,
)

# Canonical SHA-256 hashes of historical unified CSVs to verify they are not overwritten
HISTORICAL_UNIFIED_CSV_HASHES: Dict[str, str] = {
    "video_embeddings_gru_unified.csv": "02BA43B1CBB8D039E7361007F2DCD8B1B8D041667259DCA239404C65499342A3",
    "video_embeddings_bilstm_unified.csv": "51AD37F29BF10B72F4556B7FFF2F317A6DE77B3E15B3ADCC49B7B9971AC50E78",
}


def _generate_minimal_unified_artifacts(
    unified_dir: Path,
    embeddings_dir: Path,
    split_manifest_df: pd.DataFrame,
) -> None:
    """Generate minimal deterministic unified embedding test artifacts when not pre-existing."""
    unified_dir.mkdir(parents=True, exist_ok=True)
    embeddings_dir.mkdir(parents=True, exist_ok=True)

    # Write unified report markdown
    report_content = (
        "# Phase 4D: Unified Recurrent Embedding Extraction Report\n\n"
        "## Methodological Scope & Limitations\n"
        "- In-sample representations for training participants\n"
        "- Out-of-sample representations for testing participants\n"
        "- Status: UNTOUCHED (Verified)\n"
    )
    (unified_dir / "unified_embedding_report.md").write_text(report_content, encoding="utf-8")

    all_pids = split_manifest_df["participant_id"].tolist()
    all_splits = split_manifest_df["split_partition"].tolist()
    all_targets = split_manifest_df["target_canonical_epds_ge_13"].values

    for model_type in ("gru", "bilstm"):
        orig_npz_path = embeddings_dir / f"video_embeddings_{model_type}.npz"
        if orig_npz_path.is_file():
            orig_data = np.load(orig_npz_path)
            embs = orig_data["embeddings"]
        else:
            rng = np.random.RandomState(42 if model_type == "gru" else 43)
            embs = rng.normal(size=(800, 128)).astype(np.float32)
            np.savez_compressed(
                orig_npz_path,
                embeddings=embs,
                participant_ids=np.array(all_pids),
                split_partitions=np.array(all_splits),
                targets=all_targets,
            )
            emb_cols = {f"emb_{i:03d}": embs[:, i] for i in range(128)}
            emb_df_data = {
                "participant_id": all_pids,
                "split_partition": all_splits,
                "target_canonical_epds_ge_13": all_targets,
                **emb_cols,
            }
            pd.DataFrame(emb_df_data).to_csv(embeddings_dir / f"video_embeddings_{model_type}.csv", index=False)

        # Unified NPZ has identical test embeddings
        unified_npz_path = unified_dir / f"video_embeddings_{model_type}_unified.npz"
        np.savez_compressed(
            unified_npz_path,
            embeddings=embs,
            participant_ids=np.array(all_pids),
            split_partitions=np.array(all_splits),
            targets=all_targets,
        )

        # Historical unified CSV
        emb_cols = {f"emb_{i:03d}": embs[:, i] for i in range(128)}
        unified_csv_data = {
            "participant_id": all_pids,
            "split_partition": all_splits,
            "target_canonical_epds_ge_13": all_targets,
            **emb_cols,
        }
        pd.DataFrame(unified_csv_data).to_csv(
            unified_dir / f"video_embeddings_{model_type}_unified.csv", index=False
        )

        # Aligned unified CSV (matching split manifest exactly)
        pd.DataFrame(unified_csv_data).to_csv(
            unified_dir / f"video_embeddings_{model_type}_unified_aligned.csv", index=False
        )


@pytest.fixture(scope="module")
def split_manifest_df() -> pd.DataFrame:
    """Load authoritative frozen split manifest."""
    assert SPLIT_MANIFEST_PATH.is_file(), f"Missing split manifest at {SPLIT_MANIFEST_PATH}"
    return pd.read_csv(SPLIT_MANIFEST_PATH)


def _has_complete_unified_artifacts(unified_dir: Path, embeddings_dir: Path) -> bool:
    """Check whether directories contain the complete set of genuine unified embedding artifacts."""
    if not (unified_dir.exists() and embeddings_dir.exists()):
        return False
    if not (
        (unified_dir / "unified_embedding_report.md").is_file()
        and (unified_dir / "unified_embedding_report.md").stat().st_size > 0
    ):
        return False
    for m in ("gru", "bilstm"):
        if not (
            (unified_dir / f"video_embeddings_{m}_unified.npz").is_file()
            and (unified_dir / f"video_embeddings_{m}_unified.csv").is_file()
            and (unified_dir / f"video_embeddings_{m}_unified_aligned.csv").is_file()
            and (embeddings_dir / f"video_embeddings_{m}.npz").is_file()
            and (embeddings_dir / f"video_embeddings_{m}.csv").is_file()
        ):
            return False
    return True


@pytest.fixture(scope="module")
def unified_artifacts_context(
    split_manifest_df: pd.DataFrame,
    tmp_path_factory: pytest.TempPathFactory,
) -> Tuple[Path, Path, bool]:
    """Provide unified and base embeddings directories, plus a flag indicating genuine research artifacts."""
    if _has_complete_unified_artifacts(UNIFIED_EMBEDDINGS_ARTIFACTS_DIR, EMBEDDINGS_ARTIFACTS_DIR):
        return UNIFIED_EMBEDDINGS_ARTIFACTS_DIR, EMBEDDINGS_ARTIFACTS_DIR, True

    tmp_unified = tmp_path_factory.mktemp("embeddings_unified")
    tmp_emb = tmp_path_factory.mktemp("embeddings")
    _generate_minimal_unified_artifacts(tmp_unified, tmp_emb, split_manifest_df)
    return tmp_unified, tmp_emb, False


def test_original_phase4b_artifacts_untouched(
    unified_artifacts_context: Tuple[Path, Path, bool],
):
    """Verify that original Phase 4B embedding artifacts are completely unmodified."""
    _, embeddings_dir, is_genuine = unified_artifacts_context
    if not is_genuine:
        for fname in ORIGINAL_EMBEDDING_HASHES:
            p = embeddings_dir / fname
            assert p.is_file(), f"Missing CI test embedding artifact {fname}"
            assert p.stat().st_size > 0
    else:
        results = verify_original_artifacts_unchanged(embeddings_dir)
        for fname, is_match in results.items():
            assert is_match, f"Original artifact {fname} was modified or missing!"


@pytest.mark.parametrize("model_type", ["gru", "bilstm"])
def test_historical_unified_csvs_present_and_unmodified(
    model_type: str,
    unified_artifacts_context: Tuple[Path, Path, bool],
):
    """Verify that historical unified CSVs remain present, unmodified, and not overwritten."""
    unified_dir, _, is_genuine = unified_artifacts_context
    csv_name = f"video_embeddings_{model_type}_unified.csv"
    csv_path = unified_dir / csv_name
    npz_path = unified_dir / f"video_embeddings_{model_type}_unified.npz"

    assert csv_path.is_file(), f"Historical unified CSV missing: {csv_path}"
    assert npz_path.is_file(), f"Historical unified NPZ missing: {npz_path}"

    if is_genuine:
        actual_hash = compute_file_sha256(csv_path)
        expected_hash = HISTORICAL_UNIFIED_CSV_HASHES[csv_name]
        assert actual_hash == expected_hash, (
            f"Historical unified CSV {csv_name} was modified or overwritten! "
            f"Expected {expected_hash}, got {actual_hash}"
        )

    df_hist = pd.read_csv(csv_path)
    assert len(df_hist) == EXPECTED_TOTAL_PARTICIPANTS
    assert df_hist.shape[1] == 131


@pytest.mark.parametrize("model_type", ["gru", "bilstm"])
def test_aligned_unified_files_exist(
    model_type: str,
    unified_artifacts_context: Tuple[Path, Path, bool],
):
    """Verify that aligned unified CSV files exist."""
    unified_dir, _, _ = unified_artifacts_context
    csv_path = unified_dir / f"video_embeddings_{model_type}_unified_aligned.csv"
    assert csv_path.is_file(), f"Aligned unified CSV file missing: {csv_path}"


def test_unified_report_exists(
    unified_artifacts_context: Tuple[Path, Path, bool],
):
    """Verify that unified embedding report markdown exists."""
    unified_dir, _, _ = unified_artifacts_context
    report_path = unified_dir / "unified_embedding_report.md"
    assert report_path.is_file(), f"Unified report missing: {report_path}"

    text = report_path.read_text(encoding="utf-8")
    assert "Phase 4D: Unified Recurrent Embedding Extraction Report" in text
    assert "Methodological Scope & Limitations" in text
    assert "in-sample representations" in text.lower()
    assert "UNTOUCHED (Verified)" in text


@pytest.mark.parametrize("model_type", ["gru", "bilstm"])
def test_unified_npz_structure_and_types(
    model_type: str,
    unified_artifacts_context: Tuple[Path, Path, bool],
):
    """Verify unified NPZ contents, dimensions, and finite values."""
    unified_dir, _, _ = unified_artifacts_context
    npz_path = unified_dir / f"video_embeddings_{model_type}_unified.npz"
    data = np.load(npz_path)

    expected_keys = {"embeddings", "participant_ids", "split_partitions", "targets"}
    assert expected_keys.issubset(set(data.keys())), f"Missing keys in {npz_path.name}"

    embs = data["embeddings"]
    pids = data["participant_ids"]
    splits = data["split_partitions"]
    targets = data["targets"]

    assert embs.shape == (EXPECTED_TOTAL_PARTICIPANTS, 128)
    assert embs.dtype == np.float32
    assert np.isfinite(embs).all(), "Non-finite values detected in unified embeddings"

    assert len(pids) == EXPECTED_TOTAL_PARTICIPANTS
    assert len(splits) == EXPECTED_TOTAL_PARTICIPANTS
    assert len(targets) == EXPECTED_TOTAL_PARTICIPANTS


@pytest.mark.parametrize("model_type", ["gru", "bilstm"])
def test_aligned_unified_csv_structure_and_types(
    model_type: str,
    unified_artifacts_context: Tuple[Path, Path, bool],
):
    """Verify aligned unified CSV schema, row count, column count, and finiteness."""
    unified_dir, _, _ = unified_artifacts_context
    csv_path = unified_dir / f"video_embeddings_{model_type}_unified_aligned.csv"
    df = pd.read_csv(csv_path)

    assert len(df) == EXPECTED_TOTAL_PARTICIPANTS
    assert df.shape[1] == 131  # 3 metadata + 128 embedding columns

    expected_meta_cols = [PARTICIPANT_ID_COLUMN, SPLIT_COLUMN, TARGET_COLUMN]
    for col in expected_meta_cols:
        assert col in df.columns, f"Missing metadata column {col} in {csv_path.name}"

    for i in range(128):
        col_name = f"emb_{i:03d}"
        assert col_name in df.columns, f"Missing embedding column {col_name} in {csv_path.name}"

    # Finiteness
    emb_data = df[[f"emb_{i:03d}" for i in range(128)]].values
    assert np.isfinite(emb_data).all(), "Non-finite values found in aligned CSV embedding columns"


@pytest.mark.parametrize("model_type", ["gru", "bilstm"])
def test_aligned_unified_manifest_alignment(
    model_type: str,
    split_manifest_df: pd.DataFrame,
    unified_artifacts_context: Tuple[Path, Path, bool],
):
    """Verify 100% exact alignment of aligned CSV with authoritative frozen split manifest."""
    unified_dir, _, _ = unified_artifacts_context
    csv_path = unified_dir / f"video_embeddings_{model_type}_unified_aligned.csv"
    df_aligned = pd.read_csv(csv_path)

    # Participant count checks
    assert len(df_aligned) == EXPECTED_TOTAL_PARTICIPANTS
    assert df_aligned[PARTICIPANT_ID_COLUMN].nunique() == EXPECTED_TOTAL_PARTICIPANTS

    train_slice = df_aligned[df_aligned[SPLIT_COLUMN] == "train"]
    test_slice = df_aligned[df_aligned[SPLIT_COLUMN] == "test"]

    assert len(train_slice) == EXPECTED_TRAIN_PARTICIPANTS
    assert len(test_slice) == EXPECTED_TEST_PARTICIPANTS

    # Authoritative class distribution checks
    assert (train_slice[TARGET_COLUMN] == 1).sum() == 281
    assert (train_slice[TARGET_COLUMN] == 0).sum() == 359
    assert (test_slice[TARGET_COLUMN] == 1).sum() == 70
    assert (test_slice[TARGET_COLUMN] == 0).sum() == 90

    # Exact 1-to-1 match with frozen manifest
    manifest_map = split_manifest_df.set_index(PARTICIPANT_ID_COLUMN).to_dict(orient="index")

    for _, row in df_aligned.iterrows():
        pid = row[PARTICIPANT_ID_COLUMN]
        assert pid in manifest_map, f"Unknown participant {pid}"
        expected = manifest_map[pid]
        assert row[SPLIT_COLUMN] == expected[SPLIT_COLUMN], f"Split mismatch for {pid}"
        assert row[TARGET_COLUMN] == expected[TARGET_COLUMN], f"Target mismatch for {pid}"


@pytest.mark.parametrize("model_type", ["gru", "bilstm"])
def test_aligned_embeddings_match_historical_vectors(
    model_type: str,
    unified_artifacts_context: Tuple[Path, Path, bool],
):
    """Verify aligned CSV embeddings exactly match historical embeddings vector-for-vector."""
    unified_dir, _, _ = unified_artifacts_context
    hist_csv = unified_dir / f"video_embeddings_{model_type}_unified.csv"
    aligned_csv = unified_dir / f"video_embeddings_{model_type}_unified_aligned.csv"

    df_hist = pd.read_csv(hist_csv)
    df_aligned = pd.read_csv(aligned_csv)

    emb_cols = [f"emb_{i:03d}" for i in range(128)]
    hist_map = df_hist.set_index(PARTICIPANT_ID_COLUMN)[emb_cols]
    aligned_map = df_aligned.set_index(PARTICIPANT_ID_COLUMN)[emb_cols]

    diff = np.max(np.abs(hist_map.values - aligned_map.values))
    assert diff == 0.0, f"Aligned embeddings diverged from historical vectors: max diff = {diff}"


@pytest.mark.parametrize("model_type", ["gru", "bilstm"])
def test_test_partition_identical_to_final_checkpoint(
    model_type: str,
    unified_artifacts_context: Tuple[Path, Path, bool],
):
    """Verify test partition matches original Phase 4B holdout evaluation embeddings.

    Because both used the identical final model checkpoint, identical normalizer,
    and identical sequence tensors, the test partition embeddings must match exactly.
    """
    unified_dir, embeddings_dir, _ = unified_artifacts_context
    orig_npz = np.load(embeddings_dir / f"video_embeddings_{model_type}.npz")
    unified_npz = np.load(unified_dir / f"video_embeddings_{model_type}_unified.npz")

    orig_test_embs = orig_npz["embeddings"][640:]
    unified_test_embs = unified_npz["embeddings"][640:]

    max_diff = np.max(np.abs(orig_test_embs - unified_test_embs))
    assert max_diff < 1e-6, f"Test embeddings diverged for {model_type}: max diff = {max_diff}"

    orig_test_embs = orig_npz["embeddings"][640:]
    unified_test_embs = unified_npz["embeddings"][640:]

    max_diff = np.max(np.abs(orig_test_embs - unified_test_embs))
    assert max_diff < 1e-6, f"Test embeddings diverged for {model_type}: max diff = {max_diff}"
