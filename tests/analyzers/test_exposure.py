"""4-category tests for ExposureAnalyzer (per AGENTS.md Technical Standards).

Corrupted/invalid-type files are gated by the loader before analyzers run;
verified end-to-end through the Brawn worker.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from core.analyzers.exposure import ExposureAnalyzer
from core.scanner.worker import process_file

MAX_SIZE = 10 * 1_048_576
MAX_DIM = 5000


def _flat(value: int, width: int = 64, height: int = 64) -> np.ndarray:
    return np.full((height, width, 3), value, dtype=np.uint8)


# --- 1. Happy path ---


def test_black_white_and_mid_gray(tmp_path: Path) -> None:
    analyzer = ExposureAnalyzer()
    p = tmp_path / "img.jpg"

    black = analyzer.analyze(_flat(0), p)
    mid = analyzer.analyze(_flat(128), p)
    white = analyzer.analyze(_flat(255), p)

    assert black is not None and black.value_real == 0.0
    assert white is not None and white.value_real == 1.0
    assert mid is not None and mid.value_real == pytest.approx(128 / 255, abs=0.01)


def test_metric_name_and_range(tmp_path: Path) -> None:
    result = ExposureAnalyzer().analyze(_flat(77), tmp_path / "img.jpg")
    assert result is not None
    assert result.metric_name == "brightness_score"
    assert result.value_real is not None
    assert 0.0 <= result.value_real <= 1.0
    assert result.value_text is None


def test_dark_scores_lower_than_bright(tmp_path: Path) -> None:
    analyzer = ExposureAnalyzer()
    dark = analyzer.analyze(_flat(30), tmp_path / "dark.jpg")
    bright = analyzer.analyze(_flat(220), tmp_path / "bright.jpg")
    assert dark is not None and bright is not None
    assert dark.value_real is not None and bright.value_real is not None
    assert dark.value_real < bright.value_real


def test_idempotent(tmp_path: Path) -> None:
    analyzer = ExposureAnalyzer()
    rng = np.random.default_rng(seed=7)
    img = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    r1 = analyzer.analyze(img, tmp_path / "img.jpg")
    r2 = analyzer.analyze(img, tmp_path / "img.jpg")
    assert r1 is not None and r2 is not None
    assert r1.value_real == r2.value_real


# --- 2 & 3. Corrupted / invalid-type files (loader gate, via worker) ---


def test_corrupted_file_never_reaches_analyzer(tmp_path: Path) -> None:
    path = tmp_path / "bad.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0JUNK")
    result = process_file(
        path, [ExposureAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "load_failed"
    assert result.metrics == []


def test_non_image_file_never_reaches_analyzer(tmp_path: Path) -> None:
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    result = process_file(
        path, [ExposureAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "load_failed"
    assert result.metrics == []


def test_end_to_end_through_worker(tmp_path: Path) -> None:
    path = tmp_path / "gray.png"
    Image.new("RGB", (32, 32), color=(128, 128, 128)).save(path, "PNG")
    result = process_file(
        path, [ExposureAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "ok"
    assert result.analyzer_errors == 0
    assert len(result.metrics) == 1
    assert result.metrics[0].metric_name == "brightness_score"
    assert result.metrics[0].value_real == pytest.approx(128 / 255, abs=0.02)


# --- 4. Edge cases ---


def test_1x1_image(tmp_path: Path) -> None:
    result = ExposureAnalyzer().analyze(_flat(255, 1, 1), tmp_path / "tiny.png")
    assert result is not None
    assert result.value_real == 1.0


def test_extreme_aspect_ratio(tmp_path: Path) -> None:
    img = np.full((1, 5000, 3), 100, dtype=np.uint8)
    result = ExposureAnalyzer().analyze(img, tmp_path / "wide.png")
    assert result is not None
    assert result.value_real == pytest.approx(100 / 255, abs=0.01)


def test_empty_array_returns_none(tmp_path: Path) -> None:
    img = np.zeros((0, 0, 3), dtype=np.uint8)
    assert ExposureAnalyzer().analyze(img, tmp_path / "empty.png") is None
