"""Brain — asyncio scan orchestration for Phaicull.

Discovers files, dispatches them to Brawn (ProcessPoolExecutor) for
image loading and analysis, then batch-writes results to the project DB.
"""

from __future__ import annotations

import asyncio
import multiprocessing as mp
import os
import shutil
import sqlite3
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field

from core.analyzers import get_sprint1_analyzers
from core.config import Config
from core.database.dao import insert_file, insert_metric, open_project_connection
from core.grouping import regroup
from core.scanner.walker import discover_files
from core.scanner.worker import FileResult, process_file
from core.utils.thumbnail import STAGING_SUBDIR, get_thumbs_dir, thumbnail_name

BATCH_COMMIT_SIZE = 50

# Status written to the files table for MIME-rejected files.
# Stable value per docs/json_contract_scan_v1.md.
STATUS_SKIPPED_INVALID_MIME = "skipped_invalid_mime"


class ScanSummary(BaseModel):
    """Summary statistics from a completed scan."""

    total_discovered: int = 0
    processed: int = 0
    load_failed: int = 0
    load_failure_reasons: dict[str, int] = Field(
        default_factory=dict, description="load_failed count per files.status_reason."
    )
    analyzer_errors: int = 0
    skipped_mime: int = Field(
        default=0, description="Files rejected by the MIME gate during discovery."
    )
    duplicate_groups: int = Field(
        default=0, description="Near-duplicate groups (two or more files) after grouping."
    )
    thumbnails: int = Field(default=0, description="Thumbnails written this scan.")
    thumbnail_errors: int = Field(
        default=0, description="Processed files whose thumbnail could not be written."
    )


def _resolve_max_workers(config: Config, file_count: int) -> int:
    """Worker pool size: config override, else cpu_count; never more than files."""
    workers = config.scanner.max_workers or os.cpu_count() or 1
    return max(1, min(workers, file_count))


def _mp_context() -> mp.context.BaseContext:
    """Process start method for Brawn workers.

    Default ``fork`` is unsafe once the parent has threads (pytest, loguru)
    and raises a DeprecationWarning on Python 3.12+. ``spawn`` is portable
    and avoids inheriting the parent's thread state.
    """
    return mp.get_context("spawn")


async def run_scan(scan_root: Path, config: Config) -> ScanSummary:
    """Run a full scan of scan_root using the Brain/Brawn pipeline.

    Brain (this coroutine): file-walking, I/O, DB writes.
    Brawn (ProcessPoolExecutor): image loading + analyzers.
    """
    scan_root = scan_root.resolve()
    summary = ScanSummary()

    discovery = discover_files(scan_root)
    files = discovery.valid
    summary.total_discovered = len(files)
    summary.skipped_mime = len(discovery.rejected_mime)

    if not files and not discovery.rejected_mime:
        logger.info("No files found in {}", scan_root)
        return summary

    conn = open_project_connection(scan_root)
    try:
        _write_mime_rejections(conn, discovery.rejected_mime)

        if files:
            await _process_files(conn, files, config, summary, get_thumbs_dir(scan_root))

        _run_grouping(conn, config, summary)
    finally:
        conn.close()

    logger.info(
        "Scan complete: {} discovered, {} processed, {} load failures, "
        "{} analyzer errors, {} MIME-rejected",
        summary.total_discovered,
        summary.processed,
        summary.load_failed,
        summary.analyzer_errors,
        summary.skipped_mime,
    )
    return summary


async def _process_files(
    conn: sqlite3.Connection,
    files: list[Path],
    config: Config,
    summary: ScanSummary,
    thumbs_dir: Path,
) -> None:
    """Dispatch files to Brawn workers and batch-write results in input order."""
    analyzers = get_sprint1_analyzers()
    loop = asyncio.get_running_loop()
    max_workers = _resolve_max_workers(config, len(files))

    staging_dir = thumbs_dir / STAGING_SUBDIR
    shutil.rmtree(staging_dir, ignore_errors=True)  # leftovers from an interrupted scan
    staging_dir.mkdir(parents=True, exist_ok=True)

    worker_fn = partial(
        process_file,
        analyzers=analyzers,
        max_file_size_bytes=config.loader.max_file_size_bytes,
        max_dimension=config.loader.max_image_dimension,
        thumbnail_staging_dir=staging_dir,
    )
    try:
        with ProcessPoolExecutor(
            max_workers=max_workers, mp_context=_mp_context()
        ) as executor:
            futures = [loop.run_in_executor(executor, worker_fn, fp) for fp in files]

            # Write in discovery order, not completion order: new files get the
            # same files.id (and thumb_<id>.jpg) regardless of worker count.
            pending = 0
            for i, future in enumerate(futures):
                result: FileResult = await future
                _write_result_to_db(conn, result, summary, thumbs_dir)
                pending += 1

                if pending >= BATCH_COMMIT_SIZE:
                    conn.commit()
                    pending = 0
                    logger.info(
                        "Progress: {}/{} files processed",
                        i + 1,
                        summary.total_discovered,
                    )

            if pending > 0:
                conn.commit()
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


def _run_grouping(conn: sqlite3.Connection, config: Config, summary: ScanSummary) -> None:
    """Regroup near-duplicates. Metrics are already committed; a failure here keeps them."""
    try:
        result = regroup(conn, hamming_max=config.phash_hamming_max)
    except Exception:
        logger.exception("Grouping failed; scan metrics are kept")
        return
    summary.duplicate_groups = result.duplicate_groups


def _place_thumbnail(result: FileResult, thumb_path: Path, summary: ScanSummary) -> None:
    """Move the worker's staged thumbnail to thumb_<id>.jpg (atomic replace)."""
    if result.thumbnail_failed or result.staged_thumbnail is None:
        summary.thumbnail_errors += 1
        return
    try:
        Path(result.staged_thumbnail).replace(thumb_path)
    except OSError:
        summary.thumbnail_errors += 1
        logger.debug("Cannot place thumbnail for {}", result.file_path)
        return
    summary.thumbnails += 1


def _write_mime_rejections(conn: sqlite3.Connection, rejected: list[Path]) -> None:
    """Record MIME-rejected files in the files table with a skipped status."""
    for path in rejected:
        insert_file(conn, str(path), status=STATUS_SKIPPED_INVALID_MIME)
    if rejected:
        conn.commit()


def _write_result_to_db(
    conn: sqlite3.Connection,
    result: FileResult,
    summary: ScanSummary,
    thumbs_dir: Path,
) -> None:
    """Write a FileResult to the project DB and update summary counters."""
    file_id = insert_file(
        conn,
        result.file_path,
        content_hash=result.content_hash,
        status=result.status,
        status_reason=result.status_reason,
    )
    thumb_path = thumbs_dir / thumbnail_name(file_id)

    if result.status == "load_failed":
        summary.load_failed += 1
        reason = result.status_reason or "unknown"
        summary.load_failure_reasons[reason] = summary.load_failure_reasons.get(reason, 0) + 1
        thumb_path.unlink(missing_ok=True)  # do not keep showing a photo that no longer loads
        return

    summary.processed += 1
    summary.analyzer_errors += result.analyzer_errors
    _place_thumbnail(result, thumb_path, summary)

    for metric in result.metrics:
        try:
            insert_metric(
                conn,
                file_id,
                metric.metric_name,
                value_real=metric.value_real,
                value_text=metric.value_text,
            )
        except Exception:
            summary.analyzer_errors += 1
            logger.debug(
                "Failed to write metric {} for {}",
                metric.metric_name,
                result.file_path,
            )
