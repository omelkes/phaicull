"""Thumbnail generation from an already-decoded image (decode once).

Contract: docs/thumbnails.md — `{project_root}/phaicull/thumbs/thumb_<files.id>.jpg`,
longest side 300px, JPEG. Runs in the Brawn worker on the oriented BGR array the
analyzers already received; never re-reads the source file.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.database.schema import PROJECT_PHAICULL_SUBDIR

THUMB_MAX_SIDE = 300
THUMB_JPEG_QUALITY = 85
THUMBS_SUBDIR = "thumbs"
STAGING_SUBDIR = ".staging"


def get_thumbs_dir(project_root: Path) -> Path:
    """Directory holding thumb_<id>.jpg files for a project."""
    return Path(project_root).resolve() / PROJECT_PHAICULL_SUBDIR / THUMBS_SUBDIR


def thumbnail_name(file_id: int) -> str:
    """File name for the thumbnail of files.id = file_id."""
    return f"thumb_{file_id}.jpg"


def resize_to_fit(image: np.ndarray, max_side: int = THUMB_MAX_SIDE) -> np.ndarray:
    """Scale so the longest side is max_side. Smaller images are returned unchanged."""
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= max_side:
        return image
    scale = max_side / longest
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    resized: np.ndarray = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
    return resized


def write_thumbnail(
    image: np.ndarray,
    dest: Path,
    *,
    max_side: int = THUMB_MAX_SIDE,
    quality: int = THUMB_JPEG_QUALITY,
) -> None:
    """Write a JPEG thumbnail of a BGR image to dest. Raises ValueError on an empty image.

    Encodes in memory and writes via Path so non-ASCII paths work on every OS
    (cv2.imwrite does not handle them on Windows).
    """
    if image.size == 0:
        raise ValueError("cannot thumbnail an empty image")
    thumb = resize_to_fit(image, max_side)
    ok, encoded = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("JPEG encoding failed")
    dest.write_bytes(encoded.tobytes())
