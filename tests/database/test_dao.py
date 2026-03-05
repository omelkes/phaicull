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
