"""Safe image loading for Phaicull.

Handles JPG, PNG, GIF, WebP (Pillow built-ins) and HEIC (via pillow-heif) —
the same set accepted by the MIME gate in core/utils/mime.py. Applies decompression-
bomb checks (file size and pixel dimensions) before full decode, then
EXIF auto-orientation, and finally conversion to a NumPy BGR array for
OpenCV-based analyzers.

Designed to run in the Brawn process — no DB access, no asyncio.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pillow_heif
from loguru import logger
from PIL import Image

from core.utils.exif import auto_orient

pillow_heif.register_heif_opener()


class LoadFailure(StrEnum):
    """Why an image was not loaded. Values are stored in files.status_reason (stable)."""

    UNREADABLE = "unreadable"
    ZERO_BYTE = "zero_byte"
    TOO_LARGE = "too_large"
    CANNOT_OPEN = "cannot_open"
    DIMENSIONS_TOO_LARGE = "dimensions_too_large"
    DECODE_FAILED = "decode_failed"


class LoadResult(NamedTuple):
    """Decoded BGR image, or None with the failure reason."""

    image: np.ndarray | None
    failure: LoadFailure | None


def _failed(reason: LoadFailure, path: Path) -> LoadResult:
    logger.debug("Image not loaded ({}): {}", reason.value, path)
    return LoadResult(None, reason)


def try_load_image(
    path: Path,
    *,
    max_file_size_bytes: int,
    max_dimension: int,
) -> LoadResult:
    """Load an image file safely, returning the BGR array or a failure reason.

    Steps:
    1. File size check (before any decode).
    2. Open with Pillow (lazy — reads headers only).
    3. Dimension check (width/height from headers).
    4. Full pixel decode.
    5. EXIF auto-orientation.
    6. Convert to NumPy BGR array (OpenCV convention).

    Never raises for a bad file; every rejection maps to a LoadFailure.
    """
    path = Path(path).resolve()

    try:
        file_size = path.stat().st_size
    except OSError:
        return _failed(LoadFailure.UNREADABLE, path)

    if file_size == 0:
        return _failed(LoadFailure.ZERO_BYTE, path)

    if file_size > max_file_size_bytes:
        return _failed(LoadFailure.TOO_LARGE, path)

    try:
        img: Image.Image = Image.open(path)
    except Exception:
        return _failed(LoadFailure.CANNOT_OPEN, path)

    width, height = img.size
    if width > max_dimension or height > max_dimension:
        img.close()
        return _failed(LoadFailure.DIMENSIONS_TOO_LARGE, path)

    try:
        img.load()
    except Exception:
        img.close()
        return _failed(LoadFailure.DECODE_FAILED, path)

    img = auto_orient(img)

    try:
        rgb = img.convert("RGB")
        arr = np.array(rgb)
        bgr: np.ndarray = arr[:, :, ::-1].copy()
        return LoadResult(bgr, None)
    except Exception:
        return _failed(LoadFailure.DECODE_FAILED, path)
    finally:
        img.close()


def load_image(
    path: Path,
    *,
    max_file_size_bytes: int,
    max_dimension: int,
) -> np.ndarray | None:
    """Load an image file safely, returning a BGR NumPy array or None on failure."""
    return try_load_image(
        path, max_file_size_bytes=max_file_size_bytes, max_dimension=max_dimension
    ).image
