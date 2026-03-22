"""Tests for Brawn worker (per-file processing)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from core.analyzers import get_sprint1_analyzers
from core.scanner.worker import FileResult, process_file

MAX_SIZE = 10 * 1_048_576
MAX_DIM = 5000


def test_process_valid_jpeg(tmp_path: Path) -> None:
    """Valid JPEG produces a FileResult with content_hash and ok status.

    Analyzers are stubs (NotImplementedError) so metrics will be empty,
    but the worker should not crash.
    """
    path = tmp_path / "photo.jpg"
    Image.new("RGB", (32, 32), color=(100, 100, 100)).save(path, "JPEG")

    result = process_file(
        path,
        get_sprint1_analyzers(),
        max_file_size_bytes=MAX_SIZE,
        max_dimension=MAX_DIM,
    )

    assert isinstance(result, FileResult)
    assert result.status == "ok"
    assert result.content_hash is not None
    assert len(result.content_hash) == 64  # SHA-256 hex


def test_process_corrupted_image(tmp_path: Path) -> None:
    """Corrupted image results in load_failed status."""
    path = tmp_path / "bad.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0JUNK")

    result = process_file(
        path,
        get_sprint1_analyzers(),
        max_file_size_bytes=MAX_SIZE,
        max_dimension=MAX_DIM,
    )

    assert result.status == "load_failed"
    assert result.metrics == []


def test_process_non_image(tmp_path: Path) -> None:
    """Non-image file results in load_failed status."""
    path = tmp_path / "readme.txt"
    path.write_text("Not an image", encoding="utf-8")

    result = process_file(
        path,
        get_sprint1_analyzers(),
        max_file_size_bytes=MAX_SIZE,
        max_dimension=MAX_DIM,
    )

    assert result.status == "load_failed"


def test_process_zero_byte(tmp_path: Path) -> None:
    """Zero-byte file results in load_failed status."""
    path = tmp_path / "empty.bin"
    path.touch()

    result = process_file(
        path,
        get_sprint1_analyzers(),
        max_file_size_bytes=MAX_SIZE,
        max_dimension=MAX_DIM,
    )

    assert result.status == "load_failed"


def test_file_result_has_absolute_path(tmp_path: Path) -> None:
    """FileResult.file_path is an absolute resolved path string."""
    path = tmp_path / "img.jpg"
    Image.new("RGB", (8, 8)).save(path, "JPEG")

    result = process_file(
        path,
        [],
        max_file_size_bytes=MAX_SIZE,
        max_dimension=MAX_DIM,
    )

    assert Path(result.file_path).is_absolute()


def test_process_with_no_analyzers(tmp_path: Path) -> None:
    """Processing with empty analyzer list still succeeds with status ok."""
    path = tmp_path / "img.png"
    Image.new("RGB", (16, 16)).save(path, "PNG")

    result = process_file(
        path,
        [],
        max_file_size_bytes=MAX_SIZE,
        max_dimension=MAX_DIM,
    )

    assert result.status == "ok"
    assert result.metrics == []
