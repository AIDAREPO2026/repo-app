import hashlib
import struct
from pathlib import Path

from app.core.constants import LOGIN_TYPES
from scripts.make_test_files import FILES_DIR, make_eicar, make_large_video, make_oversized_image
from tests.fixture_data import DISCOMS, LOGINS

SAMPLE_FORMATS = ["pdf", "doc", "docx", "xls", "xlsx", "csv", "ppt", "pptx", "jpg", "png", "mp4", "mp3"]
# Published SHA-256 of the 68-byte EICAR test string.
EICAR_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"


def test_p0_qa_02_one_sample_per_format() -> None:
    for extension in SAMPLE_FORMATS:
        assert (FILES_DIR / f"sample.{extension}").stat().st_size > 0
    assert (FILES_DIR / "pdf-renamed.docx").read_bytes().startswith(b"%PDF")


def test_p0_qa_02_fixture_logins_cover_every_type() -> None:
    assert {login.login_type for login in LOGINS} == set(LOGIN_TYPES)
    reviewers = [login for login in LOGINS if login.login_type == "reviewer"]
    assert sorted(login.is_alternate for login in reviewers) == [False, True]
    discom_codes = {discom.code for discom in DISCOMS}
    for login in LOGINS:
        assert login.email.endswith(".example")
        assert login.discom_code is None or login.discom_code in discom_codes


def test_p0_qa_02_oversized_image_is_a_padded_jpeg(tmp_path: Path) -> None:
    image = make_oversized_image(tmp_path / "big.jpg", size=50_000)

    content = image.read_bytes()
    assert len(content) == 50_000
    assert content.startswith(b"\xff\xd8\xff")


def test_p0_qa_02_large_video_ends_in_a_free_box(tmp_path: Path) -> None:
    video = make_large_video(tmp_path / "big.mp4", size=100_000)

    content = video.read_bytes()
    assert len(content) == 100_000
    # Walk the top-level MP4 boxes: they must add up to the file size, ending with 'free'.
    position = 0
    box_type = b""
    while position < len(content):
        box_size = struct.unpack(">I", content[position : position + 4])[0]
        box_type = content[position + 4 : position + 8]
        position += box_size
    assert position == len(content)
    assert box_type == b"free"


def test_p0_qa_02_eicar_is_the_standard_test_string(tmp_path: Path) -> None:
    eicar = make_eicar(tmp_path / "eicar.txt")

    assert hashlib.sha256(eicar.read_bytes()).hexdigest() == EICAR_SHA256
