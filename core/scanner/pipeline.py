"""Brain — asyncio scan orchestration for Phaicull.

Discovers files, dispatches them to Brawn (ProcessPoolExecutor) for
image loading and analysis, then batch-writes results to the project DB.
"""

from __future__ import annotations

import asyncio
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


class ScanSummary(BaseModel):
    """Summary statistics from a completed scan."""

    total_discovered: int = 0
    processed: int = 0
    load_failed: int = 0
    analyzer_errors: int = 0
    skipped_mime: int = Field(
        default=0, description="Files skipped by MIME gate during discovery."
    )


async def run_scan(scan_root: Path, config: Config) -> ScanSummary:
    """Run a full scan of scan_root using the Brain/Brawn pipeline.

    Brain (this coroutine): file-walking, I/O, DB writes.
    Brawn (ProcessPoolExecutor): image loading + analyzers.
    """
    scan_root = scan_root.resolve()
    summary = ScanSummary()

    files = discover_files(scan_root)
    summary.total_discovered = len(files)

    if not files:
        logger.info("No valid image files found in {}", scan_root)
        return summary

    conn = open_project_connection(scan_root)
    analyzers = get_sprint1_analyzers()
    max_file_size_bytes = config.loader.max_file_size_bytes
    max_dimension = config.loader.max_image_dimension

    loop = asyncio.get_running_loop()
    max_workers = max(1, (len(files) if len(files) < 4 else 4))

    try:
        worker_fn = partial(
            process_file,
            analyzers=analyzers,
            max_file_size_bytes=max_file_size_bytes,
            max_dimension=max_dimension,
        )
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                loop.run_in_executor(executor, worker_fn, fp)
                for fp in files
            ]

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
    finally:
        conn.close()

    logger.info(
        "Scan complete: {} discovered, {} processed, {} load failures",
        summary.total_discovered,
        summary.processed,
        summary.load_failed,
    )
    return summary


def _write_result_to_db(
    conn: "sqlite3.Connection",  # noqa: F821
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
