"""Video Model Architectures module.

Exports recurrent neural network architectures (GRU, BiLSTM), masked temporal pooling modules,
participant-level statistical feature extractors, and baseline classifiers.

SCIENTIFIC INTEGRITY NOTICE:
Synthetic Video V2 features are abstract numerical simulations. Video features alone
do not represent authentic patient observations or diagnostic biomarkers.
"""

from pipelines.video_model.models.bilstm_model import (
    VideoBiLSTMEncoder,
    VideoBiLSTMModel,
)
from pipelines.video_model.models.gru_model import (
    VideoGRUEncoder,
    VideoGRUModel,
)
from pipelines.video_model.models.statistical_baseline import (
    ParticipantStatisticalFeatureExtractor,
    SUPPORTED_FEATURE_SUBSETS,
    VideoLogisticRegressionBaseline,
    VideoRandomForestBaseline,
)
from pipelines.video_model.models.temporal_pooling import (
    MaskedAttentionPooling,
    MaskedTemporalPooling,
)

__all__ = [
    # Temporal Pooling
    "MaskedAttentionPooling",
    "MaskedTemporalPooling",
    # GRU Models
    "VideoGRUEncoder",
    "VideoGRUModel",
    # BiLSTM Models
    "VideoBiLSTMEncoder",
    "VideoBiLSTMModel",
    # Statistical Baselines
    "ParticipantStatisticalFeatureExtractor",
    "SUPPORTED_FEATURE_SUBSETS",
    "VideoLogisticRegressionBaseline",
    "VideoRandomForestBaseline",
]

