"""Shared pytest fixtures for Phaicull tests.

Per AGENTS.md Testing Standards: synthetic images, edge-case files, temp DBs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

# Optional Pillow for image fixtures; skip image tests if not installed.
try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


# --- File / image fixtures ---


@pytest.fixture
def zero_byte_file(tmp_path: Path) -> Path:
    """Path to an existing zero-byte file (no content)."""
    path = tmp_path / "empty.bin"
    path.touch()
    return path


@pytest.fixture
def non_image_file(tmp_path: Path) -> Path:
    """Path to a non-image file (plain text)."""
    path = tmp_path / "readme.txt"
    path.write_text("Not an image. Just text.\n", encoding="utf-8")
    return path


@pytest.fixture
def synthetic_valid_image(tmp_path: Path) -> Path:
    """Path to a small valid JPEG (e.g. for analyzer happy-path tests)."""
    if not HAS_PILLOW:
        pytest.skip("Pillow required for synthetic_valid_image fixture")
    path = tmp_path / "valid.jpg"
    img = Image.new("RGB", (32, 32), color=(128, 64, 200))
    img.save(path, "JPEG", quality=85)
    return path


@pytest.fixture
def synthetic_valid_png(tmp_path: Path) -> Path:
    """Path to a small valid PNG."""
    if not HAS_PILLOW:
        pytest.skip("Pillow required for synthetic_valid_png fixture")
    path = tmp_path / "valid.png"
    img = Image.new("RGB", (24, 24), color=(0, 128, 255))
    img.save(path, "PNG")
    return path


@pytest.fixture
def extreme_aspect_ratio_image(tmp_path: Path) -> Path:
    """Path to a valid image with extreme aspect ratio (e.g. very wide or very tall)."""
    if not HAS_PILLOW:
        pytest.skip("Pillow required for extreme_aspect_ratio_image fixture")
    path = tmp_path / "extreme_ratio.jpg"
    # 1 pixel wide, 200 tall
    img = Image.new("RGB", (1, 200), color=(0, 0, 0))
    img.save(path, "JPEG", quality=85)
    return path


# --- Temp SQLite DB factory fixtures ---


@pytest.fixture
def temp_project_db_factory(tmp_path: Path) -> Callable[[], Path]:
    """Return a callable that creates a fresh migrated project DB and returns its path."""
    counter = 0

    def factory() -> Path:
        nonlocal counter
        counter += 1
        project_root = tmp_path / f"project_{counter}"
        from core.database.dao import ensure_project_db
        return ensure_project_db(project_root)

    return factory


@pytest.fixture
def temp_registry_db_factory(tmp_path: Path) -> Callable[[], Path]:
    """Return a callable that creates a fresh migrated registry DB and returns its path."""
    counter = 0

    def factory() -> Path:
        nonlocal counter
        counter += 1
        base = tmp_path / f"base_{counter}"
        from core.database.dao import ensure_registry_db
        return ensure_registry_db(base)

    return factory
