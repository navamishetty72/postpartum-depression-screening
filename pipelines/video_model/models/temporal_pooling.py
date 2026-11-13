"""Masked temporal pooling modules for variable-length video feature sequences.

Provides pooling operations (mean, max, mean_max, and attention) that strictly respect
sequence padding masks and tracking validity masks. Guarantees numerical stability and
zero-NaN guarantees even in degraded sequences with zero valid tracked frames.

SCIENTIFIC INTEGRITY NOTICE:
Synthetic Video V2 features are abstract numerical simulations. Video features alone
do not represent authentic patient observations or diagnostic biomarkers.
"""

from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class MaskedAttentionPooling(nn.Module):
    """Query-based or self-attention temporal pooling over valid frames.
    
    Computes frame-level attention weights:
        alpha_t = softmax(w^T tanh(W x_t + b))
    where frames masked by padding or tracking failure are assigned -inf logits.
    """

    def __init__(self, input_dim: int, hidden_dim: Optional[int] = None) -> None:
        """Initialize MaskedAttentionPooling.

        Args:
            input_dim: Feature dimension per time step.
            hidden_dim: Dimension of intermediate projection (defaults to input_dim // 2 or 64).
        """
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim if hidden_dim is not None else max(16, input_dim // 2)

        self.attn_net = nn.Sequential(
            nn.Linear(input_dim, self.hidden_dim),
            nn.Tanh(),
            nn.Linear(self.hidden_dim, 1, bias=False),
        )

    def forward(
        self,
        features: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute attention-weighted temporal sum.

        Args:
            features: (B, T, D) sequence tensor.
            mask: (B, T) boolean mask (True for valid frames, False to ignore).

        Returns:
            pooled: (B, D) pooled representation.
            weights: (B, T) attention weights.
        """
        if features.dim() != 3:
            raise ValueError(f"Expected 3D tensor (B, T, D), got shape {features.shape}")

        B, T, D = features.shape

        # (B, T, 1) -> (B, T)
        attn_logits = self.attn_net(features).squeeze(-1)

        if mask is not None:
            if mask.shape != (B, T):
                raise ValueError(f"Mask shape {mask.shape} does not match (B, T) = ({B}, {T})")

            # Check for participants with zero valid frames
            valid_counts = mask.sum(dim=1)  # (B,)
            all_masked = valid_counts == 0  # (B,)

            # Mask out invalid frames with large negative number
            attn_logits = attn_logits.masked_fill(~mask, -1e9)

            # Softmax over temporal dimension
            attn_weights = F.softmax(attn_logits, dim=-1)  # (B, T)

            # For sequences with 0 valid frames, softmax over -1e9 yields uniform weights.
            # Zero out attention weights for all-masked sequences to avoid ungrounded features
            if all_masked.any():
                attn_weights = attn_weights.masked_fill(all_masked.unsqueeze(-1), 0.0)
        else:
            attn_weights = F.softmax(attn_logits, dim=-1)

        # Weighted sum: (B, 1, T) x (B, T, D) -> (B, 1, D) -> (B, D)
        pooled = torch.bmm(attn_weights.unsqueeze(1), features).squeeze(1)

        return pooled, attn_weights


class MaskedTemporalPooling(nn.Module):
    """Unified temporal pooling module supporting mean, max, mean_max, and attention.
    
    Guarantees:
    1. Masked frames (padding or tracking dropouts) do not contaminate representations.
    2. Numerical stability: sequences with zero valid tracked frames output finite zeros
       instead of NaNs or Infs.
    3. Gradient flow remains intact for all valid frames.
    """

    SUPPORTED_METHODS = ("mean", "max", "mean_max", "attention")

    def __init__(
        self,
        method: str = "mean",
        input_dim: Optional[int] = None,
        attn_hidden_dim: Optional[int] = None,
    ) -> None:
        """Initialize MaskedTemporalPooling.

        Args:
            method: One of 'mean', 'max', 'mean_max', or 'attention'.
            input_dim: Required if method is 'attention'. Feature dimension D.
            attn_hidden_dim: Optional hidden dimension for attention network.
        """
        super().__init__()
        self.method = method.lower()
        if self.method not in self.SUPPORTED_METHODS:
            raise ValueError(
                f"Unsupported pooling method: '{method}'. Choose from {self.SUPPORTED_METHODS}."
            )

        self.input_dim = input_dim
        if self.method == "attention":
            if input_dim is None:
                raise ValueError("input_dim must be provided when pooling method is 'attention'.")
            self.attention_module = MaskedAttentionPooling(input_dim, attn_hidden_dim)
        else:
            self.attention_module = None

    def output_dim(self, input_dim: int) -> int:
        """Return the output feature dimension given the input feature dimension."""
        if self.method == "mean_max":
            return input_dim * 2
        return input_dim

    def forward(
        self,
        features: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Pool features across time dimension with mask.

        Args:
            features: (B, T, D) tensor.
            mask: (B, T) boolean mask (True for valid frames, False to ignore).
                If None, all frames are considered valid.

        Returns:
            (B, output_dim) pooled tensor.
        """
        if features.dim() != 3:
            raise ValueError(f"Expected 3D tensor (B, T, D), got shape {features.shape}")

        B, T, D = features.shape

        if mask is None:
            mask = torch.ones((B, T), dtype=torch.bool, device=features.device)
        else:
            if mask.shape != (B, T):
                raise ValueError(f"Mask shape {mask.shape} does not match features (B, T) = ({B}, {T})")

        mask_expanded = mask.unsqueeze(-1).to(dtype=features.dtype)  # (B, T, 1)
        valid_counts = mask.sum(dim=1, keepdim=True)  # (B, 1)
        zero_valid = valid_counts == 0  # (B, 1)

        # Clamped counts to prevent division by zero
        safe_counts = torch.clamp(valid_counts.to(dtype=features.dtype), min=1.0)

        if self.method == "mean":
            masked_sum = (features * mask_expanded).sum(dim=1)  # (B, D)
            pooled = masked_sum / safe_counts
            # Zero out sequences that had zero valid frames
            if zero_valid.any():
                pooled = pooled.masked_fill(zero_valid, 0.0)
            return pooled

        elif self.method == "max":
            # Mask invalid frames with large negative number
            masked_feat = features.masked_fill(~mask.unsqueeze(-1), -1e9)
            max_vals, _ = masked_feat.max(dim=1)  # (B, D)
            # If all frames in a sequence were masked, replace -1e9 with 0.0
            if zero_valid.any():
                max_vals = max_vals.masked_fill(zero_valid, 0.0)
            return max_vals

        elif self.method == "mean_max":
            # Mean branch
            masked_sum = (features * mask_expanded).sum(dim=1)
            mean_vals = masked_sum / safe_counts
            if zero_valid.any():
                mean_vals = mean_vals.masked_fill(zero_valid, 0.0)

            # Max branch
            masked_feat = features.masked_fill(~mask.unsqueeze(-1), -1e9)
            max_vals, _ = masked_feat.max(dim=1)
            if zero_valid.any():
                max_vals = max_vals.masked_fill(zero_valid, 0.0)

            return torch.cat([mean_vals, max_vals], dim=-1)

        elif self.method == "attention":
            pooled, _ = self.attention_module(features, mask=mask)
            return pooled

        else:
            raise ValueError(f"Unknown pooling method: {self.method}")

