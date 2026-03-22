"""Tests for Brain/Brawn scan pipeline (end-to-end)."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from core.config import Config
from core.database.dao import open_project_connection
from core.scanner.pipeline import ScanSummary, run_scan


def test_scan_small_directory(tmp_path: Path) -> None:
    """End-to-end: scan a temp directory with synthetic images, verify DB rows."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    Image.new("RGB", (32, 32), color=(255, 0, 0)).save(scan_root / "red.jpg", "JPEG")
    Image.new("RGB", (32, 32), color=(0, 255, 0)).save(scan_root / "green.png", "PNG")
    (scan_root / "notes.txt").write_text("ignore me")

    config = Config()
    summary = asyncio.run(run_scan(scan_root, config))

    assert isinstance(summary, ScanSummary)
    assert summary.total_discovered == 2
    assert summary.processed == 2
    assert summary.load_failed == 0

    conn = open_project_connection(scan_root)
    try:
        rows = conn.execute("SELECT file_path, status FROM files ORDER BY file_path").fetchall()
        assert len(rows) == 2
        statuses = {r["status"] for r in rows}
        assert statuses == {"ok"}
    finally:
        conn.close()


def test_scan_with_corrupted_image(tmp_path: Path) -> None:
    """Corrupted image gets load_failed status in DB; does not crash scan."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    Image.new("RGB", (16, 16)).save(scan_root / "good.jpg", "JPEG")
    bad = scan_root / "bad.jpg"
    bad.write_bytes(b"\xff\xd8\xff\xe0JUNK")

    config = Config()
    summary = asyncio.run(run_scan(scan_root, config))

    assert summary.total_discovered == 2
    assert summary.processed == 1
    assert summary.load_failed == 1

    conn = open_project_connection(scan_root)
    try:
        statuses = {
            r["file_path"].split("/")[-1]: r["status"]
            for r in conn.execute("SELECT file_path, status FROM files").fetchall()
        }
        assert statuses["good.jpg"] == "ok"
        assert statuses["bad.jpg"] == "load_failed"
    finally:
        conn.close()


def test_scan_empty_directory(tmp_path: Path) -> None:
    """Empty directory produces zero-count summary without errors."""
    scan_root = tmp_path / "empty"
    scan_root.mkdir()

    config = Config()
    summary = asyncio.run(run_scan(scan_root, config))

    assert summary.total_discovered == 0
    assert summary.processed == 0


def test_scan_creates_project_db(tmp_path: Path) -> None:
    """Scan creates the project DB (phaicull/phaicull.db) inside scan root."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    Image.new("RGB", (8, 8)).save(scan_root / "img.jpg", "JPEG")

    asyncio.run(run_scan(scan_root, Config()))

    db_path = scan_root / "phaicull" / "phaicull.db"
    assert db_path.exists()


def test_scan_idempotent(tmp_path: Path) -> None:
    """Running scan twice on the same folder doesn't duplicate files (upsert)."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    Image.new("RGB", (8, 8)).save(scan_root / "img.jpg", "JPEG")
    config = Config()

    asyncio.run(run_scan(scan_root, config))
    asyncio.run(run_scan(scan_root, config))

    conn = open_project_connection(scan_root)
    try:
        count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        assert count == 1
    finally:
        conn.close()
