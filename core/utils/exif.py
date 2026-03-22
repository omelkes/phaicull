"""EXIF orientation handling for Phaicull.

Reads the EXIF orientation tag and rotates/flips the image data before
passing to any analyzer. Uses Pillow's ImageOps.exif_transpose which
handles all 8 EXIF orientation values.
"""

from __future__ import annotations

from PIL import Image, ImageOps
from loguru import logger


def auto_orient(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation correction to a Pillow Image.

    Returns the corrected image, or the original if no EXIF orientation
    tag is present or if the EXIF data is corrupted.
    """
    try:
        oriented = ImageOps.exif_transpose(img)
        if oriented is not None:
            return oriented
        return img
    except Exception:
        logger.debug("EXIF orientation correction failed, returning original")
        return img
