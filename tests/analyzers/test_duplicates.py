"""4-category tests for DuplicatesAnalyzer / pHash (per AGENTS.md).

Corrupted/invalid-type files are gated by the loader before analyzers run;
verified end-to-end through the Brawn worker.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from core.analyzers.duplicates import DuplicatesAnalyzer
from core.scanner.worker import process_file

MAX_SIZE = 10 * 1_048_576
MAX_DIM = 5000

_rng = np.random.default_rng(seed=1234)


def _photo_like(width: int = 256, height: int = 256) -> np.ndarray:
    """Sinusoidal low-frequency structure + mild noise — photo-like spectrum.

    Strong, distinct low-frequency DCT coefficients make the hash bits
    meaningful (a flat gradient would leave them clustered at the median).
    """
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    gray = (
        128
        + 55 * np.sin(xx / 17.0)
        + 45 * np.cos(yy / 23.0)
        + 25 * np.sin((xx + 2 * yy) / 31.0)
        + _rng.normal(0, 5, size=(height, width)).astype(np.float32)
    )
    gray_u8 = np.clip(gray, 0, 255).astype(np.uint8)
    return np.stack([gray_u8] * 3, axis=-1)


def _hamming(hex_a: str, hex_b: str) -> int:
    return bin(int(hex_a, 16) ^ int(hex_b, 16)).count("1")


def _hash_of(image: np.ndarray, tmp_path: Path) -> str:
    result = DuplicatesAnalyzer().analyze(image, tmp_path / "img.jpg")
    assert result is not None
    assert result.value_text is not None
    return result.value_text


# --- 1. Happy path ---


def test_hash_format(tmp_path: Path) -> None:
    result = DuplicatesAnalyzer().analyze(_photo_like(), tmp_path / "img.jpg")
    assert result is not None
    assert result.metric_name == "phash"
    assert result.value_real is None
    assert result.value_text is not None
    assert len(result.value_text) == 16
    int(result.value_text, 16)  # valid hex


def test_identical_images_identical_hash(tmp_path: Path) -> None:
    img = _photo_like()
    assert _hash_of(img, tmp_path) == _hash_of(img.copy(), tmp_path)


def test_near_duplicate_small_hamming_distance(tmp_path: Path) -> None:
    """Slightly brightened / resized version stays within a few bits."""
    img = _photo_like()
    brighter = np.clip(img.astype(np.int16) + 10, 0, 255).astype(np.uint8)
    resized = cv2.resize(img, (200, 200), interpolation=cv2.INTER_AREA)

    h_orig = _hash_of(img, tmp_path)
    assert _hamming(h_orig, _hash_of(brighter, tmp_path)) <= 6
    assert _hamming(h_orig, _hash_of(resized, tmp_path)) <= 6


def test_different_images_large_hamming_distance(tmp_path: Path) -> None:
    img_a = _photo_like()
    img_b = np.rot90(_photo_like()).copy()  # different structure
    checker = np.indices((256, 256)).sum(axis=0) % 2 * 255
    img_c = np.stack([checker.astype(np.uint8)] * 3, axis=-1)

    h_a = _hash_of(img_a, tmp_path)
    assert _hamming(h_a, _hash_of(img_b, tmp_path)) > 10
    assert _hamming(h_a, _hash_of(img_c, tmp_path)) > 10


def test_idempotent(tmp_path: Path) -> None:
    img = _photo_like()
    hashes = {_hash_of(img, tmp_path) for _ in range(3)}
    assert len(hashes) == 1


# --- 2 & 3. Corrupted / invalid-type files (loader gate, via worker) ---


def test_corrupted_file_never_reaches_analyzer(tmp_path: Path) -> None:
    path = tmp_path / "bad.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0JUNK")
    result = process_file(
        path, [DuplicatesAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "load_failed"
    assert result.metrics == []


def test_zero_byte_file_never_reaches_analyzer(tmp_path: Path) -> None:
    path = tmp_path / "empty.jpg"
    path.touch()
    result = process_file(
        path, [DuplicatesAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    assert result.status == "load_failed"


def test_end_to_end_resaved_jpeg_is_near_duplicate(tmp_path: Path) -> None:
    """The core use case: same photo saved twice (different quality) matches."""
    img = _photo_like()
    p1 = tmp_path / "orig.jpg"
    p2 = tmp_path / "resave.jpg"
    Image.fromarray(img[:, :, ::-1]).save(p1, "JPEG", quality=95)
    Image.fromarray(img[:, :, ::-1]).save(p2, "JPEG", quality=60)

    r1 = process_file(
        p1, [DuplicatesAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )
    r2 = process_file(
        p2, [DuplicatesAnalyzer()], max_file_size_bytes=MAX_SIZE, max_dimension=MAX_DIM
    )

    assert r1.metrics and r2.metrics
    assert r1.metrics[0].value_text is not None
    assert r2.metrics[0].value_text is not None
    assert _hamming(r1.metrics[0].value_text, r2.metrics[0].value_text) <= 6


# --- 4. Edge cases ---


def test_1x1_image_produces_valid_hash(tmp_path: Path) -> None:
    img = np.full((1, 1, 3), 128, dtype=np.uint8)
    result = DuplicatesAnalyzer().analyze(img, tmp_path / "tiny.png")
    assert result is not None
    assert result.value_text is not None
    assert len(result.value_text) == 16


def test_extreme_aspect_ratio(tmp_path: Path) -> None:
    img = _rng.integers(0, 256, size=(2, 4000, 3), dtype=np.uint8)
    result = DuplicatesAnalyzer().analyze(img, tmp_path / "wide.png")
    assert result is not None
    assert result.value_text is not None
    assert len(result.value_text) == 16


def test_empty_array_returns_none(tmp_path: Path) -> None:
    img = np.zeros((0, 0, 3), dtype=np.uint8)
    assert DuplicatesAnalyzer().analyze(img, tmp_path / "empty.png") is None
