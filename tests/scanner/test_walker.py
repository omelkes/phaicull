"""Tests for file discovery (walker)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from core.scanner.walker import discover_files


def test_discover_valid_images(tmp_path: Path) -> None:
    """Discovers JPEG and PNG files in a directory."""
    Image.new("RGB", (8, 8)).save(tmp_path / "a.jpg", "JPEG")
    Image.new("RGB", (8, 8)).save(tmp_path / "b.png", "PNG")

    result = discover_files(tmp_path)

    assert len(result) == 2
    names = {p.name for p in result}
    assert names == {"a.jpg", "b.png"}


def test_skip_non_image_files(tmp_path: Path) -> None:
    """Non-image files (txt, pdf) are skipped."""
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4 fake")
    Image.new("RGB", (8, 8)).save(tmp_path / "photo.jpg", "JPEG")

    result = discover_files(tmp_path)

    assert len(result) == 1
    assert result[0].name == "photo.jpg"


def test_discover_nested(tmp_path: Path) -> None:
    """Discovers files in nested subdirectories."""
    sub = tmp_path / "vacation" / "day1"
    sub.mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(sub / "beach.jpg", "JPEG")

    result = discover_files(tmp_path)

    assert len(result) == 1
    assert "beach.jpg" in str(result[0])


def test_empty_directory(tmp_path: Path) -> None:
    """Empty directory returns empty list."""
    result = discover_files(tmp_path)
    assert result == []


def test_skip_symlink_escaping_root(tmp_path: Path) -> None:
    """Symlink pointing outside scan root is skipped."""
    outside = tmp_path.parent / "outside_img.jpg"
    Image.new("RGB", (8, 8)).save(outside, "JPEG")
    try:
        scan_root = tmp_path / "photos"
        scan_root.mkdir()
        (scan_root / "link.jpg").symlink_to(outside)
        Image.new("RGB", (8, 8)).save(scan_root / "real.jpg", "JPEG")

        result = discover_files(scan_root)

        names = {p.name for p in result}
        assert "real.jpg" in names
        assert "link.jpg" not in names
    finally:
        outside.unlink(missing_ok=True)


def test_nonexistent_root(tmp_path: Path) -> None:
    """Non-existent scan root returns empty list."""
    result = discover_files(tmp_path / "nope")
    assert result == []


def test_discover_sorted_order(tmp_path: Path) -> None:
    """Discovered files are returned in sorted order."""
    for name in ["c.jpg", "a.jpg", "b.jpg"]:
        Image.new("RGB", (8, 8)).save(tmp_path / name, "JPEG")

    result = discover_files(tmp_path)

    names = [p.name for p in result]
    assert names == ["a.jpg", "b.jpg", "c.jpg"]
