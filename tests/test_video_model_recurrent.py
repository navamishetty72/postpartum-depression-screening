"""Automated unit and integration test suite for recurrent video models (Phase 4B).

Validates:
1. Fold-level train/validation separation and zero leakage.
2. Training-only normalization fitted strictly within each fold.
3. Early stopping mechanism and best checkpoint recovery.
4. Checkpoint saving, serialization, and weight restoration.
5. Deterministic reproducibility across repeated training runs with fixed random seeds.
6. Complete out-of-fold prediction coverage across all 640 training participants.
7. Holdout isolation: test participants (160) are completely disjoint from CV training data.
8. 128-dimensional participant embedding dimensions and schema.
9. Zero duplicate or missing participant IDs in predictions and embeddings.
10. Finite model outputs, zero NaNs, and non-zero gradient flow across all trainable weights.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple
import copy
import numpy as np
import pandas as pd
import pytest
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from pipelines.video_model.config import (
    DEFAULT_RANDOM_SEED,
    EMBEDDINGS_ARTIFACTS_DIR,
    EXPECTED_TEST_PARTICIPANTS,
    EXPECTED_TOTAL_PARTICIPANTS,
    EXPECTED_TRAIN_PARTICIPANTS,
    FEATURE_DIM,
    RECURRENT_ARTIFACTS_DIR,
)
from pipelines.video_model.dataset import PPDVideoDataset
from pipelines.video_model.evaluate_recurrent import (
    evaluate_model,
    extract_embeddings_only,
)
from pipelines.video_model.models.bilstm_model import VideoBiLSTMModel
from pipelines.video_model.models.gru_model import VideoGRUModel
from pipelines.video_model.preprocessing import (
    VideoFeatureNormalizer,
    get_stratified_cv_splits,
    pad_collate_fn,
)
from pipelines.video_model.train_recurrent import (
    InMemoryVideoDataset,
    create_model_instance,
    train_single_fold,
)


@pytest.fixture(scope="module")
def train_dataset() -> PPDVideoDataset:
    return PPDVideoDataset(partition="train", validate_on_init=False)


@pytest.fixture(scope="module")
def test_dataset() -> PPDVideoDataset:
    return PPDVideoDataset(partition="test", validate_on_init=False)


# ==============================================================================
# 1. Fold Separation & Zero Leakage
# ==============================================================================
def test_recurrent_fold_separation_and_leakage_isolation(train_dataset: PPDVideoDataset) -> None:
    """Requirement: 5-fold CV splits have zero overlap between train and validation indices."""
    splits = get_stratified_cv_splits(train_dataset, n_splits=5, seed=42)
    assert len(splits) == 5

    all_val_indices: List[int] = []
    for train_idx, val_idx in splits:
        train_set = set(train_idx)
        val_set = set(val_idx)

        assert train_set.isdisjoint(val_set)
        assert len(train_set) + len(val_set) == EXPECTED_TRAIN_PARTICIPANTS
        all_val_indices.extend(val_idx.tolist())

    assert sorted(all_val_indices) == list(range(EXPECTED_TRAIN_PARTICIPANTS))
    assert len(set(all_val_indices)) == EXPECTED_TRAIN_PARTICIPANTS


# ==============================================================================
# 2. Training-Only Normalization
# ==============================================================================
def test_recurrent_training_only_normalization() -> None:
    """Requirement: Normalizer fitted on training fold data does not see validation tensors."""
    np.random.seed(42)
    train_raw = [np.random.normal(loc=5.0, scale=1.0, size=(50, 24)).astype(np.float32) for _ in range(8)]
    val_raw = [np.random.normal(loc=100.0, scale=1.0, size=(50, 24)).astype(np.float32) for _ in range(4)]

    for arr in train_raw + val_raw:
        arr[:, 22] = 0.90
        arr[:, 23] = 1.0

    normalizer = VideoFeatureNormalizer().fit(train_raw)
    # Mean of normalizer must reflect train_raw (~5.0), not val_raw (~100.0)
    for ch in range(22):
        assert normalizer.mean_[ch] < 15.0

    # Ensure transforming validation data does not modify normalizer statistics
    mean_before = normalizer.mean_.copy()
    _ = normalizer.transform(val_raw[0])
    assert np.allclose(normalizer.mean_, mean_before)


# ==============================================================================
# 3. Early Stopping & Checkpoint Loading
# ==============================================================================
def test_recurrent_early_stopping_and_checkpoint_loading(tmp_path: Path) -> None:
    """Requirement: Early stopping stops training before max_epochs when val loss stagnates, and restores best weights."""
    torch.manual_seed(42)
    np.random.seed(42)

    train_feats = [np.random.randn(45, 24).astype(np.float32) for _ in range(16)]
    val_feats = [np.random.randn(45, 24).astype(np.float32) for _ in range(8)]
    for a in train_feats + val_feats:
        a[:, 22] = 0.85
        a[:, 23] = 1.0

    train_ds = InMemoryVideoDataset(train_feats, [0, 1] * 8, [f"TR_{i}" for i in range(16)])
    val_ds = InMemoryVideoDataset(val_feats, [0, 1] * 4, [f"VAL_{i}" for i in range(8)])

    train_loader = DataLoader(train_ds, batch_size=8, shuffle=True, collate_fn=pad_collate_fn)
    val_loader = DataLoader(val_ds, batch_size=8, shuffle=False, collate_fn=pad_collate_fn)

    model = VideoGRUModel(input_dim=24, hidden_dim=32, embedding_dim=128)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    model, best_ep, hist = train_single_fold(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        criterion=criterion,
        optimizer=optimizer,
        max_epochs=20,
        patience=3,
        grad_clip=1.0,
    )

    # Must have stopped before max_epochs=20 due to patience=3
    assert len(hist["train_loss"]) < 20
    assert 1 <= best_ep <= len(hist["train_loss"])

    # Test checkpoint saving and bitwise restoration
    ckpt_file = tmp_path / "model_ckpt.pt"
    torch.save({"state_dict": model.state_dict(), "best_epoch": best_ep}, ckpt_file)

    loaded_model = VideoGRUModel(input_dim=24, hidden_dim=32, embedding_dim=128)
    ckpt = torch.load(ckpt_file)
    loaded_model.load_state_dict(ckpt["state_dict"])

    for p1, p2 in zip(model.parameters(), loaded_model.parameters()):
        assert torch.equal(p1, p2)


# ==============================================================================
# 4. Deterministic Reproducibility
# ==============================================================================
def test_recurrent_reproducibility() -> None:
    """Requirement: Fixed random seeds yield identical training loss and model parameters."""
    def run_trial(seed: int) -> Tuple[float, torch.Tensor]:
        torch.manual_seed(seed)
        np.random.seed(seed)
        feats = [np.random.randn(45, 24).astype(np.float32) for _ in range(8)]
        for a in feats:
            a[:, 22] = 0.90
            a[:, 23] = 1.0

        ds = InMemoryVideoDataset(feats, [0, 1] * 4, [f"P_{i}" for i in range(8)])
        loader = DataLoader(ds, batch_size=4, shuffle=False, collate_fn=pad_collate_fn)

        model = VideoGRUModel(input_dim=24, hidden_dim=32, embedding_dim=128)
        crit = nn.BCEWithLogitsLoss()
        opt = torch.optim.AdamW(model.parameters(), lr=1e-3)

        model.train()
        batch = next(iter(loader))
        opt.zero_grad()
        logits = model(batch["features"], batch["padding_mask"], batch["tracking_mask"]).squeeze(-1)
        loss = crit(logits, batch["targets"].float())
        loss.backward()
        opt.step()

        first_weight = next(model.parameters()).clone().detach()
        return float(loss.item()), first_weight

    loss1, w1 = run_trial(seed=42)
    loss2, w2 = run_trial(seed=42)

    assert abs(loss1 - loss2) < 1e-6
    assert torch.allclose(w1, w2, atol=1e-6)


# ==============================================================================
# 5. Finite Outputs, Loss, and Non-Zero Gradients
# ==============================================================================
def test_recurrent_finite_outputs_and_gradients() -> None:
    """Requirement: Recurrent models produce finite logits and non-zero gradients under padding and tracking masks."""
    for model_cls in (VideoGRUModel, VideoBiLSTMModel):
        torch.manual_seed(42)
        model = model_cls(input_dim=FEATURE_DIM, hidden_dim=64, embedding_dim=128, num_classes=1)

        B, T = 4, 60
        features = torch.randn(B, T, FEATURE_DIM, requires_grad=True)
        padding_mask = torch.ones((B, T), dtype=torch.bool)
        padding_mask[:, 45:] = False  # Padded tail
        tracking_mask = torch.ones((B, T), dtype=torch.bool)
        tracking_mask[:, 20:25] = False  # Untracked gap

        targets = torch.tensor([1.0, 0.0, 1.0, 0.0], dtype=torch.float32)

        out = model(features, padding_mask=padding_mask, tracking_mask=tracking_mask, return_embedding=True)
        logits = out["logits"].squeeze(-1)
        emb = out["embedding"]

        assert logits.shape == (B,)
        assert emb.shape == (B, 128)
        assert not torch.isnan(logits).any()
        assert not torch.isnan(emb).any()
        assert not torch.isinf(logits).any()
        assert not torch.isinf(emb).any()

        criterion = nn.BCEWithLogitsLoss()
        loss = criterion(logits, targets)
        loss.backward()

        for name, param in model.named_parameters():
            if param.requires_grad:
                assert param.grad is not None, f"Gradient missing for {name}"
                assert not torch.isnan(param.grad).any(), f"NaN gradient in {name}"
                assert param.grad.abs().sum() > 0.0, f"Zero gradient in {name}"


# ==============================================================================
# 6. Embedding Extraction Schema
# ==============================================================================
def test_embedding_extraction_schema(train_dataset: PPDVideoDataset) -> None:
    """Requirement: extract_embeddings_only produces exactly (N, 128) float32 embeddings."""
    model = VideoGRUModel(input_dim=24, hidden_dim=64, embedding_dim=128)
    loader = DataLoader(
        InMemoryVideoDataset(
            features_list=train_dataset.get_all_raw_tensors()[:10],
            targets=train_dataset.get_targets()[:10],
            participant_ids=train_dataset.get_participant_ids()[:10],
        ),
        batch_size=4,
        shuffle=False,
        collate_fn=pad_collate_fn,
    )

    embs, pids, targets = extract_embeddings_only(model, loader, device="cpu")

    assert embs.shape == (10, 128)
    assert embs.dtype == np.float32
    assert len(pids) == 10
    assert len(targets) == 10
    assert not np.isnan(embs).any()
    assert not np.isinf(embs).any()


# ==============================================================================
# 7. Saved Recurrent Artifacts and Embeddings Integrity
# ==============================================================================
def test_saved_recurrent_artifacts_and_embeddings() -> None:
    """Requirement: All checkpoints, predictions, metrics, and fusion embeddings exist and are valid."""
    assert RECURRENT_ARTIFACTS_DIR.exists()
    assert EMBEDDINGS_ARTIFACTS_DIR.exists()

    # Required JSON and Markdown files
    for fname in (
        "recurrent_config.json",
        "recurrent_cv_results.json",
        "recurrent_holdout_results.json",
        "recurrent_experiment_report.md",
    ):
        p = RECURRENT_ARTIFACTS_DIR / fname
        assert p.is_file(), f"Missing {fname} in recurrent artifacts"
        assert p.stat().st_size > 0

    # Model checkpoints and predictions
    for m_type in ("gru", "bilstm"):
        # 5 fold checkpoints + 1 final checkpoint
        for fold in range(5):
            ckpt = RECURRENT_ARTIFACTS_DIR / f"{m_type}_fold_{fold}.pt"
            assert ckpt.is_file(), f"Missing {ckpt}"

        final_ckpt = RECURRENT_ARTIFACTS_DIR / f"{m_type}_final.pt"
        assert final_ckpt.is_file(), f"Missing {final_ckpt}"

        # OOF predictions
        oof_p = RECURRENT_ARTIFACTS_DIR / f"oof_predictions_{m_type}.csv"
        assert oof_p.is_file(), f"Missing {oof_p}"
        df_oof = pd.read_csv(oof_p)
        assert len(df_oof) == EXPECTED_TRAIN_PARTICIPANTS == 640
        assert df_oof["participant_id"].nunique() == 640
        assert (df_oof["predicted_probability"] >= 0.0).all() and (df_oof["predicted_probability"] <= 1.0).all()

        # Holdout predictions
        holdout_p = RECURRENT_ARTIFACTS_DIR / f"holdout_predictions_{m_type}.csv"
        assert holdout_p.is_file(), f"Missing {holdout_p}"
        df_holdout = pd.read_csv(holdout_p)
        assert len(df_holdout) == EXPECTED_TEST_PARTICIPANTS == 160
        assert df_holdout["participant_id"].nunique() == 160
        assert df_holdout["true_target"].value_counts().to_dict() == {0: 90, 1: 70}

        # Embeddings NPZ and CSV
        npz_p = EMBEDDINGS_ARTIFACTS_DIR / f"video_embeddings_{m_type}.npz"
        csv_p = EMBEDDINGS_ARTIFACTS_DIR / f"video_embeddings_{m_type}.csv"
        assert npz_p.is_file(), f"Missing {npz_p}"
        assert csv_p.is_file(), f"Missing {csv_p}"

        npz_data = np.load(npz_p)
        assert npz_data["embeddings"].shape == (EXPECTED_TOTAL_PARTICIPANTS, 128)
        assert len(npz_data["participant_ids"]) == EXPECTED_TOTAL_PARTICIPANTS
        assert len(set(npz_data["participant_ids"])) == EXPECTED_TOTAL_PARTICIPANTS
        assert not np.isnan(npz_data["embeddings"]).any()
        assert not np.isinf(npz_data["embeddings"]).any()

        df_emb = pd.read_csv(csv_p)
        assert len(df_emb) == EXPECTED_TOTAL_PARTICIPANTS == 800
        assert df_emb["participant_id"].nunique() == 800
        assert "emb_000" in df_emb.columns and "emb_127" in df_emb.columns
        assert df_emb["split_partition"].value_counts().to_dict() == {"train": 640, "test": 160}
        assert df_emb["target_canonical_epds_ge_13"].value_counts().to_dict() == {0: 449, 1: 351}

