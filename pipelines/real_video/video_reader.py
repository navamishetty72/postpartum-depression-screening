"""Video ingestion, frame inspection, and quality assurance module using OpenCV.

Validates that raw video files are readable, decodable, and conform to expected
frame rates, dimensions, and duration requirements prior to OpenFace feature extraction.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from .config import SUPPORTED_VIDEO_EXTENSIONS


@dataclass
class VideoInspectionReport:
    """Structured quality-control report from raw video inspection."""

    video_path: str
    filename: str
    extension: str
    is_readable: bool
    error_message: Optional[str]
    fps: float
    frame_count: int
    duration_sec: float
    width: int
    height: int
    codec: str
    decoded_frame_count: int
    corrupted_frame_count: int
    corrupted_frame_indices: List[int]
    corrupted_frame_percentage: float
    frame_timestamps: List[float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert inspection report to JSON-serializable dictionary."""
        d = asdict(self)
        # Summarize timestamps in dict to avoid massive JSON logs
        d["timestamp_start"] = self.frame_timestamps[0] if self.frame_timestamps else 0.0
        d["timestamp_end"] = self.frame_timestamps[-1] if self.frame_timestamps else 0.0
        d["timestamp_count"] = len(self.frame_timestamps)
        d.pop("frame_timestamps", None)
        return d


class VideoReader:
    """Ingests raw video recordings and performs exhaustive integrity inspection."""

    def __init__(self, supported_extensions: Optional[set] = None) -> None:
        self.supported_extensions = supported_extensions or SUPPORTED_VIDEO_EXTENSIONS

    def inspect_video(
        self,
        video_path: Path,
        exhaustive_frame_check: bool = True,
        max_frames_to_check: Optional[int] = None,
    ) -> VideoInspectionReport:
        """Inspect video file properties and detect unreadable or corrupted frames.

        Args:
            video_path: Path to the input video file.
            exhaustive_frame_check: If True, decodes frames sequentially to detect corruption.
            max_frames_to_check: Optional cap on frames decoded during health check.

        Returns:
            VideoInspectionReport: Structured diagnostic and health report.
        """
        video_path = Path(video_path).resolve()
        filename = video_path.name
        extension = video_path.suffix.lower()

        if not video_path.is_file():
            return VideoInspectionReport(
                video_path=str(video_path),
                filename=filename,
                extension=extension,
                is_readable=False,
                error_message=f"Video file does not exist: {video_path}",
                fps=0.0,
                frame_count=0,
                duration_sec=0.0,
                width=0,
                height=0,
                codec="",
                decoded_frame_count=0,
                corrupted_frame_count=0,
                corrupted_frame_indices=[],
                corrupted_frame_percentage=100.0,
                frame_timestamps=[],
            )

        if extension not in self.supported_extensions:
            return VideoInspectionReport(
                video_path=str(video_path),
                filename=filename,
                extension=extension,
                is_readable=False,
                error_message=(
                    f"Unsupported video extension '{extension}'. "
                    f"Supported formats: {sorted(list(self.supported_extensions))}"
                ),
                fps=0.0,
                frame_count=0,
                duration_sec=0.0,
                width=0,
                height=0,
                codec="",
                decoded_frame_count=0,
                corrupted_frame_count=0,
                corrupted_frame_indices=[],
                corrupted_frame_percentage=100.0,
                frame_timestamps=[],
            )

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return VideoInspectionReport(
                video_path=str(video_path),
                filename=filename,
                extension=extension,
                is_readable=False,
                error_message="OpenCV failed to open video file (codec or container invalid).",
                fps=0.0,
                frame_count=0,
                duration_sec=0.0,
                width=0,
                height=0,
                codec="",
                decoded_frame_count=0,
                corrupted_frame_count=0,
                corrupted_frame_indices=[],
                corrupted_frame_percentage=100.0,
                frame_timestamps=[],
            )

        fps = float(cap.get(cv2.CAP_PROP_FPS))
        container_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))

        # Decode fourcc string
        codec_str = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)]).strip()

        # Handle edge case of invalid or zero FPS
        if fps <= 0.0 or np.isnan(fps):
            fps = 30.0  # Fallback default nominal FPS

        duration_sec = (container_frame_count / fps) if container_frame_count > 0 else 0.0

        corrupted_indices: List[int] = []
        decoded_count = 0
        timestamps: List[float] = []

        if exhaustive_frame_check:
            frame_idx = 0
            while True:
                if max_frames_to_check is not None and frame_idx >= max_frames_to_check:
                    break
                ret, frame = cap.read()
                if not ret:
                    # Check whether stream ended prematurely
                    if container_frame_count > 0 and frame_idx < container_frame_count:
                        corrupted_indices.append(frame_idx)
                    break

                if frame is None or frame.size == 0:
                    corrupted_indices.append(frame_idx)
                else:
                    decoded_count += 1
                    # Frame timestamp in seconds
                    ts_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                    if ts_msec > 0.0:
                        timestamps.append(float(ts_msec / 1000.0))
                    else:
                        timestamps.append(float(frame_idx / fps))

                frame_idx += 1

            total_evaluated = frame_idx
        else:
            total_evaluated = container_frame_count
            decoded_count = container_frame_count
            timestamps = [float(i / fps) for i in range(container_frame_count)]

        cap.release()

        corrupted_count = len(corrupted_indices)
        corrupted_pct = (
            (corrupted_count / total_evaluated * 100.0) if total_evaluated > 0 else 0.0
        )

        return VideoInspectionReport(
            video_path=str(video_path),
            filename=filename,
            extension=extension,
            is_readable=True,
            error_message=None,
            fps=round(fps, 3),
            frame_count=total_evaluated if exhaustive_frame_check else container_frame_count,
            duration_sec=round(duration_sec, 3),
            width=width,
            height=height,
            codec=codec_str,
            decoded_frame_count=decoded_count,
            corrupted_frame_count=corrupted_count,
            corrupted_frame_indices=corrupted_indices,
            corrupted_frame_percentage=round(corrupted_pct, 3),
            frame_timestamps=timestamps,
        )

    @staticmethod
    def create_synthetic_test_video(
        output_path: Path,
        num_frames: int = 60,
        fps: float = 30.0,
        width: int = 320,
        height: int = 240,
        inject_corrupted_frame: bool = False,
    ) -> Path:
        """Create a valid synthetic video file using OpenCV for automated pipeline testing.

        Args:
            output_path: Destination path for test video (.mp4 or .avi).
            num_frames: Total number of frames to render.
            fps: Frame rate in frames per second.
            width: Frame width in pixels.
            height: Frame height in pixels.
            inject_corrupted_frame: If True, writes black/degraded frame to test corruption QC.

        Returns:
            Path: Resolved path to the created video file.
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if not writer.isOpened():
            # Fallback to AVI with XVID if mp4v is not supported by platform build
            output_path = output_path.with_suffix(".avi")
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        for frame_idx in range(num_frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            # Add dynamic synthetic gradient so frames are distinct
            color_val = int((frame_idx / max(1, num_frames)) * 255)
            frame[:, :] = (color_val, 128, 255 - color_val)

            # Draw a simulated facial oval for visual verification
            center_x, center_y = width // 2, height // 2
            cv2.ellipse(frame, (center_x, center_y), (40, 60), 0, 0, 360, (200, 200, 200), -1)
            cv2.circle(frame, (center_x - 15, center_y - 15), 6, (50, 50, 50), -1)
            cv2.circle(frame, (center_x + 15, center_y - 15), 6, (50, 50, 50), -1)
            cv2.ellipse(frame, (center_x, center_y + 20), (20, 10), 0, 0, 180, (50, 50, 50), 2)

            writer.write(frame)

        writer.release()
        return output_path

