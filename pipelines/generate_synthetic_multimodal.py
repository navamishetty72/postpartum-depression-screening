"""Script to generate all synthetic multimodal datasets for testing and benchmarks."""

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.synthetic_audio.generator import run_generation as generate_audio
from pipelines.synthetic_text.generator import run_generation as generate_text
from pipelines.synthetic_video.generator import run_generation as generate_video
from pipelines.synthetic_video.generator_v2 import run_generation_v2 as generate_video_v2
from pipelines.synthetic_video_v3.generator_v3 import run_generation_v3 as generate_video_v3


def main():
    print("Generating synthetic audio dataset...")
    generate_audio()
    print("Generating synthetic text dataset...")
    generate_text()
    print("Generating synthetic video v1 dataset...")
    generate_video()
    print("Generating synthetic video v2 dataset...")
    generate_video_v2()
    print("Generating synthetic video v3 dataset...")
    generate_video_v3()
    print("All synthetic multimodal datasets successfully generated.")


if __name__ == "__main__":
    main()
