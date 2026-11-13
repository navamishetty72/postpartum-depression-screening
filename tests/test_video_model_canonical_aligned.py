"""Automated test suite for canonical-aligned BiLSTM video screening artifacts.

Verifies:
1. All canonical-aligned artifacts exist under artifacts/video_model/canonical_aligned/.
2. Exact participant ID and target match with data/processed/Numerical/train_test_split_manifest.csv.
3. 5-fold cross-validation allocation (exactly 128 participants per fold across 640 training participants).
4. Frozen holdout isolation (160 test participants, 0 overlap with training).
5. Valid probability outputs within [0.0, 1.0] with zero null or infinite values.
6. PyTorch checkpoint validity and non-NaN weight tensors.
7. 128-dimensional participant embedding integrity.
8. Full 4-modality prediction alignment across Clinical, Audio, Text, and Video.
9. Absolute preservation of historical Phase 4B recurrent artifacts.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
torch = pytest.importorskip("torch", reason="torch is required for video deep learning tests")

from pipelines.video_model.config import (
    EXPECTED_TEST_PARTICIPANTS,
    EXPECTED_TOTAL_PARTICIPANTS,
    EXPECTED_TRAIN_PARTICIPANTS,
    PROJECT_ROOT,
    SPLIT_MANIFEST_PATH,
    TARGET_COLUMN,
)
from pipelines.video_model.models.bilstm_model import VideoBiLSTMModel

CANONICAL_DIR = PROJECT_ROOT / "artifacts" / "video_model" / "canonical_aligned"
HISTORICAL_DIR = PROJECT_ROOT / "artifacts" / "video_model" / "recurrent"

if not (CANONICAL_DIR / "bilstm_final.pt").is_file() or not (CANONICAL_DIR / "oof_predictions_bilstm.csv").is_file():
    pytest.skip(
        "Canonical aligned BiLSTM model artifacts not present (requires running pipelines/video_model/train_canonical_aligned.py)",
        allow_module_level=True,
    )


def test_canonical_aligned_artifacts_exist():
    """Verify that all required canonical-aligned artifacts exist."""
    assert CANONICAL_DIR.is_dir(), f"Directory missing: {CANONICAL_DIR}"

    expected_files = [
        "bilstm_final.pt",
        "bilstm_fold_0.pt",
        "bilstm_fold_1.pt",
        "bilstm_fold_2.pt",
        "bilstm_fold_3.pt",
        "bilstm_fold_4.pt",
        "config.json",
        "oof_predictions_bilstm.csv",
        "holdout_predictions_bilstm.csv",
        "video_embeddings_bilstm.npz",
        "video_embeddings_bilstm.csv",
        "metrics_summary.json",
        "training_report.md",
    ]
    for fname in expected_files:
        fpath = CANONICAL_DIR / fname
        assert fpath.is_file(), f"Missing artifact: {fname}"
        assert fpath.stat().st_size > 0, f"Artifact is empty: {fname}"


def test_oof_predictions_schema_and_distribution():
    """Verify OOF predictions match canonical training manifest and constraints."""
    oof_path = CANONICAL_DIR / "oof_predictions_bilstm.csv"
    df_oof = pd.read_csv(oof_path)

    split_df = pd.read_csv(SPLIT_MANIFEST_PATH)
    train_manifest = split_df[split_df["split_partition"] == "train"].reset_index(drop=True)

    assert len(df_oof) == EXPECTED_TRAIN_PARTICIPANTS
    assert list(df_oof.columns) == [
        "participant_id",
        "fold",
        "true_target",
        "predicted_label",
        "predicted_probability",
    ]

    # Exact participant ID matching and ordering
    assert (df_oof["participant_id"] == train_manifest["participant_id"]).all()

    # Exact target label matching
    assert (df_oof["true_target"] == train_manifest[TARGET_COLUMN]).all()

    # Probability bounds and finiteness
    assert not df_oof["predicted_probability"].isna().any()
    assert (df_oof["predicted_probability"] >= 0.0).all()
    assert (df_oof["predicted_probability"] <= 1.0).all()

    # Binary prediction validity
    assert set(df_oof["predicted_label"].unique()).issubset({0, 1})

    # Exactly 5 folds with 128 participants each
    fold_counts = df_oof["fold"].value_counts().to_dict()
    assert set(fold_counts.keys()) == {0, 1, 2, 3, 4}
    for fold, count in fold_counts.items():
        assert count == 128, f"Fold {fold} has {count} samples, expected 128"


def test_holdout_predictions_schema_and_distribution():
    """Verify holdout predictions match canonical test manifest and constraints."""
    holdout_path = CANONICAL_DIR / "holdout_predictions_bilstm.csv"
    df_holdout = pd.read_csv(holdout_path)

    split_df = pd.read_csv(SPLIT_MANIFEST_PATH)
    test_manifest = split_df[split_df["split_partition"] == "test"].reset_index(drop=True)

    assert len(df_holdout) == EXPECTED_TEST_PARTICIPANTS
    assert list(df_holdout.columns) == [
        "participant_id",
        "true_target",
        "predicted_label",
        "predicted_probability",
    ]

    # Exact participant ID matching and ordering
    assert (df_holdout["participant_id"] == test_manifest["participant_id"]).all()

    # Exact target label matching
    assert (df_holdout["true_target"] == test_manifest[TARGET_COLUMN]).all()

    # Probability bounds and finiteness
    assert not df_holdout["predicted_probability"].isna().any()
    assert (df_holdout["predicted_probability"] >= 0.0).all()
    assert (df_holdout["predicted_probability"] <= 1.0).all()

    # Binary prediction validity
    assert set(df_holdout["predicted_label"].unique()).issubset({0, 1})


def test_zero_train_test_overlap():
    """Verify zero participant overlap between OOF and holdout predictions."""
    df_oof = pd.read_csv(CANONICAL_DIR / "oof_predictions_bilstm.csv")
    df_holdout = pd.read_csv(CANONICAL_DIR / "holdout_predictions_bilstm.csv")

    train_pids = set(df_oof["participant_id"])
    test_pids = set(df_holdout["participant_id"])

    assert len(train_pids.intersection(test_pids)) == 0
    assert len(train_pids.union(test_pids)) == EXPECTED_TOTAL_PARTICIPANTS


def test_checkpoints_integrity():
    """Verify that saved PyTorch checkpoints can be loaded and contain valid weights."""
    ckpt_files = [CANONICAL_DIR / f"bilstm_fold_{i}.pt" for i in range(5)]
    ckpt_files.append(CANONICAL_DIR / "bilstm_final.pt")

    for ckpt_path in ckpt_files:
        data = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        assert "state_dict" in data
        state_dict = data["state_dict"]

        model = VideoBiLSTMModel(hidden_dim=64, embedding_dim=128)
        model.load_state_dict(state_dict)

        for param in model.parameters():
            assert not torch.isnan(param).any()
            assert not torch.isinf(param).any()


def test_embeddings_integrity():
    """Verify participant embeddings matrix dimensions and alignment."""
    npz_path = CANONICAL_DIR / "video_embeddings_bilstm.npz"
    csv_path = CANONICAL_DIR / "video_embeddings_bilstm.csv"

    npz_data = np.load(npz_path)
    embeddings = npz_data["embeddings"]
    pids = npz_data["participant_ids"]
    splits = npz_data["split_partitions"]
    targets = npz_data["targets"]

    assert embeddings.shape == (EXPECTED_TOTAL_PARTICIPANTS, 128)
    assert len(pids) == EXPECTED_TOTAL_PARTICIPANTS
    assert len(splits) == EXPECTED_TOTAL_PARTICIPANTS
    assert len(targets) == EXPECTED_TOTAL_PARTICIPANTS

    df_emb = pd.read_csv(csv_path)
    assert len(df_emb) == EXPECTED_TOTAL_PARTICIPANTS
    assert "participant_id" in df_emb.columns
    assert "target_canonical_epds_ge_13" in df_emb.columns
    assert len([c for c in df_emb.columns if c.startswith("emb_")]) == 128


def test_four_modality_alignment():
    """Verify exact alignment of participant IDs and targets across all 4 modalities."""
    clin_oof = pd.read_csv(PROJECT_ROOT / "models" / "clinical_numerical" / "oof_predictions.csv")
    clin_test = pd.read_csv(PROJECT_ROOT / "models" / "clinical_numerical" / "test_predictions.csv")

    audio_oof = pd.read_csv(PROJECT_ROOT / "models" / "audio_model" / "oof_predictions.csv")
    audio_test = pd.read_csv(PROJECT_ROOT / "models" / "audio_model" / "test_predictions.csv")

    text_oof = pd.read_csv(PROJECT_ROOT / "models" / "text_model" / "oof_predictions.csv")
    text_test = pd.read_csv(PROJECT_ROOT / "models" / "text_model" / "test_predictions.csv")

    video_oof = pd.read_csv(CANONICAL_DIR / "oof_predictions_bilstm.csv")
    video_test = pd.read_csv(CANONICAL_DIR / "holdout_predictions_bilstm.csv")

    # OOF Equality
    assert (clin_oof["participant_id"] == audio_oof["participant_id"]).all()
    assert (audio_oof["participant_id"] == text_oof["participant_id"]).all()
    assert (text_oof["participant_id"] == video_oof["participant_id"]).all()

    assert (clin_oof["y_true"] == audio_oof["true_target"]).all()
    assert (audio_oof["true_target"] == text_oof["true_target"]).all()
    assert (text_oof["true_target"] == video_oof["true_target"]).all()

    # Holdout Equality
    assert (clin_test["participant_id"] == audio_test["participant_id"]).all()
    assert (audio_test["participant_id"] == text_test["participant_id"]).all()
    assert (text_test["participant_id"] == video_test["participant_id"]).all()

    assert (clin_test["y_true"] == audio_test["true_target"]).all()
    assert (audio_test["true_target"] == text_test["true_target"]).all()
    assert (text_test["true_target"] == video_test["true_target"]).all()


def test_historical_recurrent_artifacts_preserved():
    """Verify that historical Phase 4B recurrent artifacts remain intact."""
    assert HISTORICAL_DIR.is_dir()
    for fname in ["bilstm_final.pt", "oof_predictions_bilstm.csv", "holdout_predictions_bilstm.csv"]:
        fpath = HISTORICAL_DIR / fname
        assert fpath.is_file()
        assert fpath.stat().st_size > 0

