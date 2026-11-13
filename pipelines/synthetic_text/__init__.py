"""Synthetic Text Narrative Pipeline module.

Exposes generator, configuration, and execution interfaces
for the synthetic text narrative generation benchmark.
"""

from pipelines.synthetic_text.config import (
    APPROVED_CONDITIONING_COLUMNS,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    GENERATOR_VERSION,
    LANGUAGE_CODE,
    MAX_WORD_COUNT,
    MIN_WORD_COUNT,
    SYNTHETIC_TEXT_DIR,
    SYNTHETIC_TEXT_MANIFEST_PATH,
    SYNTHETIC_TEXT_NARRATIVES_DIR,
)
from pipelines.synthetic_text.generator import (
    SyntheticTextGenerator,
    run_generation,
)

__all__ = [
    "APPROVED_CONDITIONING_COLUMNS",
    "DATA_ORIGIN_TAG",
    "DEFAULT_RANDOM_SEED",
    "GENERATOR_VERSION",
    "LANGUAGE_CODE",
    "MAX_WORD_COUNT",
    "MIN_WORD_COUNT",
    "SYNTHETIC_TEXT_DIR",
    "SYNTHETIC_TEXT_MANIFEST_PATH",
    "SYNTHETIC_TEXT_NARRATIVES_DIR",
    "SyntheticTextGenerator",
    "run_generation",
]

