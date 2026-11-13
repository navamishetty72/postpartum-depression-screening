"""Real-video facial feature extraction and preprocessing pipeline.

Postpartum Depression (PPD) Multimodal Recognition Research Prototype.
Processes authentic video recordings using OpenCV for ingestion/QC and
OpenFace 2.x for Facial Action Unit, head pose, and eye gaze extraction.
"""

from .config import (
    DATA_ORIGIN_REAL_VIDEO,
    FEATURE_DIM,
    OPENFACE_ACTION_UNITS,
    OPENFACE_GAZE,
    OPENFACE_HEAD_POSE,
    OPENFACE_TRACKING,
    REAL_VIDEO_CHANNEL_NAMES,
)
from .video_reader import VideoReader, VideoInspectionReport
from .openface_runner import OpenFaceRunner, OpenFaceNotFoundError
from .cleaner import FeatureCleaner
from .tensor_builder import TensorBuilder


def __getattr__(name: str):
    if name == "RealVideoPipeline":
        from .pipeline import RealVideoPipeline
        return RealVideoPipeline
    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "DATA_ORIGIN_REAL_VIDEO",
    "FEATURE_DIM",
    "OPENFACE_ACTION_UNITS",
    "OPENFACE_GAZE",
    "OPENFACE_HEAD_POSE",
    "OPENFACE_TRACKING",
    "REAL_VIDEO_CHANNEL_NAMES",
    "VideoReader",
    "VideoInspectionReport",
    "OpenFaceRunner",
    "OpenFaceNotFoundError",
    "FeatureCleaner",
    "TensorBuilder",
    "RealVideoPipeline",
]
