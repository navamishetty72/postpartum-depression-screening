"""Automated downloader for the trained Text NER v1.3.0 model checkpoint.

Downloads the official ~89.66 MB release artifact from GitHub Releases,
verifies its cryptographic SHA256 checksum, and places it into:
models/text_ner/v1.3.0/text_ner_model.joblib
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

EXPECTED_SHA256 = "9797a6058b8c5500cc989d917184a61a266c12d0335d82db9bc5f3128633d5ef"
EXPECTED_SIZE_BYTES = 94014515

RELEASE_URL = (
    "https://github.com/navamishetty72/postpartum-depression-screening/releases/download/"
    "v1.3.0/text_ner_model.joblib"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = PROJECT_ROOT / "models" / "text_ner" / "v1.3.0"
TARGET_FILE = TARGET_DIR / "text_ner_model.joblib"


def verify_sha256(file_path: Path) -> bool:
    """Compute and verify SHA256 digest of the given file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192 * 1024):
            h.update(chunk)
    digest = h.hexdigest()
    return digest.lower() == EXPECTED_SHA256.lower()


def download_artifact(force: bool = False) -> None:
    """Download and verify the Text NER v1.3.0 model artifact."""
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    if TARGET_FILE.exists() and not force:
        print(f"Checking existing model at: {TARGET_FILE}")
        if verify_sha256(TARGET_FILE):
            print("Existing model artifact matches verified SHA256 checksum! No download needed.")
            return
        else:
            print("Existing file checksum mismatch! Re-downloading...")

    print(f"Downloading Text NER v1.3.0 model ({EXPECTED_SIZE_BYTES / (1024*1024):.2f} MB)...")
    print(f"Source URL: {RELEASE_URL}")

    temp_file = TARGET_FILE.with_suffix(".tmp")
    try:
        urllib.request.urlretrieve(RELEASE_URL, temp_file)
        print("Download complete. Verifying SHA256 checksum...")

        if not verify_sha256(temp_file):
            temp_file.unlink(missing_ok=True)
            print(f"ERROR: SHA256 verification failed! Expected {EXPECTED_SHA256}", file=sys.stderr)
            sys.exit(1)

        temp_file.replace(TARGET_FILE)
        print(f"Successfully installed verified model artifact at:\n  {TARGET_FILE}")

    except Exception as e:
        temp_file.unlink(missing_ok=True)
        print(f"ERROR: Download failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    force_download = "--force" in sys.argv
    download_artifact(force=force_download)
