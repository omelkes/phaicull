"""Brawn worker — per-file image processing in a subprocess.

Runs in ProcessPoolExecutor. Receives a Path, loads the image safely,
runs all analyzers, and returns a FileResult. No DB access, no asyncio.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field

from core.analyzers.base import AnalyzerResult, BaseAnalyzer
from core.loader.image_loader import load_image


class FileResult(BaseModel):
    """Result of processing a single file in Brawn. Crosses the process boundary."""

    file_path: str
    content_hash: str | None = None
    status: str = "ok"
    metrics: list[AnalyzerResult] = Field(default_factory=list)


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
) -> FileResult:
    """Process a single image file: load, hash, analyze.

    Designed to run in a subprocess via ProcessPoolExecutor.
    Never raises — all errors are captured in the returned FileResult.
    """
    file_path = Path(file_path).resolve()
    result = FileResult(file_path=str(file_path))

    result.content_hash = _compute_content_hash(file_path)

    img = load_image(
        file_path,
        max_file_size_bytes=max_file_size_bytes,
        max_dimension=max_dimension,
    )

    if img is None:
        result.status = "load_failed"
        logger.debug("Image load failed: {}", file_path)
        return result

    for analyzer in analyzers:
        try:
            metric = analyzer.analyze(file_path)
            if metric is not None:
                result.metrics.append(metric)
        except Exception:
            logger.debug(
                "Analyzer {} failed on {}", analyzer.metric_name, file_path
            )

    return result
