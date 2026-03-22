"""Safe image loading for Phaicull.

Handles JPG, PNG, and HEIC via Pillow + pillow-heif. Applies decompression-
bomb checks (file size and pixel dimensions) before full decode, then
EXIF auto-orientation, and finally conversion to a NumPy BGR array for
OpenCV-based analyzers.

Designed to run in the Brawn process — no DB access, no asyncio.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pillow_heif
from loguru import logger
from PIL import Image

from core.utils.exif import auto_orient

pillow_heif.register_heif_opener()


def load_image(
    path: Path,
    *,
    max_file_size_bytes: int,
    max_dimension: int,
) -> np.ndarray | None:
    """Load an image file safely, returning a BGR NumPy array or None on failure.

    Steps:
    1. File size check (before any decode).
    2. Open with Pillow (lazy — reads headers only).
    3. Dimension check (width/height from headers).
    4. Full pixel decode.
    5. EXIF auto-orientation.
    6. Convert to NumPy BGR array (OpenCV convention).

    Returns None and logs on any failure or safety rejection.
    """
    path = Path(path).resolve()

    try:
        file_size = path.stat().st_size
    except OSError:
        logger.warning("Cannot stat file: {}", path)
        return None

    if file_size == 0:
        logger.debug("Zero-byte file skipped: {}", path)
        return None

    if file_size > max_file_size_bytes:
        logger.warning(
            "File too large ({:.1f} MB > {:.1f} MB limit): {}",
            file_size / 1_048_576,
            max_file_size_bytes / 1_048_576,
            path,
        )
        return None

    try:
        img = Image.open(path)
    except Exception:
        logger.debug("Pillow cannot open file: {}", path)
        return None

    width, height = img.size
    if width > max_dimension or height > max_dimension:
        logger.warning(
            "Image dimensions too large ({}x{}, max {}): {}",
            width,
            height,
            max_dimension,
            path,
        )
        img.close()
        return None

    try:
        img.load()
    except Exception:
        logger.debug("Pillow cannot decode file: {}", path)
        img.close()
        return None

    img = auto_orient(img)

    try:
        rgb = img.convert("RGB")
        arr = np.array(rgb)
        bgr: np.ndarray = arr[:, :, ::-1].copy()
        return bgr
    except Exception:
        logger.debug("NumPy conversion failed: {}", path)
        return None
    finally:
        img.close()
