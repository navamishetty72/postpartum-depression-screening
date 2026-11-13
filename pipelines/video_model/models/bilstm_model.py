"""Lightweight Bidirectional Long Short-Term Memory (BiLSTM) model for PPD video modeling.

Architecture:
- Recurrent Encoder: 1-layer BiLSTM (input_dim=24, hidden_dim=64 per direction -> 128-dim temporal features).
- Temporal Pooling: Masked pooling (mean, max, mean_max, attention) respecting tracking & padding masks.
- Latent Projection: Standardizes pooled representations to a fixed 128-dimensional participant embedding.
- Prediction Head: Optional linear head for binary risk screening (decoupled from the encoder).

Self-Supervised Learning (SSL) Readiness:
The encoder is cleanly separated from the classification head. The embedding extraction interface
`extract_embedding()` can be utilized directly by temporal contrastive or masked autoencoder heads
without modifying the backbone architecture.

SCIENTIFIC INTEGRITY NOTICE:
Synthetic Video V2 features are abstract numerical simulations. Video features alone
do not represent authentic patient observations or diagnostic biomarkers.
"""

from typing import Any, Dict, Optional, Union
import torch
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

from pipelines.video_model.config import FEATURE_DIM
from pipelines.video_model.models.temporal_pooling import MaskedTemporalPooling


class VideoBiLSTMEncoder(nn.Module):
    """Bidirectional LSTM encoder mapping variable-length (T, 24) video sequences to a 128-dim embedding."""

    def __init__(
        self,
        input_dim: int = FEATURE_DIM,
        hidden_dim: int = 64,
        embedding_dim: int = 128,
        num_layers: int = 1,
        dropout: float = 0.0,
        pooling_method: str = "mean",
    ) -> None:
        """Initialize VideoBiLSTMEncoder.

        Args:
            input_dim: Feature dimension per frame (default: 24).
            hidden_dim: Hidden state dimension per direction (default: 64 -> 128 total bidirectional).
            embedding_dim: Fixed output participant embedding dimension (default: 128).
            num_layers: Number of recurrent layers (default: 1).
            dropout: Dropout probability.
            pooling_method: Temporal pooling strategy ('mean', 'max', 'mean_max', 'attention').
        """
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.embedding_dim = embedding_dim
        self.num_layers = num_layers
        self.pooling_method = pooling_method

        rnn_dropout = dropout if num_layers > 1 else 0.0
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=rnn_dropout,
        )

        bilstm_out_dim = hidden_dim * 2  # Bidirectional doubles hidden dimension
        self.pooling = MaskedTemporalPooling(
            method=pooling_method,
            input_dim=bilstm_out_dim,
        )

        pooled_dim = self.pooling.output_dim(bilstm_out_dim)

        # Latent projection mapping pooled features to fixed 128-dim embedding
        self.projection = nn.Sequential(
            nn.Linear(pooled_dim, embedding_dim),
            nn.LayerNorm(embedding_dim),
            nn.ReLU(),
            nn.Dropout(dropout) if dropout > 0.0 else nn.Identity(),
        )

    def forward(
        self,
        features: torch.Tensor,
        padding_mask: Optional[torch.Tensor] = None,
        tracking_mask: Optional[torch.Tensor] = None,
        sequence_lengths: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Extract 128-dimensional participant embedding from sequence tensor.

        Args:
            features: (B, T, 24) float32 tensor.
            padding_mask: (B, T) boolean mask (True for real frames, False for padded).
            tracking_mask: (B, T) boolean mask (True for valid tracked frames).
            sequence_lengths: Optional (B,) long tensor of valid sequence lengths.

        Returns:
            (B, 128) float32 participant embedding tensor.
        """
        B, T, D = features.shape

        if sequence_lengths is None and padding_mask is not None:
            sequence_lengths = padding_mask.sum(dim=1).clamp(min=1)

        if sequence_lengths is not None:
            lengths_cpu = sequence_lengths.cpu().to(torch.int64)
            lengths_cpu = torch.clamp(lengths_cpu, min=1)
            packed = pack_padded_sequence(
                features, lengths_cpu, batch_first=True, enforce_sorted=False
            )
            packed_out, _ = self.lstm(packed)
            lstm_out, _ = pad_packed_sequence(packed_out, batch_first=True, total_length=T)
        else:
            lstm_out, _ = self.lstm(features)

        # Determine effective temporal mask for pooling
        if padding_mask is not None and tracking_mask is not None:
            effective_mask = padding_mask & tracking_mask
            zero_tracked = effective_mask.sum(dim=1) == 0
            if zero_tracked.any():
                effective_mask = torch.where(
                    zero_tracked.unsqueeze(-1), padding_mask, effective_mask
                )
        elif padding_mask is not None:
            effective_mask = padding_mask
        elif tracking_mask is not None:
            effective_mask = tracking_mask
        else:
            effective_mask = torch.ones((B, T), dtype=torch.bool, device=features.device)

        pooled = self.pooling(lstm_out, mask=effective_mask)
        embedding = self.projection(pooled)
        return embedding


class VideoBiLSTMModel(nn.Module):
    """Complete BiLSTM model with decoupled encoder and optional classification head."""

    def __init__(
        self,
        input_dim: int = FEATURE_DIM,
        hidden_dim: int = 64,
        embedding_dim: int = 128,
        num_layers: int = 1,
        dropout: float = 0.0,
        pooling_method: str = "mean",
        num_classes: Optional[int] = 1,
    ) -> None:
        """Initialize VideoBiLSTMModel.

        Args:
            input_dim: Feature dimension per frame (default: 24).
            hidden_dim: BiLSTM hidden state dimension per direction (default: 64).
            embedding_dim: Fixed output participant embedding dimension (default: 128).
            num_layers: Number of recurrent layers (default: 1).
            dropout: Dropout probability.
            pooling_method: Temporal pooling strategy ('mean', 'max', 'mean_max', 'attention').
            num_classes: Number of prediction targets (1 for binary logit, None for head-free encoder).
        """
        super().__init__()
        self.encoder = VideoBiLSTMEncoder(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            embedding_dim=embedding_dim,
            num_layers=num_layers,
            dropout=dropout,
            pooling_method=pooling_method,
        )

        self.embedding_dim = embedding_dim
        self.num_classes = num_classes

        if num_classes is not None and num_classes > 0:
            self.classifier_head = nn.Linear(embedding_dim, num_classes)
        else:
            self.classifier_head = None

    def extract_embedding(
        self,
        features: torch.Tensor,
        padding_mask: Optional[torch.Tensor] = None,
        tracking_mask: Optional[torch.Tensor] = None,
        sequence_lengths: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Direct access to the 128-dimensional participant embedding for SSL/fusion."""
        return self.encoder(
            features=features,
            padding_mask=padding_mask,
            tracking_mask=tracking_mask,
            sequence_lengths=sequence_lengths,
        )

    def forward(
        self,
        features: torch.Tensor,
        padding_mask: Optional[torch.Tensor] = None,
        tracking_mask: Optional[torch.Tensor] = None,
        sequence_lengths: Optional[torch.Tensor] = None,
        return_embedding: bool = False,
    ) -> Union[torch.Tensor, Dict[str, torch.Tensor]]:
        """Forward pass through BiLSTM encoder and optional classification head.

        Args:
            features: (B, T, 24) sequence tensor.
            padding_mask: (B, T) boolean padding mask.
            tracking_mask: (B, T) boolean tracking mask.
            sequence_lengths: (B,) sequence lengths.
            return_embedding: Whether to return embedding alongside logits.

        Returns:
            If return_embedding is True:
                Dict with "logits" (B, num_classes) and "embedding" (B, 128).
            If classifier_head is None:
                (B, 128) embedding tensor.
            Otherwise:
                (B, num_classes) logits tensor.
        """
        embedding = self.encoder(
            features=features,
            padding_mask=padding_mask,
            tracking_mask=tracking_mask,
            sequence_lengths=sequence_lengths,
        )

        if self.classifier_head is not None:
            logits = self.classifier_head(embedding)
            if return_embedding:
                return {"logits": logits, "embedding": embedding}
            return logits

        if return_embedding:
            return {"embedding": embedding}
        return embedding

