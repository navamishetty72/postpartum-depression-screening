"""Synthetic Video Feature Pipeline module.

Exposes generator, configuration, and execution interfaces
for the synthetic video feature trajectory generation benchmark.
"""

from pipelines.synthetic_video.config import (
    CHANNEL_BOUNDS,
    CHANNEL_NAMES,
    CONFIDENCE_THRESHOLD,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    FEATURE_DIM,
    MAX_SEQUENCE_LENGTH,
    MIN_SEQUENCE_LENGTH,
    SYNTHETIC_VIDEO_DIR,
    SYNTHETIC_VIDEO_FEATURES_DIR,
    SYNTHETIC_VIDEO_MANIFEST_PATH,
)
from pipelines.synthetic_video.generator import (
    SyntheticVideoGenerator,
    run_generation,
)
from pipelines.synthetic_video.config_v2 import (
    SYNTHETIC_VIDEO_V2_DIR,
    SYNTHETIC_VIDEO_V2_FEATURES_DIR,
    SYNTHETIC_VIDEO_V2_MANIFEST_PATH,
)
from pipelines.synthetic_video.generator_v2 import (
    SyntheticVideoGeneratorV2,
    run_generation_v2,
)

__all__ = [
    "CHANNEL_BOUNDS",
    "CHANNEL_NAMES",
    "CONFIDENCE_THRESHOLD",
    "DATA_ORIGIN_TAG",
    "DEFAULT_RANDOM_SEED",
    "FEATURE_DIM",
    "MAX_SEQUENCE_LENGTH",
    "MIN_SEQUENCE_LENGTH",
    "SYNTHETIC_VIDEO_DIR",
    "SYNTHETIC_VIDEO_FEATURES_DIR",
    "SYNTHETIC_VIDEO_MANIFEST_PATH",
    "SyntheticVideoGenerator",
    "run_generation",
    "SYNTHETIC_VIDEO_V2_DIR",
    "SYNTHETIC_VIDEO_V2_FEATURES_DIR",
    "SYNTHETIC_VIDEO_V2_MANIFEST_PATH",
    "SyntheticVideoGeneratorV2",
    "run_generation_v2",
]

