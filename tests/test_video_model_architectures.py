"""Automated unit and integration test suite for video model architectures.

Validates the core contracts of Phase 3:
1. Temporal pooling modules (mean, max, mean_max, attention) with mask guarantees and zero-valid safety.
2. Lightweight GRU model (encoder, 128-dim embedding, binary head, return_embedding flag).
3. Lightweight BiLSTM model (encoder, 128-dim embedding, binary head, return_embedding flag).
4. Decoupled SSL embedding extraction interface.
5. Backpropagation and non-zero gradient flow across all trainable parameters.
6. Variable sequence lengths (45 <= T <= 120) and batch size 1 support.
7. Degraded sequence handling (100% untracked frames produce finite zero-NaN outputs).
8. Participant statistical feature extractor (exactly 220 features, no NaNs/Infs).
9. Logistic Regression and Random Forest baseline classifiers.
10. End-to-end integration with PPDVideoDataset and pad_collate_fn.
"""

from typing import Dict, List
import numpy as np
import pytest
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from pipelines.video_model.config import FEATURE_DIM
from pipelines.video_model.dataset import PPDVideoDataset
from pipelines.video_model.models import (
    MaskedAttentionPooling,
    MaskedTemporalPooling,
    ParticipantStatisticalFeatureExtractor,
    VideoBiLSTMEncoder,
    VideoBiLSTMModel,
    VideoGRUEncoder,
    VideoGRUModel,
    VideoLogisticRegressionBaseline,
    VideoRandomForestBaseline,
)
from pipelines.video_model.preprocessing import VideoFeatureNormalizer, pad_collate_fn


# ==============================================================================
# 1. Temporal Pooling Tests
# ==============================================================================
@pytest.mark.parametrize("method,multiplier", [
    ("mean", 1),
    ("max", 1),
    ("mean_max", 2),
    ("attention", 1),
])
def test_masked_temporal_pooling_modes(method: str, multiplier: int) -> None:
    """Requirement: Temporal pooling methods produce exact expected dimensions and finite outputs."""
    B, T, D = 4, 60, 64
    features = torch.randn(B, T, D)
    mask = torch.ones((B, T), dtype=torch.bool)
    # Mask out last 10 frames of each sequence
    mask[:, 50:] = False

    pooler = MaskedTemporalPooling(method=method, input_dim=D)
    pooled = pooler(features, mask=mask)

    assert pooled.shape == (B, D * multiplier)
    assert not torch.isnan(pooled).any()
    assert not torch.isinf(pooled).any()


def test_masked_temporal_pooling_zero_valid_frames() -> None:
    """Requirement: Sequences with 0 valid frames return finite values without NaNs or Infs."""
    B, T, D = 3, 50, 32
    features = torch.randn(B, T, D)
    # Sequence 0 has normal frames, Sequence 1 has all frames masked, Sequence 2 has 1 valid frame
    mask = torch.zeros((B, T), dtype=torch.bool)
    mask[0, :30] = True
    mask[1, :] = False  # Completely invalid
    mask[2, 0] = True

    for method in ("mean", "max", "mean_max", "attention"):
        pooler = MaskedTemporalPooling(method=method, input_dim=D)
        pooled = pooler(features, mask=mask)

        assert pooled.shape[0] == B
        assert not torch.isnan(pooled).any(), f"NaN detected in {method} pooling with 0 valid frames"
        assert not torch.isinf(pooled).any(), f"Inf detected in {method} pooling with 0 valid frames"
        # The all-masked sequence should output zeros
        assert torch.all(pooled[1] == 0.0), f"Sequence with 0 valid frames in {method} is not zeroed"


# ==============================================================================
# 2. GRU Model Architecture & Shapes
# ==============================================================================
def test_gru_model_dimensions_and_heads() -> None:
    """Requirement: GRU model produces 128-dim embeddings and binary prediction logits."""
    B, T, D = 4, 75, FEATURE_DIM
    features = torch.randn(B, T, D)
    padding_mask = torch.ones((B, T), dtype=torch.bool)
    tracking_mask = torch.ones((B, T), dtype=torch.bool)

    # 1. Full model with classification head
    model = VideoGRUModel(
        input_dim=D,
        hidden_dim=64,
        embedding_dim=128,
        pooling_method="mean_max",
        num_classes=1,
    )

    logits = model(features, padding_mask=padding_mask, tracking_mask=tracking_mask)
    assert logits.shape == (B, 1)
    assert not torch.isnan(logits).any()

    # 2. Both logits and embedding returned
    out_dict = model(
        features,
        padding_mask=padding_mask,
        tracking_mask=tracking_mask,
        return_embedding=True,
    )
    assert isinstance(out_dict, dict)
    assert out_dict["logits"].shape == (B, 1)
    assert out_dict["embedding"].shape == (B, 128)

    # 3. Decoupled SSL embedding extraction
    emb = model.extract_embedding(features, padding_mask=padding_mask, tracking_mask=tracking_mask)
    assert emb.shape == (B, 128)
    assert torch.equal(emb, out_dict["embedding"])

    # 4. Headless encoder-only configuration
    headless_model = VideoGRUModel(num_classes=None)
    emb_headless = headless_model(features, padding_mask=padding_mask)
    assert emb_headless.shape == (B, 128)


def test_gru_batch_size_one_and_variable_lengths() -> None:
    """Requirement: GRU supports batch size 1 and variable sequence lengths."""
    model = VideoGRUModel(input_dim=FEATURE_DIM, hidden_dim=64, embedding_dim=128)

    for seq_len in (45, 80, 120):
        feat = torch.randn(1, seq_len, FEATURE_DIM)
        p_mask = torch.ones((1, seq_len), dtype=torch.bool)
        t_mask = torch.ones((1, seq_len), dtype=torch.bool)

        logits = model(feat, padding_mask=p_mask, tracking_mask=t_mask)
        emb = model.extract_embedding(feat, padding_mask=p_mask, tracking_mask=t_mask)

        assert logits.shape == (1, 1)
        assert emb.shape == (1, 128)
        assert not torch.isnan(logits).any()
        assert not torch.isnan(emb).any()


# ==============================================================================
# 3. BiLSTM Model Architecture & Shapes
# ==============================================================================
def test_bilstm_model_dimensions_and_heads() -> None:
    """Requirement: BiLSTM model produces 128-dim embeddings and binary prediction logits."""
    B, T, D = 4, 60, FEATURE_DIM
    features = torch.randn(B, T, D)
    padding_mask = torch.ones((B, T), dtype=torch.bool)
    tracking_mask = torch.ones((B, T), dtype=torch.bool)

    # 1. Full model with classification head
    model = VideoBiLSTMModel(
        input_dim=D,
        hidden_dim=64,
        embedding_dim=128,
        pooling_method="mean",
        num_classes=1,
    )

    logits = model(features, padding_mask=padding_mask, tracking_mask=tracking_mask)
    assert logits.shape == (B, 1)
    assert not torch.isnan(logits).any()

    # 2. Both logits and embedding returned
    out_dict = model(
        features,
        padding_mask=padding_mask,
        tracking_mask=tracking_mask,
        return_embedding=True,
    )
    assert isinstance(out_dict, dict)
    assert out_dict["logits"].shape == (B, 1)
    assert out_dict["embedding"].shape == (B, 128)

    # 3. Decoupled SSL embedding extraction
    emb = model.extract_embedding(features, padding_mask=padding_mask, tracking_mask=tracking_mask)
    assert emb.shape == (B, 128)
    assert torch.equal(emb, out_dict["embedding"])

    # 4. Multi-class head support (e.g. 2 classes)
    model_2cls = VideoBiLSTMModel(num_classes=2)
    logits_2cls = model_2cls(features, padding_mask=padding_mask)
    assert logits_2cls.shape == (B, 2)


def test_bilstm_batch_size_one_and_variable_lengths() -> None:
    """Requirement: BiLSTM supports batch size 1 and variable sequence lengths."""
    model = VideoBiLSTMModel(input_dim=FEATURE_DIM, hidden_dim=64, embedding_dim=128)

    for seq_len in (45, 90, 120):
        feat = torch.randn(1, seq_len, FEATURE_DIM)
        p_mask = torch.ones((1, seq_len), dtype=torch.bool)
        t_mask = torch.ones((1, seq_len), dtype=torch.bool)

        logits = model(feat, padding_mask=p_mask, tracking_mask=t_mask)
        emb = model.extract_embedding(feat, padding_mask=p_mask, tracking_mask=t_mask)

        assert logits.shape == (1, 1)
        assert emb.shape == (1, 128)
        assert not torch.isnan(logits).any()
        assert not torch.isnan(emb).any()


# ==============================================================================
# 4. Gradient Flow & Backpropagation
# ==============================================================================
def test_gru_gradient_flow_and_backprop() -> None:
    """Requirement: Loss backpropagation produces non-zero gradients across all trainable weights."""
    torch.manual_seed(42)
    B, T, D = 4, 50, FEATURE_DIM
    features = torch.randn(B, T, D, requires_grad=True)
    padding_mask = torch.ones((B, T), dtype=torch.bool)
    tracking_mask = torch.ones((B, T), dtype=torch.bool)
    targets = torch.tensor([[1.0], [0.0], [1.0], [0.0]], dtype=torch.float32)

    model = VideoGRUModel(input_dim=D, hidden_dim=64, embedding_dim=128, num_classes=1)
    criterion = nn.BCEWithLogitsLoss()

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    optimizer.zero_grad()

    logits = model(features, padding_mask=padding_mask, tracking_mask=tracking_mask)
    loss = criterion(logits, targets)
    loss.backward()

    # Verify every single parameter has valid, non-zero gradient
    for name, param in model.named_parameters():
        if param.requires_grad:
            assert param.grad is not None, f"Gradient missing for {name}"
            assert not torch.isnan(param.grad).any(), f"NaN gradient in {name}"
            assert not torch.isinf(param.grad).any(), f"Inf gradient in {name}"
            assert param.grad.abs().sum() > 0.0, f"Zero gradient in {name}"


def test_bilstm_gradient_flow_and_backprop() -> None:
    """Requirement: Loss backpropagation produces non-zero gradients across all trainable weights."""
    torch.manual_seed(42)
    B, T, D = 4, 50, FEATURE_DIM
    features = torch.randn(B, T, D, requires_grad=True)
    padding_mask = torch.ones((B, T), dtype=torch.bool)
    tracking_mask = torch.ones((B, T), dtype=torch.bool)
    targets = torch.tensor([[0.0], [1.0], [0.0], [1.0]], dtype=torch.float32)

    model = VideoBiLSTMModel(input_dim=D, hidden_dim=64, embedding_dim=128, num_classes=1)
    criterion = nn.BCEWithLogitsLoss()

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    optimizer.zero_grad()

    logits = model(features, padding_mask=padding_mask, tracking_mask=tracking_mask)
    loss = criterion(logits, targets)
    loss.backward()

    for name, param in model.named_parameters():
        if param.requires_grad:
            assert param.grad is not None, f"Gradient missing for {name}"
            assert not torch.isnan(param.grad).any(), f"NaN gradient in {name}"
            assert not torch.isinf(param.grad).any(), f"Inf gradient in {name}"
            assert param.grad.abs().sum() > 0.0, f"Zero gradient in {name}"


# ==============================================================================
# 5. Masking Invariance & Degraded Sequence Resilience
# ==============================================================================
def test_masking_invariance_on_padded_frames() -> None:
    """Requirement: Changing values in padded regions does not change embeddings or logits."""
    B, T, D = 2, 60, FEATURE_DIM
    features1 = torch.randn(B, T, D)
    padding_mask = torch.ones((B, T), dtype=torch.bool)
    # Mark frames 40-59 as padding
    padding_mask[:, 40:] = False

    features2 = features1.clone()
    # Scramble padded frames with arbitrary large numbers
    features2[:, 40:, :] = 999.0

    model = VideoGRUModel(input_dim=D, hidden_dim=64, embedding_dim=128)
    model.eval()

    with torch.no_grad():
        emb1 = model.extract_embedding(features1, padding_mask=padding_mask)
        emb2 = model.extract_embedding(features2, padding_mask=padding_mask)

    # Embeddings must be numerically identical despite padded noise
    assert torch.allclose(emb1, emb2, atol=1e-5)


def test_degraded_tracking_sequence_handling() -> None:
    """Requirement: 100% untracked sequences produce finite outputs without crashing."""
    B, T, D = 2, 50, FEATURE_DIM
    features = torch.randn(B, T, D)
    padding_mask = torch.ones((B, T), dtype=torch.bool)
    tracking_mask = torch.zeros((B, T), dtype=torch.bool)  # All frames untracked

    gru_model = VideoGRUModel(input_dim=D, hidden_dim=64, embedding_dim=128)
    bilstm_model = VideoBiLSTMModel(input_dim=D, hidden_dim=64, embedding_dim=128)

    gru_emb = gru_model.extract_embedding(features, padding_mask=padding_mask, tracking_mask=tracking_mask)
    bilstm_emb = bilstm_model.extract_embedding(features, padding_mask=padding_mask, tracking_mask=tracking_mask)

    assert not torch.isnan(gru_emb).any()
    assert not torch.isinf(gru_emb).any()
    assert not torch.isnan(bilstm_emb).any()
    assert not torch.isinf(bilstm_emb).any()


# ==============================================================================
# 6. Participant Statistical Feature Extractor
# ==============================================================================
def test_statistical_feature_extractor_dimensions_and_names() -> None:
    """Requirement: Extractor produces exactly 220 features matching descriptive names."""
    extractor = ParticipantStatisticalFeatureExtractor()
    assert extractor.n_features_out_ == 220
    assert len(extractor.get_feature_names_out()) == 220

    # Single sequence extraction
    T = 60
    single_seq = np.random.uniform(0.0, 1.0, size=(T, 24)).astype(np.float32)
    single_seq[:, 22] = 0.85  # Tracking confidence
    single_seq[:, 23] = 1.0   # Success flag

    vec = extractor.extract_single(single_seq)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (220,)
    assert not np.isnan(vec).any()
    assert not np.isinf(vec).any()

    # Batch transform
    batch_seqs = [
        np.random.uniform(0.0, 1.0, size=(50, 24)).astype(np.float32),
        np.random.uniform(0.0, 1.0, size=(80, 24)).astype(np.float32),
    ]
    mat = extractor.transform(batch_seqs)
    assert mat.shape == (2, 220)
    assert not np.isnan(mat).any()


def test_statistical_feature_extractor_zero_tracked_frames() -> None:
    """Requirement: Extractor safely handles sequences with 0 valid tracked frames."""
    extractor = ParticipantStatisticalFeatureExtractor()
    T = 50
    seq = np.random.uniform(0.0, 1.0, size=(T, 24)).astype(np.float32)
    seq[:, 22] = 0.20  # Below 0.60 threshold
    seq[:, 23] = 0.0   # Failed tracking

    vec = extractor.extract_single(seq)
    assert vec.shape == (220,)
    assert not np.isnan(vec).any()
    assert not np.isinf(vec).any()

    # Dropout rate should be 1.0
    feature_names = extractor.get_feature_names_out()
    dropout_idx = feature_names.index("tracking_dropout_rate")
    assert vec[dropout_idx] == 1.0


# ==============================================================================
# 7. Statistical Classifier Baselines (Logistic Regression & Random Forest)
# ==============================================================================
def test_statistical_classifier_baselines_fit_predict() -> None:
    """Requirement: Baseline classifiers fit within folds, predict classes and probabilities."""
    np.random.seed(42)
    N = 20
    X_raw = [
        np.random.uniform(0.0, 1.0, size=(np.random.randint(45, 100), 24)).astype(np.float32)
        for _ in range(N)
    ]
    for arr in X_raw:
        arr[:, 22] = np.random.uniform(0.5, 0.95, size=len(arr))
        arr[:, 23] = 1.0

    y = np.random.randint(0, 2, size=N)

    # 1. Logistic Regression Baseline
    lr = VideoLogisticRegressionBaseline(max_iter=500, random_state=42)
    lr.fit(X_raw, y)

    preds_lr = lr.predict(X_raw)
    probs_lr = lr.predict_proba(X_raw)
    score_lr = lr.score(X_raw, y)

    assert preds_lr.shape == (N,)
    assert set(np.unique(preds_lr)).issubset({0, 1})
    assert probs_lr.shape == (N, 2)
    assert np.allclose(probs_lr.sum(axis=1), 1.0)
    assert 0.0 <= score_lr <= 1.0
    assert lr.coefficients_ is not None

    # 2. Random Forest Baseline
    rf = VideoRandomForestBaseline(n_estimators=20, max_depth=3, random_state=42)
    rf.fit(X_raw, y)

    preds_rf = rf.predict(X_raw)
    probs_rf = rf.predict_proba(X_raw)
    score_rf = rf.score(X_raw, y)

    assert preds_rf.shape == (N,)
    assert set(np.unique(preds_rf)).issubset({0, 1})
    assert probs_rf.shape == (N, 2)
    assert np.allclose(probs_rf.sum(axis=1), 1.0)
    assert 0.0 <= score_rf <= 1.0
    assert rf.feature_importances_ is not None
    assert len(rf.feature_importances_) == 220


# ==============================================================================
# 8. End-to-End Integration with Phase 2 Dataset & DataLoader
# ==============================================================================
def test_end_to_end_dataloader_to_models() -> None:
    """Requirement: Integration test feeding actual V2 dataset batches to GRU and BiLSTM models."""
    dataset = PPDVideoDataset(partition="train", validate_on_init=False)
    loader = DataLoader(
        dataset,
        batch_size=8,
        shuffle=False,
        collate_fn=pad_collate_fn,
    )

    batch = next(iter(loader))
    features = batch["features"]
    padding_mask = batch["padding_mask"]
    tracking_mask = batch["tracking_mask"]
    targets = batch["targets"]

    B, T, D = features.shape
    assert B == 8
    assert D == 24

    # Test GRU forward pass
    gru_model = VideoGRUModel(input_dim=24, hidden_dim=64, embedding_dim=128, num_classes=1)
    gru_res = gru_model(features, padding_mask=padding_mask, tracking_mask=tracking_mask, return_embedding=True)
    assert gru_res["logits"].shape == (B, 1)
    assert gru_res["embedding"].shape == (B, 128)
    assert not torch.isnan(gru_res["logits"]).any()
    assert not torch.isnan(gru_res["embedding"]).any()

    # Test BiLSTM forward pass
    bilstm_model = VideoBiLSTMModel(input_dim=24, hidden_dim=64, embedding_dim=128, num_classes=1)
    bilstm_res = bilstm_model(features, padding_mask=padding_mask, tracking_mask=tracking_mask, return_embedding=True)
    assert bilstm_res["logits"].shape == (B, 1)
    assert bilstm_res["embedding"].shape == (B, 128)
    assert not torch.isnan(bilstm_res["logits"]).any()
    assert not torch.isnan(bilstm_res["embedding"]).any()

