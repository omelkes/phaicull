"""Tests for database DAO (project and registry)."""

from pathlib import Path

import pytest

from core.database.dao import (
    add_project,
    ensure_project_db,
    ensure_registry_db,
    get_project_db_path,
    get_registry_db_path,
    insert_file,
    insert_metric,
    list_projects,
    open_project_connection,
    open_registry_connection,
)


def test_get_project_db_path() -> None:
    """Project DB path is project_root/phaicull/phaicull.db."""
    root = Path("/foo/bar")
    assert get_project_db_path(root) == Path("/foo/bar/phaicull/phaicull.db")


def test_get_registry_db_path_default(tmp_path: Path) -> None:
    """Registry DB path with base_dir is base/.projects/registry.db."""
    reg = get_registry_db_path(tmp_path)
    assert reg == tmp_path / ".projects" / "registry.db"


def test_ensure_project_db_creates_dir_and_db(tmp_path: Path) -> None:
    """ensure_project_db creates phaicull/ and phaicull.db and runs migrations."""
    project_root = tmp_path / "my_photos"
    db_path = ensure_project_db(project_root)
    assert db_path.exists()
    assert db_path.name == "phaicull.db"
    assert db_path.parent.name == "phaicull"
    assert project_root / "phaicull" / "phaicull.db" == db_path


def test_ensure_registry_db_creates_dir_and_db(tmp_path: Path) -> None:
    """ensure_registry_db creates .projects/ and registry.db."""
    db_path = ensure_registry_db(tmp_path)
    assert db_path.exists()
    assert db_path.name == "registry.db"
    assert db_path.parent.name == ".projects"


def test_open_project_connection_insert_file(tmp_path: Path) -> None:
    """Open project conn, insert a file, read it back."""
    project_root = tmp_path / "photos"
    conn = open_project_connection(project_root)
    try:
        fid = insert_file(conn, "/photos/img1.jpg", content_hash="abc", status="ok")
        conn.commit()
        assert fid > 0
        row = conn.execute("SELECT file_path, content_hash, status FROM files WHERE id = ?", (fid,)).fetchone()
        assert row is not None
        assert row[0] == "/photos/img1.jpg"
        assert row[1] == "abc"
        assert row[2] == "ok"
    finally:
        conn.close()


def test_add_project_list_projects(tmp_path: Path) -> None:
    """Registry: add project, list projects."""
    conn = open_registry_connection(tmp_path)
    try:
        add_project(conn, "/abs/path/to/photos", name="Holiday")
        conn.commit()
        projects = list_projects(conn)
        assert len(projects) == 1
        assert projects[0]["path"] == "/abs/path/to/photos"
        assert projects[0]["name"] == "Holiday"
        assert "added_at" in projects[0]
    finally:
        conn.close()


def test_add_project_idempotent(tmp_path: Path) -> None:
    """Adding same path twice updates name, single row."""
    conn = open_registry_connection(tmp_path)
    try:
        add_project(conn, "/same/path", name="First")
        add_project(conn, "/same/path", name="Second")
        conn.commit()
        projects = list_projects(conn)
        assert len(projects) == 1
        assert projects[0]["name"] == "Second"
    finally:
        conn.close()


# --- insert_metric ---


def test_insert_metric_numeric(tmp_path: Path) -> None:
    """Insert blur_score (value_real), read back."""
    project_root = tmp_path / "photos"
    conn = open_project_connection(project_root)
    try:
        fid = insert_file(conn, "/photos/img1.jpg", status="ok")
        conn.commit()
        insert_metric(conn, fid, "blur_score", value_real=0.42)
        conn.commit()
        row = conn.execute(
            "SELECT metric_name, value_real, value_text FROM metrics WHERE file_id = ?",
            (fid,),
        ).fetchone()
        assert row is not None
        assert row[0] == "blur_score"
        assert row[1] == 0.42
        assert row[2] is None
    finally:
        conn.close()


def test_insert_metric_text(tmp_path: Path) -> None:
    """Insert phash (value_text), read back."""
    project_root = tmp_path / "photos"
    conn = open_project_connection(project_root)
    try:
        fid = insert_file(conn, "/photos/img2.jpg", status="ok")
        conn.commit()
        insert_metric(conn, fid, "phash", value_text="ff00aa55cc33dd99")
        conn.commit()
        row = conn.execute(
            "SELECT metric_name, value_real, value_text FROM metrics WHERE file_id = ?",
            (fid,),
        ).fetchone()
        assert row is not None
        assert row[0] == "phash"
        assert row[1] is None
        assert row[2] == "ff00aa55cc33dd99"
    finally:
        conn.close()


def test_insert_metric_upsert(tmp_path: Path) -> None:
    """Insert same (file_id, metric_name) twice; second overwrites first."""
    project_root = tmp_path / "photos"
    conn = open_project_connection(project_root)
    try:
        fid = insert_file(conn, "/photos/img3.jpg", status="ok")
        conn.commit()
        insert_metric(conn, fid, "blur_score", value_real=0.3)
        conn.commit()
        insert_metric(conn, fid, "blur_score", value_real=0.7)
        conn.commit()
        rows = conn.execute(
            "SELECT metric_name, value_real FROM metrics WHERE file_id = ?", (fid,)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "blur_score"
        assert rows[0][1] == 0.7
    finally:
        conn.close()


def test_insert_metric_after_insert_file(tmp_path: Path) -> None:
    """Full flow: insert_file, insert_metric, assert row in metrics."""
    project_root = tmp_path / "photos"
    conn = open_project_connection(project_root)
    try:
        fid = insert_file(conn, "/vacation/beach.heic", content_hash="abc123", status="ok")
        conn.commit()
        insert_metric(conn, fid, "blur_score", value_real=0.15)
        insert_metric(conn, fid, "brightness_score", value_real=0.82)
        insert_metric(conn, fid, "phash", value_text="deadbeef")
        conn.commit()
        rows = conn.execute(
            "SELECT metric_name, value_real, value_text FROM metrics WHERE file_id = ? ORDER BY metric_name",
            (fid,),
        ).fetchall()
        assert len(rows) == 3
        assert tuple(rows[0]) == ("blur_score", 0.15, None)
        assert tuple(rows[1]) == ("brightness_score", 0.82, None)
        assert tuple(rows[2]) == ("phash", None, "deadbeef")
    finally:
        conn.close()
