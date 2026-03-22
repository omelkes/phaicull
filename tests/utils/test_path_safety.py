"""Tests for path scope safety."""

from __future__ import annotations

import os
from pathlib import Path

from core.utils.path_safety import validate_scan_path


def test_file_inside_root(tmp_path: Path) -> None:
    """Normal file within scan root is valid."""
    f = tmp_path / "photos" / "img.jpg"
    f.parent.mkdir()
    f.touch()
    assert validate_scan_path(f, tmp_path) is True


def test_file_in_nested_subdir(tmp_path: Path) -> None:
    """File deep inside scan root is valid."""
    f = tmp_path / "a" / "b" / "c" / "img.png"
    f.parent.mkdir(parents=True)
    f.touch()
    assert validate_scan_path(f, tmp_path) is True


def test_symlink_inside_root(tmp_path: Path) -> None:
    """Symlink pointing to a file within scan root is valid."""
    real = tmp_path / "real.jpg"
    real.touch()
    link = tmp_path / "link.jpg"
    link.symlink_to(real)
    assert validate_scan_path(link, tmp_path) is True


def test_symlink_escaping_root(tmp_path: Path) -> None:
    """Symlink whose target is outside scan root is rejected."""
    outside = tmp_path.parent / "outside_file.txt"
    outside.touch()
    try:
        scan_root = tmp_path / "photos"
        scan_root.mkdir()
        link = scan_root / "escape.jpg"
        link.symlink_to(outside)
        assert validate_scan_path(link, scan_root) is False
    finally:
        outside.unlink(missing_ok=True)


def test_relative_traversal(tmp_path: Path) -> None:
    """Path with ../ components that escapes root is rejected."""
    scan_root = tmp_path / "project"
    scan_root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.touch()
    crafted = scan_root / ".." / "secret.txt"
    assert validate_scan_path(crafted, scan_root) is False


def test_nonexistent_file(tmp_path: Path) -> None:
    """Non-existent file is rejected (resolve strict=True fails)."""
    f = tmp_path / "does_not_exist.jpg"
    assert validate_scan_path(f, tmp_path) is False


def test_directory_rejected(tmp_path: Path) -> None:
    """A directory (not a file) is rejected."""
    d = tmp_path / "subdir"
    d.mkdir()
    assert validate_scan_path(d, tmp_path) is False


def test_scan_root_itself(tmp_path: Path) -> None:
    """The scan root directory itself is not a file, so rejected."""
    assert validate_scan_path(tmp_path, tmp_path) is False
