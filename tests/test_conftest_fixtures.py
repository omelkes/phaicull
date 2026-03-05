"""Smoke tests that conftest fixtures work (synthetic images, files, DB factories)."""

from pathlib import Path

import pytest


def test_zero_byte_file(zero_byte_file: Path) -> None:
    assert zero_byte_file.exists()
    assert zero_byte_file.stat().st_size == 0


def test_non_image_file(non_image_file: Path) -> None:
    assert non_image_file.exists()
    assert "Not an image" in non_image_file.read_text()
    assert non_image_file.suffix == ".txt"


def test_synthetic_valid_image(synthetic_valid_image: Path) -> None:
    assert synthetic_valid_image.exists()
    assert synthetic_valid_image.stat().st_size > 0
    assert synthetic_valid_image.suffix.lower() in (".jpg", ".jpeg")


def test_synthetic_valid_png(synthetic_valid_png: Path) -> None:
    assert synthetic_valid_png.exists()
    assert synthetic_valid_png.stat().st_size > 0
    assert synthetic_valid_png.suffix.lower() == ".png"


def test_extreme_aspect_ratio_image(extreme_aspect_ratio_image: Path) -> None:
    assert extreme_aspect_ratio_image.exists()
    assert extreme_aspect_ratio_image.stat().st_size > 0


def test_temp_project_db_factory(temp_project_db_factory: object) -> None:
    factory = temp_project_db_factory
    path1 = factory()
    path2 = factory()
    assert path1.exists()
    assert path2.exists()
    assert path1 != path2
    assert path1.name == "phaicull.db"


def test_temp_registry_db_factory(temp_registry_db_factory: object) -> None:
    factory = temp_registry_db_factory
    path1 = factory()
    path2 = factory()
    assert path1.exists()
    assert path2.exists()
    assert path1 != path2
    assert path1.name == "registry.db"
