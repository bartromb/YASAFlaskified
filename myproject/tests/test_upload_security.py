"""
tests/test_upload_security.py — path traversal in the chunked EDF upload.

`file_id` arrives verbatim from the browser and used to be interpolated into
filenames with an f-string, so it was never a separate os.path.join component
and `../` escaped the upload directory:

    file_id = "../../../tmp/evil"   ->   /tmp/evil_chunk_0

Exploitable by any logged-in user.  Two defences are pinned here:

  1. `validate_chunk_params()` accepts only [A-Za-z0-9_-]{1,64}
  2. `FileUploadHandler._safe_path()` keeps every derived path (chunks,
     _assembled.edf and the final filename) inside upload_dir

Run:
    pytest myproject/tests/test_upload_security.py -v
"""
import io
import os

import pytest
from app import FileUploadHandler, UploadError
from werkzeug.datastructures import FileStorage


@pytest.fixture()
def handler(tmp_path):
    """Handler rooted in a temp upload dir; Redis is never touched here."""
    return FileUploadHandler(str(tmp_path / "uploads"), redis_connection=None)


def _chunk(data=b"data", name="study.edf"):
    return FileStorage(io.BytesIO(data), filename=name)


# ══════════════════════════════════════════════════════════════
#  1. validate_chunk_params — file_id allowlist
# ══════════════════════════════════════════════════════════════

BAD_FILE_IDS = [
    "../x",
    "../../etc/passwd",
    "../../../tmp/evil",
    "a/b",
    "a\\b",
    "",
    None,
    "x" * 65,
    "abc\x00def",
    "..",
    ".",
    "a b",
    "a;rm -rf /",
    "%2e%2e%2fetc",
    "\n",
]


@pytest.mark.parametrize("bad", BAD_FILE_IDS)
def test_validate_chunk_params_rejects_bad_file_id(handler, bad):
    with pytest.raises(UploadError):
        handler.validate_chunk_params(bad, 0, 1, "study.edf")


# The two shapes the frontend actually produces (see templates/upload.html):
#   crypto.randomUUID()
#   `${Date.now()}-${Math.random().toString(36).slice(2)}`
GOOD_FILE_IDS = [
    "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
    "1753740000000-k3j4h5g6x7",
    "abc123",
    "A_B-c9",
    "x" * 64,
]


@pytest.mark.parametrize("good", GOOD_FILE_IDS)
def test_validate_chunk_params_accepts_client_file_ids(handler, good):
    assert handler.validate_chunk_params(good, 0, 1, "study.edf") is True


def test_validate_chunk_params_still_checks_other_args(handler):
    """The pre-existing validation must keep working."""
    fid = "abc123"
    with pytest.raises(UploadError):
        handler.validate_chunk_params(fid, -1, 1, "study.edf")
    with pytest.raises(UploadError):
        handler.validate_chunk_params(fid, 0, 0, "study.edf")
    with pytest.raises(UploadError):
        handler.validate_chunk_params(fid, 2, 2, "study.edf")
    with pytest.raises(UploadError):
        handler.validate_chunk_params(fid, 0, 1, "")


# ══════════════════════════════════════════════════════════════
#  2. _safe_path — containment inside upload_dir
# ══════════════════════════════════════════════════════════════

def test_safe_path_accepts_normal_names(handler):
    base = os.path.realpath(handler.upload_dir)
    assert handler._safe_path("abc123_chunk_0") == os.path.join(base, "abc123_chunk_0")
    assert handler._safe_path("study.edf") == os.path.join(base, "study.edf")


@pytest.mark.parametrize("name", [
    "../escape",
    "../../etc/passwd",
    "sub/../../escape",
    "/etc/passwd",
])
def test_safe_path_rejects_paths_outside_upload_dir(handler, name):
    with pytest.raises(UploadError):
        handler._safe_path(name)


# ══════════════════════════════════════════════════════════════
#  3. The exploit itself must not write outside upload_dir
# ══════════════════════════════════════════════════════════════

def test_save_chunk_cannot_escape_upload_dir(handler, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(UploadError):
        handler.save_chunk("../outside/evil", 0, _chunk(b"pwned"))

    assert not (outside / "evil_chunk_0").exists(), \
        "chunk was written outside the upload directory"


def test_assemble_file_cannot_escape_via_final_filename(handler, tmp_path):
    file_id = "abcdef"
    handler.save_chunk(file_id, 0, _chunk(b"data"))

    with pytest.raises(UploadError):
        handler.assemble_file(file_id, 1, "../evil.edf")

    assert not (tmp_path / "evil.edf").exists(), \
        "assembled file escaped the upload directory"


def test_assemble_file_cannot_escape_via_file_id(handler, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(UploadError):
        handler.assemble_file("../outside/evil", 1, "study.edf")

    assert not (outside / "evil_assembled.edf").exists()


# ══════════════════════════════════════════════════════════════
#  4. Regression — a legitimate upload still works end to end
# ══════════════════════════════════════════════════════════════

def test_full_two_chunk_upload_still_assembles(handler):
    file_id = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"

    handler.validate_chunk_params(file_id, 0, 2, "study.edf")
    handler.save_chunk(file_id, 0, _chunk(b"AAAA"))
    handler.validate_chunk_params(file_id, 1, 2, "study.edf")
    handler.save_chunk(file_id, 1, _chunk(b"BBBB"))

    final_filename = handler.sanitize_filename("study.edf")
    final_path = handler.assemble_file(file_id, 2, final_filename)

    assert os.path.isfile(final_path)
    with open(final_path, "rb") as fh:
        assert fh.read() == b"AAAABBBB"

    # chunks and the temporary assembly file are cleaned up
    for i in range(2):
        assert not os.path.exists(
            os.path.join(handler.upload_dir, f"{file_id}_chunk_{i}")
        )
    assert not os.path.exists(
        os.path.join(handler.upload_dir, f"{file_id}_assembled.edf")
    )


def test_assemble_file_keeps_collision_rename_inside_upload_dir(handler):
    """Existing final name -> timestamped name, still contained."""
    file_id = "collide01"
    base = os.path.realpath(handler.upload_dir)
    existing = os.path.join(base, "study.edf")
    with open(existing, "wb") as fh:
        fh.write(b"old")

    handler.save_chunk(file_id, 0, _chunk(b"NEW"))
    final_path = handler.assemble_file(file_id, 1, "study.edf")

    assert os.path.realpath(final_path).startswith(base + os.sep)
    assert final_path != existing
    with open(existing, "rb") as fh:
        assert fh.read() == b"old", "pre-existing file was overwritten"


def test_sanitize_filename_unchanged(handler):
    """sanitize_filename was already correct — guard against regressions."""
    assert handler.sanitize_filename("study.edf") == "study.edf"
    assert handler.sanitize_filename("  study.edf  ") == "study.edf"
    assert handler.sanitize_filename("../../etc/passwd") == "etc_passwd.edf"
    assert handler.sanitize_filename("no_extension") == "no_extension.edf"
    with pytest.raises(UploadError):
        handler.sanitize_filename("x" * 300 + ".edf")
