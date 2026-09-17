"""Tests for file discovery (walker)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from core.scanner.walker import DiscoveryResult, discover_files


def test_discover_valid_images(tmp_path: Path) -> None:
    """Discovers JPEG and PNG files in a directory."""
    Image.new("RGB", (8, 8)).save(tmp_path / "a.jpg", "JPEG")
    Image.new("RGB", (8, 8)).save(tmp_path / "b.png", "PNG")

    result = discover_files(tmp_path)

    assert isinstance(result, DiscoveryResult)
    assert len(result.valid) == 2
    names = {p.name for p in result.valid}
    assert names == {"a.jpg", "b.png"}
    assert result.rejected_mime == []


def test_non_image_files_reported_as_rejected(tmp_path: Path) -> None:
    """Non-image files (txt, pdf) are returned in rejected_mime, not valid."""
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4 fake")
    Image.new("RGB", (8, 8)).save(tmp_path / "photo.jpg", "JPEG")

    result = discover_files(tmp_path)

    assert len(result.valid) == 1
    assert result.valid[0].name == "photo.jpg"
    rejected_names = {p.name for p in result.rejected_mime}
    assert rejected_names == {"notes.txt", "doc.pdf"}


def test_discover_nested(tmp_path: Path) -> None:
    """Discovers files in nested subdirectories."""
    sub = tmp_path / "vacation" / "day1"
    sub.mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(sub / "beach.jpg", "JPEG")

    result = discover_files(tmp_path)

    assert len(result.valid) == 1
    assert "beach.jpg" in str(result.valid[0])


def test_empty_directory(tmp_path: Path) -> None:
    """Empty directory returns empty result."""
    result = discover_files(tmp_path)
    assert result.valid == []
    assert result.rejected_mime == []


def test_skip_symlink_escaping_root(tmp_path: Path) -> None:
    """Symlink pointing outside scan root is skipped entirely (not rejected)."""
    outside = tmp_path.parent / "outside_img.jpg"
    Image.new("RGB", (8, 8)).save(outside, "JPEG")
    try:
        scan_root = tmp_path / "photos"
        scan_root.mkdir()
        (scan_root / "link.jpg").symlink_to(outside)
        Image.new("RGB", (8, 8)).save(scan_root / "real.jpg", "JPEG")

        result = discover_files(scan_root)

        names = {p.name for p in result.valid}
        assert "real.jpg" in names
        assert "link.jpg" not in names
        assert result.rejected_mime == []
    finally:
        outside.unlink(missing_ok=True)


def test_nonexistent_root(tmp_path: Path) -> None:
    """Non-existent scan root returns empty result."""
    result = discover_files(tmp_path / "nope")
    assert result.valid == []
    assert result.rejected_mime == []


def test_discover_sorted_order(tmp_path: Path) -> None:
    """Discovered files are returned in sorted order."""
    for name in ["c.jpg", "a.jpg", "b.jpg"]:
        Image.new("RGB", (8, 8)).save(tmp_path / name, "JPEG")

    result = discover_files(tmp_path)

    names = [p.name for p in result.valid]
    assert names == ["a.jpg", "b.jpg", "c.jpg"]


def test_phaicull_data_dir_is_ignored(tmp_path: Path) -> None:
    """Files inside {scan_root}/phaicull/ (project DB, caches) are never scanned."""
    Image.new("RGB", (8, 8)).save(tmp_path / "photo.jpg", "JPEG")
    data_dir = tmp_path / "phaicull"
    data_dir.mkdir()
    (data_dir / "phaicull.db").write_bytes(b"SQLite format 3\x00fake")
    Image.new("RGB", (8, 8)).save(data_dir / "thumb.jpg", "JPEG")

    result = discover_files(tmp_path)

    assert [p.name for p in result.valid] == ["photo.jpg"]
    assert result.rejected_mime == []
