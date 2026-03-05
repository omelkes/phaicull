"""Tests for MIME validation (magic-byte checker)."""

from pathlib import Path

import pytest

from core.utils.mime import (
    get_image_mime,
    is_supported_image,
    supported_image_mime_types,
)


# --- Happy path: valid image files ---


def test_valid_jpeg_returns_image_jpeg(synthetic_valid_image: Path) -> None:
    assert get_image_mime(synthetic_valid_image) == "image/jpeg"
    assert is_supported_image(synthetic_valid_image) is True


def test_valid_png_returns_image_png(synthetic_valid_png: Path) -> None:
    assert get_image_mime(synthetic_valid_png) == "image/png"
    assert is_supported_image(synthetic_valid_png) is True


def test_jpeg_with_wrong_extension_returns_image_jpeg(tmp_path: Path) -> None:
    """Magic bytes determine type; extension is ignored."""
    from PIL import Image
    path = tmp_path / "fake.txt"
    img = Image.new("RGB", (2, 2), color="red")
    img.save(path, "JPEG")
    assert get_image_mime(path) == "image/jpeg"


# --- Corrupted / truncated files ---


def test_zero_byte_file_returns_none(zero_byte_file: Path) -> None:
    assert get_image_mime(zero_byte_file) is None
    assert is_supported_image(zero_byte_file) is False


def test_truncated_jpeg_header_returns_none(tmp_path: Path) -> None:
    """Only 2 bytes of JPEG magic (FF D8) — incomplete signature."""
    path = tmp_path / "truncated.jpg"
    path.write_bytes(b"\xff\xd8")
    assert get_image_mime(path) is None


def test_truncated_png_header_returns_none(tmp_path: Path) -> None:
    """Only 4 bytes of PNG magic — incomplete."""
    path = tmp_path / "truncated.png"
    path.write_bytes(b"\x89PNG")
    assert get_image_mime(path) is None


# --- Non-image files ---


def test_non_image_file_returns_none(non_image_file: Path) -> None:
    assert get_image_mime(non_image_file) is None
    assert is_supported_image(non_image_file) is False


def test_pdf_like_header_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "fake.pdf"
    path.write_bytes(b"%PDF-1.4 fake content")
    assert get_image_mime(path) is None


# --- Edge cases ---


def test_missing_file_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "does_not_exist.jpg"
    assert not path.exists()
    assert get_image_mime(path) is None


def test_supported_image_mime_types_returns_tuple() -> None:
    mimes = supported_image_mime_types()
    assert isinstance(mimes, tuple)
    assert "image/jpeg" in mimes
    assert "image/png" in mimes
    assert "image/gif" in mimes
    assert "image/webp" in mimes
    assert "image/heic" in mimes


def test_heic_magic_bytes_returns_image_heic(tmp_path: Path) -> None:
    """Apple HEIC/HEIF: ftyp box at offset 4, brand 'heic' at offset 8."""
    path = tmp_path / "photo.heic"
    # Minimal ftyp box: size (24, big-endian) + 'ftyp' + 'heic'
    path.write_bytes(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00")
    assert get_image_mime(path) == "image/heic"
    assert is_supported_image(path) is True


def test_heif_mif1_brand_returns_image_heic(tmp_path: Path) -> None:
    """HEIF with mif1 brand (common for HEIF images) is recognized."""
    path = tmp_path / "image.heif"
    path.write_bytes(b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00")
    assert get_image_mime(path) == "image/heic"


def test_extreme_aspect_ratio_image_still_valid(extreme_aspect_ratio_image: Path) -> None:
    """Valid JPEG with extreme dimensions is still recognized by magic bytes."""
    assert get_image_mime(extreme_aspect_ratio_image) == "image/jpeg"
