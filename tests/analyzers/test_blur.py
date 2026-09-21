"""4-category tests for BlurAnalyzer (per AGENTS.md Technical Standards).

Categories:
1. Happy path — sharp vs blurred images rank correctly.
2. Corrupted files — gated by the loader before analyzers run; verified
   end-to-end through the Brawn worker.
3. Invalid type (non-image) — same loader gate, verified through the worker.
4. Edge cases — 1x1 pixel, extreme aspect ratio, flat/empty arrays.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from core.analyzers.blur import BlurAnalyzer
from core.scanner.worker import process_file

MAX_SIZE = 10 * 1_048_576
MAX_DIM = 5000

_rng = np.random.default_rng(seed=42)


def _sharp_image(width: int = 256, height: int = 256) -> np.ndarray:
    """High-frequency random texture — strong edges everywhere."""
    return _rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)


def _blurred(image: np.ndarray, ksize: int = 15) -> np.ndarray:
    result: np.ndarray = cv2.GaussianBlur(image, (ksize, ksize), 0)
    return result


# --- 1. Happy path ---


def test_sharp_scores_higher_than_blurry(tmp_path: Path) -> None:
    analyzer = BlurAnalyzer()
    sharp = _sharp_image()
    blurry = _blurred(sharp)

    r_sharp = analyzer.analyze(sharp, tmp_path / "sharp.jpg")
    r_blurry = analyzer.analyze(blurry, tmp_path / "blurry.jpg")

    assert r_sharp is not None and r_blurry is not None
    assert r_sharp.value_real is not None and r_blurry.value_real is not None
    assert r_sharp.value_real > r_blurry.value_real


def test_score_in_unit_range_and_metric_name(tmp_path: Path) -> None:
    result = BlurAnalyzer().analyze(_sharp_image(), tmp_path / "img.jpg")
    assert result is not None
    assert result.metric_name == "blur_score"
    assert result.value_real is not None
    assert 0.0 <= result.value_real <= 1.0
    assert result.value_text is None


def test_monotonic_with_increasing_blur(tmp_path: Path) -> None:
    """More blur => lower score (monotonic ranking)."""
    analyzer = BlurAnalyzer()
    base = _sharp_image()
    scores = []
    for ksize in (1, 5, 11, 21):
        img = _blurred(base, ksize) if ksize > 1 else base
        r = analyzer.analyze(img, tmp_path / f"k{ksize}.jpg")
        assert r is not None and r.value_real is not None
        scores.append(r.value_real)
    assert scores == sorted(scores, reverse=True)


def test_idempotent(tmp_path: Path) -> None:
    analyzer = BlurAnalyzer()
    img = _sharp_image()
    r1 = analyzer.analyze(img, tmp_path / "img.jpg")
    r2 = analyzer.analyze(img, tmp_path / "img.jpg")
    assert r1 is not None and r2 is not None
    assert r1.value_real == r2.value_real


def test_resolution_stability(tmp_path: Path) -> None:
    """Same content at different resolutions gives comparable scores.

    A sharp image upscaled 2x must not flip to the blurry end of the scale.
    """
    analyzer = BlurAnalyzer()
    small = _sharp_image(400, 300)
    large = cv2.resize(small, (1600, 1200), interpolation=cv2.INTER_NEAREST)

    r_small = analyzer.analyze(small, tmp_path / "small.jpg")
    r_large = analyzer.analyze(large, tmp_path / "large.jpg")

    assert r_small is not None and r_small.value_real is not None
    assert r_large is not None and r_large.value_real is not None
    assert abs(r_small.value_real - r_large.value_real) < 0.35


# --- 2 & 3. Corrupted / invalid-type files (loader gate, via worker) ---


def test_corrupted_file_never_reaches_analyzer(tmp_path: Path) -> None:
    path = tmp_path / "bad.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0JUNK")
    result = process_file(
        path, [BlurAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "load_failed"
    assert result.metrics == []


def test_non_image_file_never_reaches_analyzer(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("not an image")
    result = process_file(
        path, [BlurAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "load_failed"
    assert result.metrics == []


def test_end_to_end_through_worker(tmp_path: Path) -> None:
    """Real file on disk: worker decodes and blur metric is produced."""
    path = tmp_path / "photo.png"
    Image.fromarray(_sharp_image()[:, :, ::-1]).save(path, "PNG")
    result = process_file(
        path, [BlurAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "ok"
    assert result.analyzer_errors == 0
    assert len(result.metrics) == 1
    assert result.metrics[0].metric_name == "blur_score"


# --- 4. Edge cases ---


def test_1x1_image_returns_zero_score(tmp_path: Path) -> None:
    """1x1 has no edges: variance 0 => score 0.0 (cannot assess sharpness)."""
    img = np.full((1, 1, 3), 128, dtype=np.uint8)
    result = BlurAnalyzer().analyze(img, tmp_path / "tiny.png")
    assert result is not None
    assert result.value_real == 0.0


def test_extreme_aspect_ratio(tmp_path: Path) -> None:
    img = _rng.integers(0, 256, size=(2, 3000, 3), dtype=np.uint8)
    result = BlurAnalyzer().analyze(img, tmp_path / "wide.png")
    assert result is not None
    assert result.value_real is not None
    assert 0.0 <= result.value_real <= 1.0


def test_flat_image_scores_blurry(tmp_path: Path) -> None:
    """Uniform color has zero edge response — bottom of the scale."""
    img = np.full((128, 128, 3), 200, dtype=np.uint8)
    result = BlurAnalyzer().analyze(img, tmp_path / "flat.png")
    assert result is not None
    assert result.value_real == 0.0


def test_empty_array_returns_none(tmp_path: Path) -> None:
    img = np.zeros((0, 0, 3), dtype=np.uint8)
    assert BlurAnalyzer().analyze(img, tmp_path / "empty.png") is None
