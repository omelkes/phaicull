"""File discovery (Brain-side) for scan pipeline.

Walks a directory recursively, applies path scope safety and MIME
validation gate, and returns valid image paths plus MIME-rejected paths
(so the pipeline can log rejections to the SQLite status column).
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field

from core.database.schema import PROJECT_PHAICULL_SUBDIR
from core.utils.mime import is_supported_image
from core.utils.path_safety import validate_scan_path


class DiscoveryResult(BaseModel):
    """Outcome of walking a scan root."""

    valid: list[Path] = Field(default_factory=list, description="Supported image files.")
    rejected_mime: list[Path] = Field(
        default_factory=list,
        description="Files that failed MIME magic-byte validation (logged to DB status).",
    )


def discover_files(scan_root: Path) -> DiscoveryResult:
    """Walk scan_root recursively and classify files.

    Applies these gates in order:
    1. Phaicull data directory — files under {scan_root}/phaicull/ (the project
       DB and caches) are never scanned.
    2. Path scope safety — paths that escape scan_root are skipped silently
       (debug log only; they are outside project scope by definition).
    3. MIME validation — files that are not supported image types are returned
       in rejected_mime so the caller can record them in SQLite.

    Never raises for individual files.
    """
    scan_root = scan_root.resolve()
    result = DiscoveryResult()

    if not scan_root.is_dir():
        logger.error("Scan root is not a directory: {}", scan_root)
        return result

    phaicull_dir = scan_root / PROJECT_PHAICULL_SUBDIR

    for file_path in sorted(scan_root.rglob("*")):
        if not file_path.is_file():
            continue

        if phaicull_dir in file_path.parents:
            continue

        if not validate_scan_path(file_path, scan_root):
            logger.debug("Skipped (path safety): {}", file_path)
            continue

        if not is_supported_image(file_path):
            logger.debug("Rejected (unsupported MIME): {}", file_path)
            result.rejected_mime.append(file_path)
            continue

        result.valid.append(file_path)

    logger.info(
        "Discovered {} valid image files ({} MIME-rejected) in {}",
        len(result.valid),
        len(result.rejected_mime),
        scan_root,
    )
    return result
