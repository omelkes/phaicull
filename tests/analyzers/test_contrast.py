"""4-category tests for ContrastAnalyzer (per AGENTS.md Technical Standards).

Corrupted/invalid-type files are gated by the loader before analyzers run;
verified end-to-end through the Brawn worker.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from core.analyzers.contrast import ContrastAnalyzer
from core.scanner.worker import process_file

MAX_SIZE = 10 * 1_048_576
MAX_DIM = 5000


def _flat(value: int, width: int = 64, height: int = 64) -> np.ndarray:
    return np.full((height, width, 3), value, dtype=np.uint8)


def _checkerboard(width: int = 64, height: int = 64) -> np.ndarray:
    yy, xx = np.mgrid[0:height, 0:width]
    tiles = ((xx // 4) + (yy // 4)) % 2
    gray = (tiles * 255).astype(np.uint8)
    return np.stack([gray] * 3, axis=-1)


# --- 1. Happy path ---


def test_flat_image_scores_zero(tmp_path: Path) -> None:
    result = ContrastAnalyzer().analyze(_flat(128), tmp_path / "flat.jpg")
    assert result is not None
    assert result.value_real == 0.0


def test_checkerboard_scores_near_one(tmp_path: Path) -> None:
    result = ContrastAnalyzer().analyze(_checkerboard(), tmp_path / "check.jpg")
    assert result is not None
    assert result.value_real is not None
    assert result.value_real == pytest.approx(1.0, abs=0.05)


def test_low_contrast_scores_below_high_contrast(tmp_path: Path) -> None:
    analyzer = ContrastAnalyzer()
    muted = np.full((64, 64, 3), 120, dtype=np.uint8)
    muted[:, :32] = 130
    low = analyzer.analyze(muted, tmp_path / "low.jpg")
    high = analyzer.analyze(_checkerboard(), tmp_path / "high.jpg")
    assert low is not None and high is not None
    assert low.value_real is not None and high.value_real is not None
    assert low.value_real < high.value_real


def test_metric_name_and_range(tmp_path: Path) -> None:
    result = ContrastAnalyzer().analyze(_checkerboard(), tmp_path / "img.jpg")
    assert result is not None
    assert result.metric_name == "contrast_score"
    assert result.value_real is not None
    assert 0.0 <= result.value_real <= 1.0
    assert result.value_text is None


def test_idempotent(tmp_path: Path) -> None:
    analyzer = ContrastAnalyzer()
    img = _checkerboard()
    r1 = analyzer.analyze(img, tmp_path / "img.jpg")
    r2 = analyzer.analyze(img, tmp_path / "img.jpg")
    assert r1 is not None and r2 is not None
    assert r1.value_real == r2.value_real


# --- 2 & 3. Corrupted / invalid-type files (loader gate, via worker) ---


def test_corrupted_file_never_reaches_analyzer(tmp_path: Path) -> None:
    path = tmp_path / "bad.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0JUNK")
    result = process_file(
        path, [ContrastAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "load_failed"
    assert result.metrics == []


def test_non_image_file_never_reaches_analyzer(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("not an image")
    result = process_file(
        path, [ContrastAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "load_failed"
    assert result.metrics == []


def test_end_to_end_through_worker(tmp_path: Path) -> None:
    path = tmp_path / "flat.png"
    Image.new("RGB", (32, 32), color=(80, 80, 80)).save(path, "PNG")
    result = process_file(
        path, [ContrastAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "ok"
    assert result.analyzer_errors == 0
    assert len(result.metrics) == 1
    assert result.metrics[0].metric_name == "contrast_score"
    assert result.metrics[0].value_real == pytest.approx(0.0, abs=0.02)


# --- 4. Edge cases ---


def test_1x1_image_scores_zero(tmp_path: Path) -> None:
    result = ContrastAnalyzer().analyze(_flat(200, 1, 1), tmp_path / "tiny.png")
    assert result is not None
    assert result.value_real == 0.0


def test_extreme_aspect_ratio(tmp_path: Path) -> None:
    img = np.zeros((1, 4000, 3), dtype=np.uint8)
    img[:, :2000] = 255
    result = ContrastAnalyzer().analyze(img, tmp_path / "wide.png")
    assert result is not None
    assert result.value_real is not None
    assert result.value_real == pytest.approx(1.0, abs=0.05)


def test_empty_array_returns_none(tmp_path: Path) -> None:
    img = np.zeros((0, 0, 3), dtype=np.uint8)
    assert ContrastAnalyzer().analyze(img, tmp_path / "empty.png") is None
