"""File discovery (Brain-side) for scan pipeline.

Walks a directory recursively, applies path scope safety and MIME
validation gate, and returns the list of valid image file paths.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from core.utils.mime import is_supported_image
from core.utils.path_safety import validate_scan_path


def discover_files(scan_root: Path) -> list[Path]:
    """Walk scan_root recursively and return valid image file paths.

    Applies two gates in order:
    1. Path scope safety — reject paths that escape scan_root.
    2. MIME validation — reject files that are not supported image types.

    Skipped files are logged but do not cause errors.
    """
    scan_root = scan_root.resolve()
    valid: list[Path] = []

    if not scan_root.is_dir():
        logger.error("Scan root is not a directory: {}", scan_root)
        return valid

    for file_path in sorted(scan_root.rglob("*")):
        if not file_path.is_file():
            continue

        if not validate_scan_path(file_path, scan_root):
            logger.debug("Skipped (path safety): {}", file_path)
            continue

        if not is_supported_image(file_path):
            logger.debug("Skipped (unsupported MIME): {}", file_path)
            continue

        valid.append(file_path)

    logger.info("Discovered {} valid image files in {}", len(valid), scan_root)
    return valid
