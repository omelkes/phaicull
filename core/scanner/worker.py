"""Brawn worker — per-file image processing in a subprocess.

Runs in ProcessPoolExecutor. Receives a Path, loads the image safely,
runs all analyzers on the decoded array (decode once, analyze many),
and returns a FileResult. No DB access, no asyncio.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field

from core.analyzers.base import AnalyzerResult, BaseAnalyzer
from core.loader.image_loader import LoadFailure, try_load_image
from core.utils.thumbnail import write_thumbnail


class FileResult(BaseModel):
    """Result of processing a single file in Brawn. Crosses the process boundary."""

    file_path: str
    content_hash: str | None = None
    status: str = "ok"
    status_reason: str | None = Field(
        default=None, description="LoadFailure code when status is load_failed."
    )
    metrics: list[AnalyzerResult] = Field(default_factory=list)
    analyzer_errors: int = Field(
        default=0, description="Number of analyzers that raised on this file."
    )
    staged_thumbnail: str | None = Field(
        default=None,
        description="Thumbnail written under a temporary name; Brain renames it to "
        "thumb_<file_id>.jpg once the row id is known.",
    )
    thumbnail_failed: bool = Field(
        default=False, description="Thumbnail generation was attempted and raised."
    )


def _compute_content_hash(path: Path) -> str | None:
    """SHA-256 of file bytes. Returns None on read error."""
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def process_file(
    file_path: Path,
    analyzers: list[BaseAnalyzer],
    *,
    max_file_size_bytes: int,
    max_dimension: int,
    thumbnail_staging_dir: Path | None = None,
) -> FileResult:
    """Process a single image file: load, hash, analyze, thumbnail.

    The image is decoded exactly once; the resulting BGR array is passed to
    every analyzer (BaseAnalyzer contract v2) and, when thumbnail_staging_dir
    is given, resized into a thumbnail under a unique temporary name.

    Designed to run in a subprocess via ProcessPoolExecutor.
    Never raises — all errors are captured in the returned FileResult.
    """
    file_path = Path(file_path).resolve()
    result = FileResult(file_path=str(file_path))

    result.content_hash = _compute_content_hash(file_path)

    img, failure = try_load_image(
        file_path,
        max_file_size_bytes=max_file_size_bytes,
        max_dimension=max_dimension,
    )

    if img is None:
        result.status = "load_failed"
        result.status_reason = (failure or LoadFailure.DECODE_FAILED).value
        logger.warning("Skipped {} ({})", file_path, result.status_reason)
        return result

    for analyzer in analyzers:
        try:
            metric = analyzer.analyze(img, file_path)
            if metric is not None:
                result.metrics.append(metric)
        except Exception:
            result.analyzer_errors += 1
            logger.debug(
                "Analyzer {} failed on {}", analyzer.metric_name, file_path
            )

    if thumbnail_staging_dir is not None:
        staged = Path(thumbnail_staging_dir) / f"{uuid.uuid4().hex}.jpg"
        try:
            write_thumbnail(img, staged)
            result.staged_thumbnail = str(staged)
        except Exception:
            result.thumbnail_failed = True
            staged.unlink(missing_ok=True)
            logger.debug("Thumbnail failed for {}", file_path)

    return result
