"""Tests for EXIF orientation handling."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from PIL import Image

from core.utils.exif import auto_orient


def _make_image_with_orientation(tmp_path: Path, orientation: int) -> Image.Image:
    """Create a 40x20 image with an EXIF orientation tag.

    Width > height so we can detect rotation by checking dimension swap.
    """
    img = Image.new("RGB", (40, 20), color=(100, 150, 200))
    from PIL.ExifTags import Base as ExifBase

    exif = img.getexif()
    exif[ExifBase.Orientation] = orientation
    path = tmp_path / f"oriented_{orientation}.jpg"
    img.save(path, "JPEG", exif=exif.tobytes())
    return Image.open(path)


def test_orientation_6_rotates_90cw(tmp_path: Path) -> None:
    """Orientation 6 (rotate 90 CW) swaps width and height."""
    img = _make_image_with_orientation(tmp_path, 6)
    assert img.size == (40, 20)
    corrected = auto_orient(img)
    assert corrected.size == (20, 40)


def test_orientation_3_rotates_180(tmp_path: Path) -> None:
    """Orientation 3 (rotate 180) keeps same dimensions."""
    img = _make_image_with_orientation(tmp_path, 3)
    corrected = auto_orient(img)
    assert corrected.size == (40, 20)


def test_orientation_8_rotates_270cw(tmp_path: Path) -> None:
    """Orientation 8 (rotate 270 CW / 90 CCW) swaps width and height."""
    img = _make_image_with_orientation(tmp_path, 8)
    corrected = auto_orient(img)
    assert corrected.size == (20, 40)


def test_no_exif_returns_unchanged(tmp_path: Path) -> None:
    """Image without EXIF data is returned unchanged."""
    img = Image.new("RGB", (30, 30), color=(0, 0, 0))
    corrected = auto_orient(img)
    assert corrected.size == (30, 30)


def test_orientation_1_identity(tmp_path: Path) -> None:
    """Orientation 1 (normal) keeps image as-is."""
    img = _make_image_with_orientation(tmp_path, 1)
    corrected = auto_orient(img)
    assert corrected.size == (40, 20)


def test_corrupted_exif_returns_original(tmp_path: Path) -> None:
    """Image with corrupted EXIF data is returned without crash."""
    path = tmp_path / "bad_exif.jpg"
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    img.save(path, "JPEG")
    data = bytearray(path.read_bytes())
    # Append garbage EXIF-like marker
    data.extend(b"\xff\xe1\x00\x04BAAD")
    path.write_bytes(bytes(data))
    reopened = Image.open(path)
    corrected = auto_orient(reopened)
    assert corrected.size[0] > 0 and corrected.size[1] > 0
