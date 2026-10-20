"""Tests for Brain/Brawn scan pipeline (end-to-end)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from core.config import Config
from core.database.dao import open_project_connection
from core.scanner import pipeline
from core.scanner.pipeline import ScanSummary, run_scan


def _structured_image(size: int = 256) -> Image.Image:
    """Photo-like low-frequency structure, so pHash bits survive a JPEG re-save.

    Solid colors all hash alike; too-simple patterns leave bits near the median.
    """
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    gray = (
        128
        + 55 * np.sin(xx / 17.0)
        + 45 * np.cos(yy / 23.0)
        + 25 * np.sin((xx + 2 * yy) / 31.0)
    )
    return Image.fromarray(np.clip(gray, 0, 255).astype(np.uint8)).convert("RGB")


def _group_ids_by_name(scan_root: Path) -> dict[str, int | None]:
    conn = open_project_connection(scan_root)
    try:
        rows = conn.execute("SELECT file_path, group_id FROM files").fetchall()
        return {Path(r["file_path"]).name: r["group_id"] for r in rows}
    finally:
        conn.close()


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
    assert summary.skipped_mime == 1  # notes.txt

    conn = open_project_connection(scan_root)
    try:
        statuses = {
            r["file_path"].split("/")[-1]: r["status"]
            for r in conn.execute("SELECT file_path, status FROM files").fetchall()
        }
        assert statuses["red.jpg"] == "ok"
        assert statuses["green.png"] == "ok"
        assert statuses["notes.txt"] == "skipped_invalid_mime"
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


def test_scan_writes_all_sprint1_metrics(tmp_path: Path) -> None:
    """All Sprint 1 analyzers succeed: metrics rows written, zero analyzer errors."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    Image.new("RGB", (64, 64), color=(120, 80, 40)).save(scan_root / "img.jpg", "JPEG")

    summary = asyncio.run(run_scan(scan_root, Config()))

    assert summary.processed == 1
    assert summary.analyzer_errors == 0

    conn = open_project_connection(scan_root)
    try:
        rows = conn.execute(
            "SELECT metric_name, value_real, value_text FROM metrics ORDER BY metric_name"
        ).fetchall()
        metrics = {r["metric_name"]: (r["value_real"], r["value_text"]) for r in rows}
        assert set(metrics) == {
            "blur_score",
            "brightness_score",
            "contrast_score",
            "phash",
        }
        assert 0.0 <= metrics["blur_score"][0] <= 1.0
        assert 0.0 <= metrics["brightness_score"][0] <= 1.0
        assert 0.0 <= metrics["contrast_score"][0] <= 1.0
        assert len(metrics["phash"][1]) == 16
    finally:
        conn.close()


def test_rescan_does_not_duplicate_mime_rejected(tmp_path: Path) -> None:
    """MIME-rejected files get one status row, stable across rescans."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    (scan_root / "notes.txt").write_text("not an image")
    config = Config()

    asyncio.run(run_scan(scan_root, config))
    asyncio.run(run_scan(scan_root, config))

    conn = open_project_connection(scan_root)
    try:
        rows = conn.execute(
            "SELECT file_path, status FROM files WHERE status = 'skipped_invalid_mime'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["file_path"].endswith("notes.txt")
    finally:
        conn.close()


def test_scan_groups_near_duplicates(tmp_path: Path) -> None:
    """Two saves of one photo share a group; a different photo and rejects stay NULL."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    photo = _structured_image()
    photo.save(scan_root / "shot.jpg", "JPEG", quality=95)
    photo.save(scan_root / "shot_copy.jpg", "JPEG", quality=60)
    photo.rotate(90).save(scan_root / "other.jpg", "JPEG")
    (scan_root / "broken.jpg").write_bytes(b"\xff\xd8\xff\xe0JUNK")
    (scan_root / "notes.txt").write_text("not an image")

    summary = asyncio.run(run_scan(scan_root, Config()))

    assert summary.duplicate_groups == 1
    groups = _group_ids_by_name(scan_root)
    assert groups["shot.jpg"] is not None
    assert groups["shot.jpg"] == groups["shot_copy.jpg"]
    assert groups["other.jpg"] is None
    assert groups["broken.jpg"] is None
    assert groups["notes.txt"] is None


def test_rescan_keeps_group_ids(tmp_path: Path) -> None:
    """An unchanged folder keeps the same group ids across scans."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    photo = _structured_image()
    photo.save(scan_root / "a.jpg", "JPEG")
    photo.save(scan_root / "b.jpg", "JPEG")
    config = Config()

    asyncio.run(run_scan(scan_root, config))
    first = _group_ids_by_name(scan_root)
    asyncio.run(run_scan(scan_root, config))

    assert first["a.jpg"] is not None
    assert _group_ids_by_name(scan_root) == first


def test_grouping_failure_keeps_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If grouping raises, the scan still finishes and metrics stay in the DB."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    _structured_image().save(scan_root / "a.jpg", "JPEG")

    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline, "regroup", fail)
    summary = asyncio.run(run_scan(scan_root, Config()))

    assert summary.processed == 1
    assert summary.duplicate_groups == 0
    conn = open_project_connection(scan_root)
    try:
        count = conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
        assert count > 0
    finally:
        conn.close()


def _file_ids_by_name(scan_root: Path) -> dict[str, int]:
    conn = open_project_connection(scan_root)
    try:
        rows = conn.execute("SELECT id, file_path FROM files").fetchall()
        return {Path(r["file_path"]).name: r["id"] for r in rows}
    finally:
        conn.close()


def test_scan_writes_thumbnails_named_by_file_id(tmp_path: Path) -> None:
    """Each ok file gets phaicull/thumbs/thumb_<id>.jpg (≤300px); broken files get none."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    Image.new("RGB", (1200, 800), color=(200, 30, 30)).save(scan_root / "big.jpg", "JPEG")
    Image.new("RGB", (40, 30), color=(30, 200, 30)).save(scan_root / "small.png", "PNG")
    (scan_root / "broken.jpg").write_bytes(b"\xff\xd8\xff\xe0JUNK")

    summary = asyncio.run(run_scan(scan_root, Config()))

    assert summary.thumbnails == 2
    assert summary.thumbnail_errors == 0
    thumbs = scan_root / "phaicull" / "thumbs"
    ids = _file_ids_by_name(scan_root)
    with Image.open(thumbs / f"thumb_{ids['big.jpg']}.jpg") as thumb:
        assert thumb.size == (300, 200)
    with Image.open(thumbs / f"thumb_{ids['small.png']}.jpg") as thumb:
        assert thumb.size == (40, 30)
    assert not (thumbs / f"thumb_{ids['broken.jpg']}.jpg").exists()
    assert not (thumbs / ".staging").exists()


def test_rescan_keeps_one_thumbnail_per_file(tmp_path: Path) -> None:
    """Rescans overwrite thumb_<id>.jpg in place; no extra files accumulate."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    Image.new("RGB", (500, 500)).save(scan_root / "a.jpg", "JPEG")
    config = Config()

    asyncio.run(run_scan(scan_root, config))
    asyncio.run(run_scan(scan_root, config))

    thumbs = scan_root / "phaicull" / "thumbs"
    ids = _file_ids_by_name(scan_root)
    assert sorted(p.name for p in thumbs.iterdir()) == [f"thumb_{ids['a.jpg']}.jpg"]


def test_thumbnail_removed_when_file_stops_loading(tmp_path: Path) -> None:
    """A photo that later becomes unreadable must not keep showing its old thumbnail."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    photo = scan_root / "a.jpg"
    Image.new("RGB", (500, 500)).save(photo, "JPEG")
    config = Config()

    asyncio.run(run_scan(scan_root, config))
    thumb = scan_root / "phaicull" / "thumbs" / f"thumb_{_file_ids_by_name(scan_root)['a.jpg']}.jpg"
    assert thumb.exists()

    photo.write_bytes(b"\xff\xd8\xff\xe0JUNK")
    asyncio.run(run_scan(scan_root, config))

    assert not thumb.exists()


def test_scan_ignores_own_phaicull_db(tmp_path: Path) -> None:
    """A rescan must not record the project's own phaicull/ data directory."""
    scan_root = tmp_path / "photos"
    scan_root.mkdir()
    Image.new("RGB", (8, 8)).save(scan_root / "img.jpg", "JPEG")
    config = Config()

    asyncio.run(run_scan(scan_root, config))  # creates phaicull/phaicull.db
    summary = asyncio.run(run_scan(scan_root, config))

    assert summary.skipped_mime == 0

    conn = open_project_connection(scan_root)
    try:
        rows = conn.execute("SELECT file_path FROM files").fetchall()
        assert all("/phaicull/" not in r["file_path"] for r in rows)
    finally:
        conn.close()
