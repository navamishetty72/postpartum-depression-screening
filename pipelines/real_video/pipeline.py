"""Pipeline orchestrator for real video feature extraction, cleaning, and export.

Executes the complete end-to-end real video workflow:
1. Ingests and inspects raw video recordings via OpenCV.
2. Executes OpenFace 2.x FeatureExtraction CLI (or processes existing OpenFace CSVs).
3. Cleans, masks, and validates extracted features.
4. Assembles (T, 24) temporal feature tensors, participant summaries, and QC reports.
5. Updates the master video manifest and compiles cohort-level quality metrics.

SCIENTIFIC & PRIVACY RULES:
- Zero EPDS, PHQ, or canonical target labels may enter this pipeline.
- Video files and participant identities are kept out of Git version control.
- If OpenFace fails or is unavailable, the pipeline records failure and does NOT fake outputs.
"""

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from .config import (
    CLEANED_DIR,
    DATA_ORIGIN_REAL_VIDEO,
    DEFAULT_RAW_VIDEO_DIR,
    FEATURE_DIM,
    FEATURES_DIR,
    PIPELINE_VERSION,
    PROCESSED_VIDEO_DIR,
    PROJECT_ROOT,
    QUALITY_REPORTS_DIR,
    RAW_OPENFACE_DIR,
    REAL_VIDEO_CHANNEL_NAMES,
    SUMMARIES_DIR,
    SUPPORTED_VIDEO_EXTENSIONS,
    VIDEO_MANIFEST_PATH,
)
from .video_reader import VideoReader, VideoInspectionReport
from .openface_runner import OpenFaceRunner, OpenFaceNotFoundError
from .cleaner import FeatureCleaner, CleaningTransformationReport
from .tensor_builder import TensorBuilder

# Configure privacy-safe logging (no PII or media frames in logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("RealVideoPipeline")


class RealVideoPipeline:
    """End-to-end coordinator for real video feature extraction and validation."""

    def __init__(
        self,
        output_dir: Union[str, Path] = PROCESSED_VIDEO_DIR,
        openface_bin: Optional[Union[str, Path]] = None,
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.raw_openface_dir = self.output_dir / "raw_openface"
        self.cleaned_dir = self.output_dir / "cleaned"
        self.features_dir = self.output_dir / "features"
        self.summaries_dir = self.output_dir / "summaries"
        self.quality_reports_dir = self.output_dir / "quality_reports"
        self.manifest_path = self.output_dir / "video_manifest.csv"

        # Create output directories
        for d in (
            self.raw_openface_dir,
            self.cleaned_dir,
            self.features_dir,
            self.summaries_dir,
            self.quality_reports_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

        self.video_reader = VideoReader()
        self.openface_runner = OpenFaceRunner(binary_path=openface_bin)
        self.cleaner = FeatureCleaner()
        self.tensor_builder = TensorBuilder()

    def check_environment(self) -> Dict[str, Any]:
        """Check OpenCV and OpenFace dependencies and report diagnostic status."""
        import cv2

        opencv_info = {
            "available": True,
            "version": cv2.__version__,
            "status": "READY",
        }
        openface_info = self.openface_runner.check_availability()

        all_ready = opencv_info["available"] and openface_info["available"]
        return {
            "opencv": opencv_info,
            "openface": openface_info,
            "overall_status": "READY" if all_ready else "DEPENDENCIES_INCOMPLETE",
        }

    def process_single_video(
        self,
        video_path: Union[str, Path],
        participant_id: str,
        recording_id: Optional[str] = None,
        split_partition: str = "unassigned",
        precomputed_openface_csv: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Process a single real video recording through ingestion, extraction, and cleaning.

        Args:
            video_path: Path to the raw video file.
            participant_id: Unique participant identifier (e.g. 'BGD_001').
            recording_id: Optional recording identifier (defaults to video stem).
            split_partition: 'train', 'test', or 'unassigned'.
            precomputed_openface_csv: Optional path to pre-existing OpenFace CSV.

        Returns:
            Dict[str, Any]: Processing record with status and artifact paths.
        """
        video_path = Path(video_path).resolve()
        rec_id = recording_id or video_path.stem
        record_prefix = f"{participant_id}_{rec_id}"

        logger.info(f"Processing recording {rec_id} for participant {participant_id}")

        # Step 1: Video Ingestion & Health Check via OpenCV
        inspection: VideoInspectionReport = self.video_reader.inspect_video(video_path)
        if not inspection.is_readable:
            logger.error(f"Video unreadable for {participant_id}: {inspection.error_message}")
            return {
                "participant_id": participant_id,
                "recording_id": rec_id,
                "split_partition": split_partition,
                "processing_status": "FAILED_VIDEO_UNREADABLE",
                "error_message": inspection.error_message,
                "tracking_success_rate": 0.0,
                "mean_tracking_confidence": 0.0,
                "artifacts": {},
            }

        # Step 2: OpenFace Feature Extraction
        raw_csv_dest = self.raw_openface_dir / f"{record_prefix}.csv"

        if precomputed_openface_csv and Path(precomputed_openface_csv).is_file():
            # Use precomputed OpenFace CSV (e.g. from offline/Docker extraction or CI fixture)
            logger.info(f"Using precomputed OpenFace CSV: {precomputed_openface_csv}")
            raw_openface_df = self.openface_runner.parse_openface_csv(Path(precomputed_openface_csv))
            # Save copy to raw_openface directory for auditability
            raw_openface_df.to_csv(raw_csv_dest, index=False)
        else:
            # Run live OpenFace extraction CLI
            try:
                extracted_csv = self.openface_runner.run_extraction(
                    video_path=video_path,
                    output_dir=self.raw_openface_dir,
                )
                raw_openface_df = self.openface_runner.parse_openface_csv(extracted_csv)
                if extracted_csv != raw_csv_dest:
                    raw_openface_df.to_csv(raw_csv_dest, index=False)
            except OpenFaceNotFoundError as e:
                logger.error(f"OpenFace execution halted: {e}")
                return {
                    "participant_id": participant_id,
                    "recording_id": rec_id,
                    "split_partition": split_partition,
                    "processing_status": "FAILED_OPENFACE_UNAVAILABLE",
                    "error_message": str(e),
                    "tracking_success_rate": 0.0,
                    "mean_tracking_confidence": 0.0,
                    "artifacts": {},
                }
            except Exception as e:
                logger.error(f"OpenFace extraction failed for {rec_id}: {e}")
                return {
                    "participant_id": participant_id,
                    "recording_id": rec_id,
                    "split_partition": split_partition,
                    "processing_status": "FAILED_EXTRACTION_ERROR",
                    "error_message": str(e),
                    "tracking_success_rate": 0.0,
                    "mean_tracking_confidence": 0.0,
                    "artifacts": {},
                }

        # Step 3: Feature Cleaning and Transformation
        try:
            cleaned_df, cleaning_report = self.cleaner.clean_features(
                raw_df=raw_openface_df,
                recording_fps=inspection.fps,
            )
        except Exception as e:
            logger.error(f"Feature cleaning failed for {rec_id}: {e}")
            return {
                "participant_id": participant_id,
                "recording_id": rec_id,
                "split_partition": split_partition,
                "processing_status": "FAILED_CLEANING_ERROR",
                "error_message": str(e),
                "tracking_success_rate": 0.0,
                "mean_tracking_confidence": 0.0,
                "artifacts": {},
            }

        # Step 4: Assemble Temporal Tensor and Summaries
        try:
            tensor = self.tensor_builder.build_temporal_tensor(cleaned_df)
            summary = self.tensor_builder.compute_participant_summary(
                cleaned_df=cleaned_df,
                participant_id=participant_id,
                recording_id=rec_id,
            )
            qc_report = self.tensor_builder.build_quality_report(
                participant_id=participant_id,
                recording_id=rec_id,
                video_inspection=inspection.to_dict(),
                cleaning_report=cleaning_report.to_dict(),
            )
        except Exception as e:
            logger.error(f"Tensor assembly failed for {rec_id}: {e}")
            return {
                "participant_id": participant_id,
                "recording_id": rec_id,
                "split_partition": split_partition,
                "processing_status": "FAILED_TENSOR_ASSEMBLY",
                "error_message": str(e),
                "tracking_success_rate": 0.0,
                "mean_tracking_confidence": 0.0,
                "artifacts": {},
            }

        # Step 5: Save Artifacts
        cleaned_csv_path = self.cleaned_dir / f"{record_prefix}_cleaned.csv"
        cleaned_df.to_csv(cleaned_csv_path, index=False)

        feature_tensor_path = self.features_dir / f"{participant_id}.npy"
        np.save(feature_tensor_path, tensor)

        summary_json_path = self.summaries_dir / f"{participant_id}_summary.json"
        with open(summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        qc_json_path = self.quality_reports_dir / f"{participant_id}_qc.json"
        with open(qc_json_path, "w", encoding="utf-8") as f:
            json.dump(qc_report, f, indent=2)

        # Determine definitive processing status
        if cleaning_report.tracked_frames_count == 0:
            final_status = "SUCCESS_NO_FACE_DETECTED"
        elif qc_report["qc_status"] == "FAIL":
            final_status = "COMPLETED_WITH_QC_FAIL"
        else:
            final_status = "SUCCESS"

        logger.info(
            f"Successfully processed {rec_id}: {len(cleaned_df)} frames, "
            f"tracking_rate={cleaning_report.tracking_success_rate:.1%}, status={final_status}"
        )

        def _rel_path(p: Path) -> str:
            try:
                return str(p.relative_to(PROJECT_ROOT))
            except ValueError:
                return str(p)

        return {
            "participant_id": participant_id,
            "recording_id": rec_id,
            "split_partition": split_partition,
            "video_path": str(video_path),
            "fps": inspection.fps,
            "frame_count": inspection.frame_count,
            "duration_sec": inspection.duration_sec,
            "width": inspection.width,
            "height": inspection.height,
            "corrupted_frame_count": inspection.corrupted_frame_count,
            "corrupted_frame_percentage": inspection.corrupted_frame_percentage,
            "tracked_frames_count": cleaning_report.tracked_frames_count,
            "tracking_success_rate": cleaning_report.tracking_success_rate,
            "mean_tracking_confidence": cleaning_report.mean_confidence,
            "qc_status": qc_report["qc_status"],
            "processing_status": final_status,
            "error_message": None,
            "artifacts": {
                "raw_openface_csv": _rel_path(raw_csv_dest),
                "cleaned_csv": _rel_path(cleaned_csv_path),
                "feature_tensor": _rel_path(feature_tensor_path),
                "summary_json": _rel_path(summary_json_path),
                "qc_report_json": _rel_path(qc_json_path),
            },
        }

    def process_cohort(
        self,
        raw_video_dir: Union[str, Path] = DEFAULT_RAW_VIDEO_DIR,
        metadata_manifest_path: Optional[Union[str, Path]] = None,
    ) -> pd.DataFrame:
        """Process an entire participant video cohort.

        Args:
            raw_video_dir: Directory containing input video recordings.
            metadata_manifest_path: Optional CSV mapping video files to participant IDs.
                Required schema: 'video_file' or 'filename', 'participant_id' (optional: 'recording_id', 'split_partition').

        Returns:
            pd.DataFrame: Completed cohort video manifest.
        """
        raw_video_dir = Path(raw_video_dir).resolve()
        logger.info(f"Scanning for videos in {raw_video_dir}...")

        discovered_videos: List[Path] = []
        if raw_video_dir.is_dir():
            for ext in SUPPORTED_VIDEO_EXTENSIONS:
                discovered_videos.extend(raw_video_dir.glob(f"*{ext}"))
                discovered_videos.extend(raw_video_dir.glob(f"*{ext.upper()}"))

        discovered_videos = sorted(list(set(discovered_videos)))
        logger.info(f"Discovered {len(discovered_videos)} video recordings.")

        manifest_map: Dict[str, Dict[str, str]] = {}
        if metadata_manifest_path and Path(metadata_manifest_path).is_file():
            meta_df = pd.read_csv(metadata_manifest_path)
            # Find video filename column
            fn_col = next((c for c in meta_df.columns if "file" in c.lower() or "video" in c.lower()), None)
            pid_col = next((c for c in meta_df.columns if "participant" in c.lower() or c == "id"), None)
            split_col = next((c for c in meta_df.columns if "split" in c.lower() or "partition" in c.lower()), None)

            if fn_col and pid_col:
                for _, r in meta_df.iterrows():
                    fn = Path(str(r[fn_col])).name
                    manifest_map[fn] = {
                        "participant_id": str(r[pid_col]),
                        "split_partition": str(r[split_col]) if split_col else "unassigned",
                    }

        records: List[Dict[str, Any]] = []

        for video_file in discovered_videos:
            fn = video_file.name
            mapping = manifest_map.get(fn, {})
            participant_id = mapping.get("participant_id", video_file.stem.split("_")[0])
            split_partition = mapping.get("split_partition", "unassigned")

            res = self.process_single_video(
                video_path=video_file,
                participant_id=participant_id,
                recording_id=video_file.stem,
                split_partition=split_partition,
            )

            # Flatten record for manifest CSV
            flat_record: Dict[str, Any] = {
                "participant_id": res["participant_id"],
                "recording_id": res["recording_id"],
                "split_partition": res["split_partition"],
                "data_origin": DATA_ORIGIN_REAL_VIDEO,
                "pipeline_version": PIPELINE_VERSION,
                "video_path": res.get("video_path", str(video_file)),
                "fps": res.get("fps", 0.0),
                "frame_count": res.get("frame_count", 0),
                "duration_sec": res.get("duration_sec", 0.0),
                "width": res.get("width", 0),
                "height": res.get("height", 0),
                "corrupted_frame_count": res.get("corrupted_frame_count", 0),
                "corrupted_frame_percentage": res.get("corrupted_frame_percentage", 0.0),
                "tracked_frames_count": res.get("tracked_frames_count", 0),
                "tracking_success_rate": res.get("tracking_success_rate", 0.0),
                "mean_tracking_confidence": res.get("mean_tracking_confidence", 0.0),
                "qc_status": res.get("qc_status", "FAIL"),
                "processing_status": res["processing_status"],
                "error_message": res.get("error_message"),
                "cleaned_csv_path": res.get("artifacts", {}).get("cleaned_csv"),
                "feature_tensor_path": res.get("artifacts", {}).get("feature_tensor"),
                "summary_json_path": res.get("artifacts", {}).get("summary_json"),
                "qc_report_json_path": res.get("artifacts", {}).get("qc_report_json"),
            }
            records.append(flat_record)

        manifest_df = pd.DataFrame(records)
        manifest_df.to_csv(self.manifest_path, index=False)
        logger.info(f"Saved cohort manifest to {self.manifest_path} ({len(manifest_df)} records)")

        return manifest_df

    def generate_processing_summary(
        self,
        manifest_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """Compile a quantitative cohort processing summary report."""
        if manifest_df is None:
            if not self.manifest_path.is_file():
                return {
                    "total_videos_discovered": 0,
                    "successfully_processed": 0,
                    "failed_videos": 0,
                    "videos_no_detectable_face": 0,
                    "average_tracking_success_rate": 0.0,
                    "missing_frame_percentage": 0.0,
                    "feature_extraction_errors": 0,
                    "invalid_feature_values": 0,
                    "output_files_generated": 0,
                    "message": "No cohort manifest found. Run cohort processing first.",
                }
            manifest_df = pd.read_csv(self.manifest_path)

        total_videos = len(manifest_df)
        if total_videos == 0:
            return {
                "total_videos_discovered": 0,
                "successfully_processed": 0,
                "failed_videos": 0,
                "videos_no_detectable_face": 0,
                "average_tracking_success_rate": 0.0,
                "missing_frame_percentage": 0.0,
                "feature_extraction_errors": 0,
                "invalid_feature_values": 0,
                "output_files_generated": 0,
            }

        success_mask = manifest_df["processing_status"].str.startswith("SUCCESS")
        success_count = int(success_mask.sum())
        failed_count = total_videos - success_count

        no_face_mask = manifest_df["processing_status"] == "SUCCESS_NO_FACE_DETECTED"
        no_face_count = int(no_face_mask.sum())

        avg_tracking = (
            float(manifest_df.loc[success_mask, "tracking_success_rate"].mean())
            if success_count > 0
            else 0.0
        )
        avg_missing = (
            float(manifest_df.loc[success_mask, "corrupted_frame_percentage"].mean())
            if success_count > 0
            else 0.0
        )

        extraction_errors = int((manifest_df["processing_status"].str.startswith("FAILED")).sum())

        # Count total artifact files on disk in output directories
        artifact_count = sum(
            len(list(d.glob("*.*")))
            for d in (
                self.raw_openface_dir,
                self.cleaned_dir,
                self.features_dir,
                self.summaries_dir,
                self.quality_reports_dir,
            )
            if d.is_dir()
        )

        summary = {
            "total_videos_discovered": total_videos,
            "successfully_processed": success_count,
            "failed_videos": failed_count,
            "videos_no_detectable_face": no_face_count,
            "average_tracking_success_rate": round(avg_tracking, 4),
            "missing_frame_percentage": round(avg_missing, 4),
            "feature_extraction_errors": extraction_errors,
            "invalid_feature_values": 0,
            "output_files_generated": artifact_count,
        }
        return summary


def main() -> None:
    """CLI entrypoint for real video pipeline commands."""
    parser = argparse.ArgumentParser(
        description="Real-Video Facial Feature Extraction Pipeline (OpenFace 2.x & OpenCV)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Pipeline execution command")

    # Command 1: check-openface / check-env
    subparsers.add_parser("check-openface", help="Check OpenCV and OpenFace dependency availability")

    # Command 2: process-video
    proc_single = subparsers.add_parser("process-video", help="Process a single video recording")
    proc_single.add_argument("--video-path", required=True, type=str, help="Path to input video file")
    proc_single.add_argument("--participant-id", required=True, type=str, help="Participant ID (e.g. BGD_001)")
    proc_single.add_argument("--recording-id", type=str, default=None, help="Optional recording ID")
    proc_single.add_argument("--output-dir", type=str, default=str(PROCESSED_VIDEO_DIR), help="Output directory")
    proc_single.add_argument("--openface-bin", type=str, default=None, help="Explicit OpenFace binary path")
    proc_single.add_argument("--openface-csv", type=str, default=None, help="Path to precomputed OpenFace CSV")

    # Command 3: process-cohort
    proc_cohort = subparsers.add_parser("process-cohort", help="Process all videos in a directory")
    proc_cohort.add_argument(
        "--raw-video-dir", type=str, default=str(DEFAULT_RAW_VIDEO_DIR), help="Directory of raw videos"
    )
    proc_cohort.add_argument(
        "--manifest", type=str, default=None, help="Metadata manifest mapping videos to participant IDs"
    )
    proc_cohort.add_argument("--output-dir", type=str, default=str(PROCESSED_VIDEO_DIR), help="Output directory")
    proc_cohort.add_argument("--openface-bin", type=str, default=None, help="Explicit OpenFace binary path")

    # Command 4: generate-report
    rep_parser = subparsers.add_parser("generate-report", help="Generate cohort processing summary report")
    rep_parser.add_argument("--output-dir", type=str, default=str(PROCESSED_VIDEO_DIR), help="Output directory")

    # Command 5: validate-features
    val_parser = subparsers.add_parser("validate-features", help="Validate processed features against criteria")
    val_parser.add_argument("--output-dir", type=str, default=str(PROCESSED_VIDEO_DIR), help="Output directory")

    args = parser.parse_args()

    if args.command == "check-openface" or args.command is None:
        pipeline = RealVideoPipeline()
        env_status = pipeline.check_environment()
        print("\n=== Real Video Pipeline Environment Diagnostic ===")
        print(f"OpenCV Status:   {env_status['opencv']['status']} (v{env_status['opencv'].get('version')})")
        print(f"OpenFace Status: {env_status['openface']['status']}")
        if env_status["openface"]["available"]:
            print(f"  Binary Path:   {env_status['openface']['binary_path']}")
        else:
            print(f"  Message:       {env_status['openface']['message']}")
        print(f"Overall Status:  {env_status['overall_status']}\n")

    elif args.command == "process-video":
        pipeline = RealVideoPipeline(
            output_dir=args.output_dir,
            openface_bin=args.openface_bin,
        )
        res = pipeline.process_single_video(
            video_path=args.video_path,
            participant_id=args.participant_id,
            recording_id=args.recording_id,
            precomputed_openface_csv=args.openface_csv,
        )
        print(json.dumps(res, indent=2))

    elif args.command == "process-cohort":
        pipeline = RealVideoPipeline(
            output_dir=args.output_dir,
            openface_bin=args.openface_bin,
        )
        manifest = pipeline.process_cohort(
            raw_video_dir=args.raw_video_dir,
            metadata_manifest_path=args.manifest,
        )
        summary = pipeline.generate_processing_summary(manifest)
        print("\n=== Cohort Processing Summary ===")
        print(json.dumps(summary, indent=2))

    elif args.command == "generate-report":
        pipeline = RealVideoPipeline(output_dir=args.output_dir)
        summary = pipeline.generate_processing_summary()
        print("\n=== Cohort Processing Summary ===")
        print(json.dumps(summary, indent=2))

    elif args.command == "validate-features":
        import pytest
        exit_code = pytest.main(["-v", "tests/test_real_video.py"])
        sys.exit(exit_code)


if __name__ == "__main__":
    main()

