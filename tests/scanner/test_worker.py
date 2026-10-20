"""Tests for Brawn worker (per-file processing)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from core.analyzers import get_sprint1_analyzers
from core.scanner.worker import FileResult, process_file

MAX_SIZE = 10 * 1_048_576
MAX_DIM = 5000


def test_process_valid_jpeg(tmp_path: Path) -> None:
    """Valid JPEG produces a FileResult with content_hash, ok status, and metrics."""
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
    assert result.analyzer_errors == 0
    names = {m.metric_name for m in result.metrics}
    assert names == {"blur_score", "brightness_score", "contrast_score", "phash"}


def test_analyzer_failures_are_counted(tmp_path: Path) -> None:
    """Analyzers that raise are counted in FileResult.analyzer_errors."""
    import numpy as np

    from core.analyzers.base import AnalyzerResult, BaseAnalyzer

    class FailingAnalyzer(BaseAnalyzer):
        @property
        def metric_name(self) -> str:
            return "always_fails"

        def analyze(self, image: np.ndarray, path: Path) -> AnalyzerResult | None:
            raise RuntimeError("boom")

    path = tmp_path / "photo.jpg"
    Image.new("RGB", (32, 32)).save(path, "JPEG")

    result = process_file(
        path,
        [FailingAnalyzer()],
        max_file_size_bytes=MAX_SIZE,
        max_dimension=MAX_DIM,
    )

    assert result.status == "ok"
    assert result.analyzer_errors == 1
    assert result.metrics == []


def test_analyzers_receive_decoded_image(tmp_path: Path) -> None:
    """Worker passes the decoded BGR array to analyzers (decode-once contract)."""
    import numpy as np

    from core.analyzers.base import AnalyzerResult, BaseAnalyzer

    class RecordingAnalyzer(BaseAnalyzer):
        @property
        def metric_name(self) -> str:
            return "mean_pixel"

        def analyze(self, image: np.ndarray, path: Path) -> AnalyzerResult | None:
            assert image.ndim == 3 and image.shape[2] == 3
            assert image.dtype == np.uint8
            return AnalyzerResult(metric_name=self.metric_name, value_real=float(image.mean()))

    path = tmp_path / "gray.png"
    Image.new("RGB", (16, 16), color=(50, 50, 50)).save(path, "PNG")

    result = process_file(
        path,
        [RecordingAnalyzer()],
        max_file_size_bytes=MAX_SIZE,
        max_dimension=MAX_DIM,
    )

    assert result.status == "ok"
    assert result.analyzer_errors == 0
    assert len(result.metrics) == 1
    assert result.metrics[0].value_real == pytest.approx(50.0, abs=2.0)


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
    assert result.status_reason is not None
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
    assert result.status_reason == "zero_byte"


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


def test_thumbnail_is_staged_from_decoded_image(tmp_path: Path) -> None:
    """With a staging dir, the worker writes a 300px thumbnail under a temporary name."""
    path = tmp_path / "wide.jpg"
    Image.new("RGB", (900, 600), color=(10, 120, 200)).save(path, "JPEG")
    staging = tmp_path / "staging"
    staging.mkdir()

    result = process_file(
        path, [], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM,
        thumbnail_staging_dir=staging,
    )

    assert not result.thumbnail_failed
    assert result.staged_thumbnail is not None
    staged = Path(result.staged_thumbnail)
    assert staged.parent == staging
    with Image.open(staged) as thumb:
        assert thumb.size == (300, 200)


def test_no_thumbnail_without_staging_dir(tmp_path: Path) -> None:
    path = tmp_path / "img.jpg"
    Image.new("RGB", (64, 64)).save(path, "JPEG")

    result = process_file(path, [], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM)

    assert result.staged_thumbnail is None
    assert not result.thumbnail_failed


def test_corrupted_file_gets_no_thumbnail(tmp_path: Path) -> None:
    path = tmp_path / "bad.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0JUNK")
    staging = tmp_path / "staging"
    staging.mkdir()

    result = process_file(
        path, [], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM,
        thumbnail_staging_dir=staging,
    )

    assert result.status == "load_failed"
    assert result.staged_thumbnail is None
    assert list(staging.iterdir()) == []


def test_thumbnail_failure_does_not_fail_the_file(tmp_path: Path) -> None:
    """A thumbnail error is recorded; status and metrics are unaffected."""
    path = tmp_path / "img.jpg"
    Image.new("RGB", (64, 64)).save(path, "JPEG")
    missing_dir = tmp_path / "does-not-exist"

    result = process_file(
        path, get_sprint1_analyzers(), max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM,
        thumbnail_staging_dir=missing_dir,
    )

    assert result.status == "ok"
    assert result.thumbnail_failed
    assert result.staged_thumbnail is None
    assert len(result.metrics) == 4


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
