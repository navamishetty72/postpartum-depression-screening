"""Modular Multimodal Fusion & Cross-Modal Discordance Engine.

MIORA Postpartum Depression Screening Research Prototype.

Responsibilities:
1. Ingest structured single-modality outputs (clinical, text, audio, video).
2. Validate modality statuses ('completed', 'unavailable', 'failed', 'not_requested').
3. Distinguish true risk-predictive modalities from non-predictive extraction tasks (Text NER).
4. Strictly reject combining incompatible outputs or treating entity confidence as risk probabilities.
5. Track underlying model versions across all contributing branches.
6. Evaluate whether late fusion is scientifically justified and technically possible (requiring >= 2 predictive modalities).
7. Perform cross-modal discordance analysis with transparent explanations when data is insufficient.
8. Support clean extensibility for future trained unimodal audio/video inference classifiers without rewriting screening APIs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel

from backend.schemas.screening import (
    AudioModalityResult,
    ClinicalModalityResult,
    FusionModalityResult,
    TextModalityResult,
    VideoModalityResult,
)

logger = logging.getLogger("ppd.fusion_engine")

VALID_MODALITY_STATUSES = {"completed", "unavailable", "failed", "not_requested"}


class FusionStatus(str, Enum):
    """Execution status for the multimodal fusion stage."""

    COMPLETED = "completed"
    NOT_AVAILABLE = "not_available"
    INSUFFICIENT_DATA = "insufficient_data"
    FAILED = "failed"


class ModalityType(str, Enum):
    """Supported screening modalities."""

    CLINICAL = "clinical"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"


@dataclass
class ModalityCandidate:
    """Standardized representation of a single modality output candidate for fusion."""

    modality: str
    status: str
    probability: Optional[float] = None
    predicted_class: Optional[int] = None
    risk_category: Optional[str] = None
    model_version: Optional[str] = None
    is_predictive: bool = False
    is_available: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscordanceResult:
    """Structured report detailing cross-modal alignment or divergence."""

    discordance_detected: bool
    comparison: List[Dict[str, Any]]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to standard serializable dictionary matching the API contract."""
        return {
            "discordance_detected": self.discordance_detected,
            "comparison": self.comparison,
            "explanation": self.explanation,
        }


class DiscordanceAnalyzer:
    """Analyzes divergence between comparable predictive modality signals.

    NOTE ON CLINICAL VALIDITY:
    The default threshold (0.25) is an exploratory research heuristic for evaluating
    divergence across multiple predictive modalities under simulated benchmark conditions.
    It is NOT a clinically validated diagnostic cut-off and must be calibrated against
    prospective multi-site clinical trial cohorts.

    Requires at least two comparable calibrated risk probabilities. Never compares
    Text NER entity confidence with clinical risk probability.
    """

    DEFAULT_DISCORDANCE_THRESHOLD: float = 0.25

    def __init__(self, threshold: float = DEFAULT_DISCORDANCE_THRESHOLD) -> None:
        self.threshold: float = float(threshold)

    def analyze(self, candidates: List[ModalityCandidate]) -> DiscordanceResult:
        """Evaluate discordance across candidates with valid continuous risk probabilities."""
        predictive = [c for c in candidates if c.is_predictive and c.probability is not None]

        if len(predictive) < 2:
            return DiscordanceResult(
                discordance_detected=False,
                comparison=[],
                explanation="Insufficient comparable modality predictions.",
            )

        comparisons: List[Dict[str, Any]] = []
        max_diff = 0.0

        for i in range(len(predictive)):
            for j in range(i + 1, len(predictive)):
                c1, c2 = predictive[i], predictive[j]
                assert c1.probability is not None and c2.probability is not None
                diff = abs(c1.probability - c2.probability)
                max_diff = max(max_diff, diff)
                is_divergent = diff >= self.threshold

                comparisons.append({
                    "modality_a": c1.modality,
                    "modality_b": c2.modality,
                    "probability_a": round(c1.probability, 4),
                    "probability_b": round(c2.probability, 4),
                    "absolute_difference": round(diff, 4),
                    "divergence_significant": is_divergent,
                })

        is_discordant = max_diff >= self.threshold
        explanation = (
            f"Significant cross-modal discordance detected (max difference {max_diff:.4f} >= threshold {self.threshold:.2f}). "
            "Clinician should investigate divergent behavioral vs. self-reported clinical signs."
            if is_discordant
            else f"Modality probabilities are concordant (max difference {max_diff:.4f} < threshold {self.threshold:.2f})."
        )

        return DiscordanceResult(
            discordance_detected=is_discordant,
            comparison=comparisons,
            explanation=explanation,
        )


class BaseFusionStrategy(ABC):
    """Abstract base strategy for combining multiple validated predictive modality streams."""

    @abstractmethod
    def combine(
        self,
        candidates: List[ModalityCandidate],
    ) -> Tuple[float, str, Optional[int], Dict[str, float]]:
        """Combine predictive modalities into (combined_score, risk_category, epds_equiv, contributions)."""
        pass


class WeightedAverageFusionStrategy(BaseFusionStrategy):
    """Modular late fusion strategy performing calibrated weighted probability aggregation.

    Enforces that all candidates are predictive with valid probability outputs in [0.0, 1.0].
    """

    def __init__(self, default_weights: Optional[Dict[str, float]] = None) -> None:
        self.default_weights: Dict[str, float] = default_weights or {
            "clinical": 0.40,
            "text": 0.20,
            "audio": 0.20,
            "video": 0.20,
        }

    def combine(
        self,
        candidates: List[ModalityCandidate],
    ) -> Tuple[float, str, Optional[int], Dict[str, float]]:
        """Compute weighted probability average across available predictive modalities."""
        predictive = [c for c in candidates if c.is_predictive and c.probability is not None]
        if len(predictive) < 2:
            raise ValueError(
                f"WeightedAverageFusionStrategy requires >= 2 predictive modalities, got {len(predictive)}."
            )

        # Normalize weights across available modalities
        raw_weights = {c.modality: self.default_weights.get(c.modality, 1.0) for c in predictive}
        total_weight = sum(raw_weights.values())
        if total_weight <= 0:
            raise ValueError("Total modality fusion weight must be greater than zero.")

        normalized_weights = {k: v / total_weight for k, v in raw_weights.items()}

        combined_score = sum(
            c.probability * normalized_weights[c.modality] for c in predictive  # type: ignore
        )
        combined_score = round(float(combined_score), 4)

        # Risk tiering
        if combined_score >= 0.70:
            risk_category = "HIGH_RISK"
        elif combined_score >= 0.40:
            risk_category = "MODERATE_RISK"
        else:
            risk_category = "LOW_RISK"

        # Linear EPDS 0-30 approximation
        epds_equivalent = min(30, max(0, int(round(combined_score * 30))))

        return (
            combined_score,
            risk_category,
            epds_equivalent,
            {k: round(v, 4) for k, v in normalized_weights.items()},
        )


class MultimodalFusionEngine:
    """Central engine orchestrating multimodal fusion and cross-modal discordance analysis.

    Defensively checks model readiness, refuses to fabricate composite scores when models
    are missing or non-predictive, and produces transparent audit records.
    """

    def __init__(
        self,
        strategy: Optional[BaseFusionStrategy] = None,
        discordance_analyzer: Optional[DiscordanceAnalyzer] = None,
    ) -> None:
        # None by default: reflects that unimodal audio/video classifiers are not yet trained
        self.strategy: Optional[BaseFusionStrategy] = strategy
        self.discordance_analyzer: DiscordanceAnalyzer = (
            discordance_analyzer or DiscordanceAnalyzer()
        )

    def extract_candidate(
        self,
        modality: str,
        data: Union[BaseModel, Dict[str, Any], None],
    ) -> ModalityCandidate:
        """Defensively parse and normalize a modality payload into a ModalityCandidate."""
        if data is None:
            return ModalityCandidate(
                modality=modality,
                status="not_requested",
                is_predictive=False,
                is_available=False,
            )

        dict_data = data.model_dump() if isinstance(data, BaseModel) else dict(data)
        status = str(dict_data.get("status", "unavailable")).lower()

        if status not in VALID_MODALITY_STATUSES:
            raise ValueError(
                f"Invalid modality status '{status}' for modality '{modality}'. "
                f"Expected one of {sorted(VALID_MODALITY_STATUSES)}."
            )

        if status != "completed":
            return ModalityCandidate(
                modality=modality,
                status=status,
                is_predictive=False,
                is_available=False,
                model_version=dict_data.get("model_version"),
                metadata=dict_data,
            )

        # Modality status is 'completed' - determine capabilities
        if modality == ModalityType.CLINICAL.value:
            prediction = dict_data.get("prediction") or {}
            prob = prediction.get("predicted_risk_probability")
            pred_class = prediction.get("predicted_class")
            risk_cat = prediction.get("risk_category")

            if prob is not None and isinstance(prob, (int, float)) and 0.0 <= prob <= 1.0:
                return ModalityCandidate(
                    modality=modality,
                    status=status,
                    probability=float(prob),
                    predicted_class=int(pred_class) if pred_class is not None else None,
                    risk_category=str(risk_cat) if risk_cat else None,
                    model_version=dict_data.get("model_version", "random_forest"),
                    is_predictive=True,
                    is_available=True,
                    metadata=dict_data,
                )
            return ModalityCandidate(
                modality=modality,
                status="failed",
                is_predictive=False,
                is_available=False,
                metadata={"error": "Malformed clinical prediction payload"},
            )

        elif modality == ModalityType.TEXT.value:
            # Text NER extracts biomedical entity spans. It does NOT produce a PPD risk probability.
            # Enforce strict scientific boundary: never treat span confidence as PPD risk probability.
            return ModalityCandidate(
                modality=modality,
                status=status,
                probability=None,
                predicted_class=None,
                model_version=dict_data.get("model_version"),
                is_predictive=False,
                is_available=True,
                metadata={
                    "processing_type": dict_data.get("processing_type", "biomedical_ner"),
                    "total_entities_detected": dict_data.get("total_entities_detected", 0),
                },
            )

        elif modality in (ModalityType.AUDIO.value, ModalityType.VIDEO.value):
            # Audio and video inference classifiers are not yet trained in this prototype phase.
            prediction = dict_data.get("prediction")
            if prediction and isinstance(prediction, dict):
                prob = prediction.get("predicted_risk_probability")
                if prob is not None and isinstance(prob, (int, float)) and 0.0 <= prob <= 1.0:
                    return ModalityCandidate(
                        modality=modality,
                        status=status,
                        probability=float(prob),
                        model_version=dict_data.get("model_version"),
                        is_predictive=True,
                        is_available=True,
                        metadata=dict_data,
                    )

            # Not predictive / fixture-only
            return ModalityCandidate(
                modality=modality,
                status="unavailable",
                is_predictive=False,
                is_available=False,
                model_version=dict_data.get("model_version"),
                metadata=dict_data,
            )

        raise ValueError(f"Unknown modality '{modality}'.")

    def evaluate(
        self,
        clinical: Union[ClinicalModalityResult, Dict[str, Any], None] = None,
        text: Union[TextModalityResult, Dict[str, Any], None] = None,
        audio: Union[AudioModalityResult, Dict[str, Any], None] = None,
        video: Union[VideoModalityResult, Dict[str, Any], None] = None,
    ) -> FusionModalityResult:
        """Evaluate multimodal inputs and compute fusion and discordance results."""
        try:
            candidates: List[ModalityCandidate] = [
                self.extract_candidate(ModalityType.CLINICAL.value, clinical),
                self.extract_candidate(ModalityType.TEXT.value, text),
                self.extract_candidate(ModalityType.AUDIO.value, audio),
                self.extract_candidate(ModalityType.VIDEO.value, video),
            ]
        except ValueError as exc:
            logger.error("Modality extraction validation failed during fusion: %s", exc)
            return FusionModalityResult(
                status=FusionStatus.FAILED.value,
                combined_score=None,
                risk_category=None,
                epds_equivalent=None,
                modality_contributions={},
                discordance_analysis={
                    "discordance_detected": False,
                    "comparison": [],
                    "explanation": f"Modality validation failed: {exc}",
                },
            )

        # 1. Evaluate cross-modal discordance
        discordance_report = self.discordance_analyzer.analyze(candidates)

        # 2. Identify comparable predictive modalities
        predictive_candidates = [
            c for c in candidates if c.is_predictive and c.probability is not None
        ]

        # 3. Check whether fusion is technically possible
        if len(predictive_candidates) < 2:
            # When < 2 predictive modalities exist, fusion is not available
            # Log exact reason for auditability
            available_modalities = [c.modality for c in candidates if c.is_available]
            logger.info(
                "Multimodal late fusion not available: %d predictive modality/modalities (%s) "
                "available across active candidates %s.",
                len(predictive_candidates),
                [c.modality for c in predictive_candidates],
                available_modalities,
            )
            return FusionModalityResult(
                status=FusionStatus.NOT_AVAILABLE.value,
                combined_score=None,
                risk_category=None,
                epds_equivalent=None,
                modality_contributions={},
                discordance_analysis=discordance_report.to_dict(),
            )

        # 4. If >= 2 predictive modalities exist, evaluate with fusion strategy if configured
        if self.strategy is None:
            logger.warning(
                "Multiple predictive modalities (%s) are present, but no validated fusion strategy is active.",
                [c.modality for c in predictive_candidates],
            )
            return FusionModalityResult(
                status=FusionStatus.NOT_AVAILABLE.value,
                combined_score=None,
                risk_category=None,
                epds_equivalent=None,
                modality_contributions={},
                discordance_analysis=discordance_report.to_dict(),
            )

        # 5. Execute fusion strategy
        try:
            combined_score, risk_cat, epds_equiv, contributions = self.strategy.combine(
                predictive_candidates
            )
            return FusionModalityResult(
                status=FusionStatus.COMPLETED.value,
                combined_score=combined_score,
                risk_category=risk_cat,
                epds_equivalent=epds_equiv,
                modality_contributions=contributions,
                discordance_analysis=discordance_report.to_dict(),
            )
        except Exception as exc:
            logger.error("Fusion strategy execution failed: %s", exc, exc_info=True)
            return FusionModalityResult(
                status=FusionStatus.FAILED.value,
                combined_score=None,
                risk_category=None,
                epds_equivalent=None,
                modality_contributions={},
                discordance_analysis=discordance_report.to_dict(),
            )


# Global singleton instance for production runtime
fusion_engine = MultimodalFusionEngine()


def get_fusion_engine() -> MultimodalFusionEngine:
    """FastAPI dependency provider for MultimodalFusionEngine."""
    return fusion_engine

