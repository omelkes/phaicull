"""Tests for image loader — safety checks, format support, EXIF orientation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from core.loader.image_loader import load_image

MAX_FILE_SIZE = 10 * 1_048_576  # 10 MB for tests
MAX_DIM = 5000


# --- Happy path ---


def test_load_valid_jpeg(tmp_path: Path) -> None:
    """Valid JPEG loads as BGR numpy array with correct shape."""
    path = tmp_path / "photo.jpg"
    Image.new("RGB", (64, 48), color=(255, 0, 0)).save(path, "JPEG")

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=MAX_DIM)

    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (48, 64, 3)
    # Red pixel in BGR: B=0, G=0, R=255
    assert result[0, 0, 2] > 200  # R channel


def test_load_valid_png(tmp_path: Path) -> None:
    """Valid PNG loads correctly."""
    path = tmp_path / "image.png"
    Image.new("RGB", (32, 32), color=(0, 255, 0)).save(path, "PNG")

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=MAX_DIM)

    assert result is not None
    assert result.shape == (32, 32, 3)


def test_load_rgba_png(tmp_path: Path) -> None:
    """RGBA PNG is converted to 3-channel BGR."""
    path = tmp_path / "rgba.png"
    Image.new("RGBA", (16, 16), color=(0, 0, 255, 128)).save(path, "PNG")

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=MAX_DIM)

    assert result is not None
    assert result.shape == (16, 16, 3)


def test_load_with_exif_orientation(tmp_path: Path) -> None:
    """Image with EXIF orientation 6 (90 CW) has swapped dimensions after load."""
    from PIL.ExifTags import Base as ExifBase

    path = tmp_path / "rotated.jpg"
    img = Image.new("RGB", (80, 40), color=(100, 100, 100))
    exif = img.getexif()
    exif[ExifBase.Orientation] = 6
    img.save(path, "JPEG", exif=exif.tobytes())

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=MAX_DIM)

    assert result is not None
    # 80x40 rotated 90 CW → 40x80
    assert result.shape == (80, 40, 3)


# --- Safety rejections ---


def test_reject_oversized_file(tmp_path: Path) -> None:
    """File exceeding max_file_size_bytes returns None."""
    path = tmp_path / "big.jpg"
    Image.new("RGB", (100, 100)).save(path, "JPEG")

    result = load_image(path, max_file_size_bytes=10, max_dimension=MAX_DIM)

    assert result is None


def test_reject_huge_dimensions(tmp_path: Path) -> None:
    """Image with dimensions exceeding max_dimension returns None."""
    path = tmp_path / "wide.png"
    # Create a very wide but thin image (uses little disk space)
    Image.new("RGB", (200, 1)).save(path, "PNG")

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=100)

    assert result is None


# --- Corrupted / invalid ---


def test_zero_byte_file(tmp_path: Path) -> None:
    """Zero-byte file returns None."""
    path = tmp_path / "empty.jpg"
    path.touch()

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=MAX_DIM)

    assert result is None


def test_truncated_jpeg(tmp_path: Path) -> None:
    """Truncated JPEG returns None."""
    path = tmp_path / "truncated.jpg"
    good = tmp_path / "good.jpg"
    Image.new("RGB", (32, 32)).save(good, "JPEG")
    data = good.read_bytes()
    path.write_bytes(data[: len(data) // 3])

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=MAX_DIM)

    assert result is None


def test_non_image_file(tmp_path: Path) -> None:
    """Text file returns None."""
    path = tmp_path / "readme.txt"
    path.write_text("Hello world", encoding="utf-8")

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=MAX_DIM)

    assert result is None


def test_nonexistent_file(tmp_path: Path) -> None:
    """Missing file returns None."""
    path = tmp_path / "ghost.jpg"

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=MAX_DIM)

    assert result is None


# --- Edge cases ---


def test_1x1_image(tmp_path: Path) -> None:
    """Smallest valid image loads successfully."""
    path = tmp_path / "tiny.png"
    Image.new("RGB", (1, 1), color=(42, 42, 42)).save(path, "PNG")

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=MAX_DIM)

    assert result is not None
    assert result.shape == (1, 1, 3)


def test_grayscale_image(tmp_path: Path) -> None:
    """Grayscale (L mode) image is converted to 3-channel BGR."""
    path = tmp_path / "gray.png"
    Image.new("L", (20, 20), color=128).save(path, "PNG")

    result = load_image(path, max_file_size_bytes=MAX_FILE_SIZE, max_dimension=MAX_DIM)

    assert result is not None
    assert result.shape == (20, 20, 3)
