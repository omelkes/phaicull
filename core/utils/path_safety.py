"""Path scope safety for Phaicull scans.

Per AGENTS.md: use Path.resolve() to ensure operations stay within project scope.
Reject or skip symlinks/paths that escape the scan folder root.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger


def validate_scan_path(file_path: Path, scan_root: Path) -> bool:
    """Return True if file_path is safely within scan_root.

    Resolves both paths (following symlinks) and checks containment.
    Returns False and logs a warning for paths that escape scan_root.
    """
    try:
        resolved_root = scan_root.resolve(strict=True)
        resolved_file = file_path.resolve(strict=True)
    except (OSError, ValueError):
        logger.warning("Path resolution failed: {}", file_path)
        return False

    if not resolved_file.is_file():
        return False

    try:
        resolved_file.relative_to(resolved_root)
    except ValueError:
        logger.warning(
            "Path escapes scan root: {} -> {} (root: {})",
            file_path,
            resolved_file,
            resolved_root,
        )
        return False

    return True
