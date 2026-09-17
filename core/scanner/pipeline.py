"""Brain — asyncio scan orchestration for Phaicull.

Discovers files, dispatches them to Brawn (ProcessPoolExecutor) for
image loading and analysis, then batch-writes results to the project DB.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field

from core.analyzers import get_sprint1_analyzers
from core.config import Config
from core.database.dao import insert_file, insert_metric, open_project_connection
from core.scanner.walker import discover_files
from core.scanner.worker import FileResult, process_file

BATCH_COMMIT_SIZE = 50

# Status written to the files table for MIME-rejected files.
# Stable value per docs/json_contract_scan_v1.md.
STATUS_SKIPPED_INVALID_MIME = "skipped_invalid_mime"


class ScanSummary(BaseModel):
    """Summary statistics from a completed scan."""

    total_discovered: int = 0
    processed: int = 0
    load_failed: int = 0
    analyzer_errors: int = 0
    skipped_mime: int = Field(
        default=0, description="Files rejected by the MIME gate during discovery."
    )


def _resolve_max_workers(config: Config, file_count: int) -> int:
    """Worker pool size: config override, else cpu_count; never more than files."""
    workers = config.scanner.max_workers or os.cpu_count() or 1
    return max(1, min(workers, file_count))


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
            await _process_files(conn, files, config, summary)
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
) -> None:
    """Dispatch files to Brawn workers and batch-write results."""
    analyzers = get_sprint1_analyzers()
    loop = asyncio.get_running_loop()
    max_workers = _resolve_max_workers(config, len(files))

    worker_fn = partial(
        process_file,
        analyzers=analyzers,
        max_file_size_bytes=config.loader.max_file_size_bytes,
        max_dimension=config.loader.max_image_dimension,
    )
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [loop.run_in_executor(executor, worker_fn, fp) for fp in files]

        pending = 0
        for i, coro in enumerate(asyncio.as_completed(futures)):
            result: FileResult = await coro
            _write_result_to_db(conn, result, summary)
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
) -> None:
    """Write a FileResult to the project DB and update summary counters."""
    file_id = insert_file(
        conn,
        result.file_path,
        content_hash=result.content_hash,
        status=result.status,
    )

    if result.status == "load_failed":
        summary.load_failed += 1
        return

    summary.processed += 1
    summary.analyzer_errors += result.analyzer_errors

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
