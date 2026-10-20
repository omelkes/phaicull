"""Thumbnail generation from a decoded BGR array.

Four categories per AGENTS.md. Corrupted and invalid-type files never reach the
thumbnailer (the loader gates them); that path is covered in test_worker.py.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from core.utils.thumbnail import (
    THUMB_MAX_SIDE,
    get_thumbs_dir,
    resize_to_fit,
    thumbnail_name,
    write_thumbnail,
)


def _image(width: int, height: int) -> np.ndarray:
    rng = np.random.default_rng(seed=7)
    return rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)


def test_paths_follow_contract(tmp_path: Path) -> None:
    assert thumbnail_name(42) == "thumb_42.jpg"
    assert get_thumbs_dir(tmp_path) == tmp_path.resolve() / "phaicull" / "thumbs"


# --- 1. Happy path ---


@pytest.mark.parametrize(("width", "height", "expected"), [(1200, 800, (300, 200)),
                                                          (800, 1200, (200, 300))])
def test_longest_side_becomes_300(
    tmp_path: Path, width: int, height: int, expected: tuple[int, int]
) -> None:
    dest = tmp_path / "thumb.jpg"
    write_thumbnail(_image(width, height), dest)
    with Image.open(dest) as thumb:
        assert thumb.format == "JPEG"
        assert thumb.size == expected


def test_input_array_is_not_mutated() -> None:
    image = _image(900, 600)
    before = image.copy()
    resize_to_fit(image)
    assert np.array_equal(image, before)


# --- 2 & 3. Corrupted / invalid input ---


def test_empty_array_raises(tmp_path: Path) -> None:
    dest = tmp_path / "thumb.jpg"
    with pytest.raises(ValueError):
        write_thumbnail(np.zeros((0, 0, 3), dtype=np.uint8), dest)
    assert not dest.exists()


# --- 4. Edge cases ---


def test_small_image_is_not_upscaled(tmp_path: Path) -> None:
    dest = tmp_path / "thumb.jpg"
    write_thumbnail(_image(120, 80), dest)
    with Image.open(dest) as thumb:
        assert thumb.size == (120, 80)


def test_1x1_image(tmp_path: Path) -> None:
    dest = tmp_path / "thumb.jpg"
    write_thumbnail(_image(1, 1), dest)
    with Image.open(dest) as thumb:
        assert thumb.size == (1, 1)


def test_extreme_aspect_ratio_keeps_at_least_one_pixel(tmp_path: Path) -> None:
    dest = tmp_path / "thumb.jpg"
    write_thumbnail(_image(4000, 2), dest)
    with Image.open(dest) as thumb:
        assert thumb.size == (THUMB_MAX_SIDE, 1)


def test_non_ascii_destination(tmp_path: Path) -> None:
    dest = tmp_path / "náhled_žluťoučký.jpg"
    write_thumbnail(_image(600, 400), dest)
    assert dest.stat().st_size > 0
