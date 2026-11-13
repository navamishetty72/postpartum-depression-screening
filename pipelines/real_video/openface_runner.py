"""OpenFace 2.x execution wrapper, dependency checker, and CSV extraction parser.

Detects OpenFace binaries on the host system, runs FeatureExtraction CLI with
standard facial Action Unit, head pose, and gaze flags, and parses raw OpenFace CSVs.

SCIENTIFIC RESTRICTION:
If OpenFace is unavailable, this module halts and reports the missing dependency
clearly with actionable installation instructions. It does NOT invent or fabricate
synthetic numbers to substitute for unextracted facial measurements.
"""

import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from .config import (
    OPENFACE_ACTION_UNITS,
    OPENFACE_GAZE,
    OPENFACE_HEAD_POSE,
    OPENFACE_METADATA_COLS,
    OPENFACE_TRACKING,
)


class OpenFaceNotFoundError(FileNotFoundError):
    """Raised when OpenFace 2.x FeatureExtraction executable cannot be found."""

    def __init__(self, message: Optional[str] = None) -> None:
        default_msg = (
            "OpenFace 2.x executable ('FeatureExtraction' or 'FeatureExtraction.exe') was not found.\n"
            "To install OpenFace 2.x:\n"
            "  1. Windows: Download pre-compiled OpenFace 2.2.0 from:\n"
            "     https://github.com/TadasBaltrusaitis/OpenFace/releases\n"
            "     Extract to C:\\OpenFace\\ and set OPENFACE_BIN_PATH=C:\\OpenFace\\FeatureExtraction.exe\n"
            "  2. Linux (Ubuntu/Debian): Follow build steps at:\n"
            "     https://github.com/TadasBaltrusaitis/OpenFace/wiki/Unix-Installation\n"
            "  3. Docker (Recommended for cross-platform execution):\n"
            "     docker pull algebr/openface:latest\n"
            "     docker run -v /data:/data algebr/openface:latest FeatureExtraction -f /data/video.mp4\n"
            "SCIENTIFIC RULE: Measurements must not be fabricated when OpenFace is unavailable."
        )
        super().__init__(message or default_msg)


class OpenFaceRunner:
    """Manages OpenFace 2.x discovery, CLI execution, and output CSV parsing."""

    def __init__(self, binary_path: Optional[Union[str, Path]] = None) -> None:
        self.explicit_binary_path: Optional[Path] = (
            Path(binary_path).resolve() if binary_path is not None else None
        )
        self.binary_path: Optional[Path] = self.find_openface_binary(binary_path)

    @staticmethod
    def is_valid_executable(path: Union[str, Path]) -> bool:
        """Check if path exists, is a regular file, and has executable permissions or extension."""
        try:
            p = Path(path).resolve()
            if not p.is_file():
                return False
            if os.access(p, os.X_OK):
                if os.name == "nt":
                    pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
                    valid_exts = {ext.strip().lower() for ext in pathext if ext.strip()} | {".exe", ".bat", ".cmd"}
                    return p.suffix.lower() in valid_exts
                return True
            return False
        except (PermissionError, OSError):
            return False

    @classmethod
    def find_openface_binary(cls, custom_path: Optional[Union[str, Path]] = None) -> Optional[Path]:
        """Locate OpenFace FeatureExtraction executable across paths and environment variables.

        Search priority:
        1. Explicitly provided custom_path argument:
           - Must be checked directly.
           - If it does not exist or is not executable, returns None.
           - Never falls back to environment variables or automatic discovery when an explicit
             path is supplied.
        2. Automatic discovery (only when custom_path is None):
           a. OPENFACE_BIN_PATH or OPENFACE_EXE environment variables.
           b. System PATH via shutil.which().
           c. Standard platform installation directories on Windows and Unix.

        Returns:
            Optional[Path]: Resolved path to executable if found, else None.
        """
        # 1. Custom path explicitly supplied (strict: no fallback)
        if custom_path is not None:
            p = Path(custom_path).resolve()
            if cls.is_valid_executable(p):
                return p
            return None

        # 2. Automatic discovery: Environment variables
        for env_var in ("OPENFACE_BIN_PATH", "OPENFACE_EXE"):
            val = os.environ.get(env_var)
            if val:
                p = Path(val).resolve()
                if cls.is_valid_executable(p):
                    return p

        # 3. Automatic discovery: System PATH lookup
        for binary_name in ("FeatureExtraction.exe", "FeatureExtraction", "OpenFaceOffline.exe"):
            found = shutil.which(binary_name)
            if found:
                p = Path(found).resolve()
                if cls.is_valid_executable(p):
                    return p

        # 4. Automatic discovery: Standard installation directories on Windows
        user_profile = Path(os.environ.get("USERPROFILE", "C:/Users/Default"))
        standard_windows_paths = [
            user_profile / "Downloads" / "OpenFace_2.2.0_win_x64" / "OpenFace_2.2.0_win_x64" / "FeatureExtraction.exe",
            user_profile / "Downloads" / "OpenFace_2.2.0_win_x64" / "FeatureExtraction.exe",
            Path("C:/OpenFace/FeatureExtraction.exe"),
            Path("C:/Program Files/OpenFace/FeatureExtraction.exe"),
            Path("C:/tools/OpenFace/FeatureExtraction.exe"),
            Path("C:/OpenFace_2.2.0_win_x64/FeatureExtraction.exe"),
            user_profile / "OpenFace" / "FeatureExtraction.exe",
        ]
        for candidate in standard_windows_paths:
            if cls.is_valid_executable(candidate):
                return candidate

        # 5. Automatic discovery: Standard Unix paths
        standard_unix_paths = [
            Path("/usr/local/bin/FeatureExtraction"),
            Path("/opt/openface/build/bin/FeatureExtraction"),
            Path("/usr/bin/FeatureExtraction"),
        ]
        for candidate in standard_unix_paths:
            if cls.is_valid_executable(candidate):
                return candidate

        return None

    def check_availability(self) -> Dict[str, Any]:
        """Check whether OpenFace 2.x is available and return diagnostic status."""
        if self.binary_path and self.is_valid_executable(self.binary_path):
            return {
                "available": True,
                "binary_path": str(self.binary_path),
                "version": "2.x",
                "status": "READY",
                "message": f"OpenFace executable verified at {self.binary_path}",
            }
        else:
            if self.explicit_binary_path is not None:
                message = (
                    f"Explicitly specified OpenFace executable at '{self.explicit_binary_path}' "
                    f"does not exist or is not executable. Fallback to automatic discovery is disabled."
                )
            else:
                message = (
                    "OpenFace 2.x FeatureExtraction executable is not installed or not on PATH. "
                    "Set OPENFACE_BIN_PATH environment variable or install OpenFace."
                )
            return {
                "available": False,
                "binary_path": None,
                "version": None,
                "status": "NOT_FOUND",
                "message": message,
            }

    def run_extraction(
        self,
        video_path: Path,
        output_dir: Path,
        timeout_sec: int = 600,
        extra_flags: Optional[List[str]] = None,
    ) -> Path:
        """Execute OpenFace FeatureExtraction on a single video recording.

        Args:
            video_path: Path to input video file.
            output_dir: Directory where raw OpenFace CSV and outputs will be written.
            timeout_sec: Maximum execution timeout in seconds.
            extra_flags: Optional additional CLI flags for FeatureExtraction.

        Returns:
            Path: Path to the generated OpenFace CSV file.

        Raises:
            OpenFaceNotFoundError: If OpenFace binary is not available.
            RuntimeError: If OpenFace execution fails or output CSV is missing.
        """
        if not self.binary_path or not self.is_valid_executable(self.binary_path):
            raise OpenFaceNotFoundError()

        video_path = Path(video_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Standard OpenFace extraction command: 2D landmarks, 3D head pose, eye gaze, Action Units
        cmd = [
            str(self.binary_path),
            "-f",
            str(video_path),
            "-out_dir",
            str(output_dir),
            "-2Dfp",
            "-pose",
            "-gaze",
            "-aus",
        ]
        if extra_flags:
            cmd.extend(extra_flags)

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            check=False,
            cwd=str(self.binary_path.parent),
        )

        stem = video_path.stem
        expected_csv = output_dir / f"{stem}.csv"

        if result.returncode != 0:
            raise RuntimeError(
                f"OpenFace FeatureExtraction failed with exit code {result.returncode}.\n"
                f"STDERR: {result.stderr}\nSTDOUT: {result.stdout}"
            )

        if not expected_csv.is_file():
            raise RuntimeError(
                f"OpenFace FeatureExtraction finished but expected CSV was not created: {expected_csv}"
            )

        return expected_csv

    @staticmethod
    def parse_openface_csv(csv_path: Path) -> pd.DataFrame:
        """Parse, clean header whitespace, and validate an OpenFace 2.x output CSV.

        OpenFace CSVs typically contain leading spaces in column headers
        (e.g., ' confidence', ' success', ' AU01_r'). This method standardizes them.

        Args:
            csv_path: Path to raw OpenFace CSV file.

        Returns:
            pd.DataFrame: Cleaned DataFrame with stripped column headers and validated schemas.
        """
        csv_path = Path(csv_path).resolve()
        if not csv_path.is_file():
            raise FileNotFoundError(f"OpenFace CSV file not found: {csv_path}")

        df = pd.read_csv(csv_path)

        # Strip whitespace from column headers
        df.columns = df.columns.astype(str).str.strip()

        # Check required tracking columns
        for col in OPENFACE_TRACKING:
            if col not in df.columns:
                raise ValueError(f"Missing required OpenFace tracking column '{col}' in {csv_path.name}")

        return df

    @staticmethod
    def check_feature_availability(df: pd.DataFrame) -> Dict[str, Any]:
        """Inspect a parsed OpenFace DataFrame and report which feature sets are present."""
        cols = set(df.columns)
        aus_present = [au for au in OPENFACE_ACTION_UNITS if au in cols]
        pose_present = [p for p in OPENFACE_HEAD_POSE if p in cols]
        gaze_present = [g for g in OPENFACE_GAZE if g in cols]
        tracking_present = [t for t in OPENFACE_TRACKING if t in cols]

        return {
            "total_columns": len(cols),
            "total_frames": len(df),
            "action_units_present": aus_present,
            "action_units_missing": [au for au in OPENFACE_ACTION_UNITS if au not in cols],
            "head_pose_present": pose_present,
            "head_pose_missing": [p for p in OPENFACE_HEAD_POSE if p not in cols],
            "gaze_present": gaze_present,
            "gaze_missing": [g for g in OPENFACE_GAZE if g not in cols],
            "tracking_present": tracking_present,
            "is_complete_schema": (
                len(aus_present) == len(OPENFACE_ACTION_UNITS)
                and len(pose_present) == len(OPENFACE_HEAD_POSE)
                and len(gaze_present) == len(OPENFACE_GAZE)
                and len(tracking_present) == len(OPENFACE_TRACKING)
            ),
        }

