"""Synthetic Audio Pipeline module.

Exposes generator, conditioning extractor, and configuration interfaces
for the synthetic audio data generation benchmark.
"""

from pipelines.synthetic_audio.config import (
    ACOUSTIC_FEATURE_BOUNDS,
    ACOUSTIC_FEATURE_NAMES,
    ACOUSTIC_FEATURE_STDS,
    BASELINE_ACOUSTIC_MEANS,
    CONDITIONING_COVARIATE_NAMES,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    EMBEDDING_DIM,
    MAX_SEQUENCE_LENGTH,
    MIN_SEQUENCE_LENGTH,
    SYNTHETIC_AUDIO_DIR,
    SYNTHETIC_AUDIO_FEATURES_DIR,
    SYNTHETIC_AUDIO_MANIFEST_PATH,
)
from pipelines.synthetic_audio.conditioning import (
    ClinicalConditioningExtractor,
    extract_cohort_conditioning,
)
from pipelines.synthetic_audio.generator import (
    SyntheticAudioGenerator,
    run_generation,
)

__all__ = [
    "ACOUSTIC_FEATURE_BOUNDS",
    "ACOUSTIC_FEATURE_NAMES",
    "ACOUSTIC_FEATURE_STDS",
    "BASELINE_ACOUSTIC_MEANS",
    "CONDITIONING_COVARIATE_NAMES",
    "DATA_ORIGIN_TAG",
    "DEFAULT_RANDOM_SEED",
    "EMBEDDING_DIM",
    "MAX_SEQUENCE_LENGTH",
    "MIN_SEQUENCE_LENGTH",
    "SYNTHETIC_AUDIO_DIR",
    "SYNTHETIC_AUDIO_FEATURES_DIR",
    "SYNTHETIC_AUDIO_MANIFEST_PATH",
    "ClinicalConditioningExtractor",
    "extract_cohort_conditioning",
    "SyntheticAudioGenerator",
    "run_generation",
]

