"""Write the large and antivirus test files into tests/files/generated/, which git ignores.

    uv run python scripts/make_test_files.py               # all three files
    uv run python scripts/make_test_files.py --skip-video  # without the 1 GB MP4

They are built on demand rather than committed: two are too big for git, and antivirus
tools on laptops would quarantine a committed EICAR file in every checkout.
"""

import base64
import struct
import sys
from pathlib import Path
from typing import BinaryIO

FILES_DIR = Path(__file__).resolve().parent.parent / "tests" / "files"
GENERATED_DIR = FILES_DIR / "generated"
MB = 1024 * 1024
CHUNK = MB

# D-01: one MB over the 20 MB image limit, so uploads must refuse it.
OVERSIZED_IMAGE_BYTES = 21 * MB
# FR-3.5, AC-11: a large but allowed video, for the resumable upload test.
LARGE_VIDEO_BYTES = 1000 * MB

# The standard EICAR antivirus test string (eicar.org). It is harmless, but scanners flag it
# on sight, so it is stored base64-encoded to keep this script itself from being quarantined.
EICAR_BASE64 = "WDVPIVAlQEFQWzRcUFpYNTQoUF4pN0NDKTd9JEVJQ0FSLVNUQU5EQVJELUFOVElWSVJVUy1URVNULUZJTEUhJEgrSCo="


def write_zeros(file: BinaryIO, count: int) -> None:
    """Append count zero bytes, a megabyte at a time, so memory use stays small."""
    while count > 0:
        step = min(count, CHUNK)
        file.write(bytes(step))
        count -= step


def make_oversized_image(target: Path, size: int = OVERSIZED_IMAGE_BYTES) -> Path:
    """Write a real JPEG padded to size. Viewers stop at the end-of-image marker, so it still opens."""
    picture = (FILES_DIR / "sample.jpg").read_bytes()
    with target.open("wb") as file:
        file.write(picture)
        write_zeros(file, size - len(picture))
    return target


def make_large_video(target: Path, size: int = LARGE_VIDEO_BYTES) -> Path:
    """Write a real MP4 followed by a 'free' box that fills it to size. Players skip free boxes."""
    video = (FILES_DIR / "sample.mp4").read_bytes()
    free_box_size = size - len(video)
    with target.open("wb") as file:
        file.write(video)
        file.write(struct.pack(">I", free_box_size) + b"free")
        write_zeros(file, free_box_size - 8)
    return target


def make_eicar(target: Path) -> Path:
    """Write the EICAR test file, which every antivirus scanner reports as infected."""
    target.write_bytes(base64.b64decode(EICAR_BASE64))
    return target


def main() -> int:
    """Write every generated file, skipping the video when asked."""
    GENERATED_DIR.mkdir(exist_ok=True)
    made = [
        make_oversized_image(GENERATED_DIR / "image-21mb.jpg"),
        make_eicar(GENERATED_DIR / "eicar.txt"),
    ]
    if "--skip-video" not in sys.argv:
        made.append(make_large_video(GENERATED_DIR / "video-1gb.mp4"))
    for path in made:
        print(f"{path.relative_to(FILES_DIR.parent.parent)}: {path.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
