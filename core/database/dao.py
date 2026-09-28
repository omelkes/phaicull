"""Data Access Objects for Phaicull SQLite databases.

All SQL lives in this module (per AGENTS.md). Two databases:
- Project DB: path = project_root / phaicull / phaicull.db (files, metrics, groups).
- Registry DB: path = base_dir / .projects / registry.db (list of projects).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import NamedTuple

from core.database import schema
from core.database.connection import enable_wal
from core.database.migrate import migrate, migrate_registry


def get_project_db_path(project_root: Path) -> Path:
    """Return the path to the project SQLite DB for the given project root."""
    return Path(project_root).resolve() / schema.PROJECT_PHAICULL_SUBDIR / schema.PROJECT_DB_NAME


def get_registry_db_path(base_dir: Path | None = None) -> Path:
    """Return the registry DB path. base_dir defaults to repo/install root (parent of core)."""
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent.parent
    return Path(base_dir).resolve() / schema.PROJECTS_DIR_NAME / schema.REGISTRY_DB_NAME


def ensure_project_db(project_root: Path) -> Path:
    """Create project directory and run migrations. Returns path to project DB."""
    db_path = get_project_db_path(project_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    migrate(db_path)
    return db_path


def ensure_registry_db(base_dir: Path | None = None) -> Path:
    """Create .projects dir and run registry migrations. Returns path to registry DB."""
    db_path = get_registry_db_path(base_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    migrate_registry(db_path)
    return db_path


def open_project_connection(project_root: Path) -> sqlite3.Connection:
    """Open a connection to the project DB (migrations applied). Caller must close."""
    db_path = ensure_project_db(project_root)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    enable_wal(conn)
    return conn


def open_registry_connection(base_dir: Path | None = None) -> sqlite3.Connection:
    """Open a connection to the registry DB (migrations applied). Caller must close."""
    db_path = ensure_registry_db(base_dir)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    enable_wal(conn)
    return conn


# --- Project DB: files ---


def insert_file(
    conn: sqlite3.Connection,
    file_path: str,
    *,
    content_hash: str | None = None,
    status: str | None = None,
    group_id: int | None = None,
) -> int:
    """Insert a file row. Returns file id. Replaces on path conflict (upsert).

    On conflict, group_id is only overwritten when a non-NULL value is passed —
    rescans (which pass group_id=None) preserve existing grouping results.
    """
    conn.execute(
        """
        INSERT INTO files (file_path, content_hash, status, group_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(file_path) DO UPDATE SET
            content_hash=excluded.content_hash,
            status=excluded.status,
            group_id=COALESCE(excluded.group_id, files.group_id),
            updated_at=datetime('now')
        """,
        (file_path, content_hash, status, group_id),
    )
    row = conn.execute("SELECT id FROM files WHERE file_path = ?", (file_path,)).fetchone()
    return row[0] if row else 0


# --- Project DB: metrics ---


def insert_metric(
    conn: sqlite3.Connection,
    file_id: int,
    metric_name: str,
    *,
    value_real: float | None = None,
    value_text: str | None = None,
) -> None:
    """Insert or replace a metric row. Idempotent on (file_id, metric_name)."""
    conn.execute(
        """
        INSERT INTO metrics (file_id, metric_name, value_real, value_text)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(file_id, metric_name) DO UPDATE SET
            value_real=excluded.value_real,
            value_text=excluded.value_text
        """,
        (file_id, metric_name, value_real, value_text),
    )


# --- Project DB: groups ---


class GroupingCandidate(NamedTuple):
    """One status=ok file plus its phash, if any. Used by the grouping pass."""

    file_id: int
    file_path: str
    phash: str | None


def insert_group(conn: sqlite3.Connection) -> int:
    """Insert an empty groups row. Returns its id. Does not commit."""
    cursor = conn.execute("INSERT INTO groups DEFAULT VALUES")
    group_id = cursor.lastrowid
    if group_id is None:
        raise RuntimeError("INSERT INTO groups did not return an id")
    return int(group_id)


def set_file_group(conn: sqlite3.Connection, file_id: int, group_id: int | None) -> None:
    """Set files.group_id for one file. Does not commit.

    Pass group_id=None to clear membership. No-op if file_id does not exist.
    """
    conn.execute(
        "UPDATE files SET group_id = ?, updated_at = datetime('now') WHERE id = ?",
        (group_id, file_id),
    )


def list_files_for_grouping(conn: sqlite3.Connection) -> list[GroupingCandidate]:
    """Return status=ok files with their phash metric (NULL if missing).

    Ordered by file id so clustering is deterministic. Does not commit.
    """
    cursor = conn.execute(
        """
        SELECT f.id, f.file_path, m.value_text AS phash
        FROM files AS f
        LEFT JOIN metrics AS m
            ON m.file_id = f.id AND m.metric_name = 'phash'
        WHERE f.status = 'ok'
        ORDER BY f.id
        """
    )
    return [
        GroupingCandidate(
            file_id=int(row["id"]),
            file_path=str(row["file_path"]),
            phash=row["phash"] if row["phash"] is None else str(row["phash"]),
        )
        for row in cursor.fetchall()
    ]


def reset_groups(conn: sqlite3.Connection) -> None:
    """Clear every group_id, then delete groups rows. Does not commit.

    group_id is nulled first so this stays valid if foreign keys are enabled later.
    """
    conn.execute("UPDATE files SET group_id = NULL")
    conn.execute("DELETE FROM groups")


def count_multi_file_groups(conn: sqlite3.Connection) -> int:
    """Count groups that contain more than one file. Does not commit."""
    row = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT group_id
            FROM files
            WHERE group_id IS NOT NULL
            GROUP BY group_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()
    return int(row[0]) if row else 0


# --- Registry DB: projects ---


def add_project(conn: sqlite3.Connection, path: str, name: str | None = None) -> int:
    """Register a project path. Returns project id. path must be absolute."""
    conn.execute(
        "INSERT INTO projects (path, name) VALUES (?, ?) "
        "ON CONFLICT(path) DO UPDATE SET name=excluded.name",
        (path, name),
    )
    row = conn.execute("SELECT id FROM projects WHERE path = ?", (path,)).fetchone()
    return row[0] if row else 0


def list_projects(conn: sqlite3.Connection) -> list[dict[str, object]]:
    """Return all registered projects (id, path, name, added_at)."""
    cursor = conn.execute(
        "SELECT id, path, name, added_at FROM projects ORDER BY added_at"
    )
    return [dict(row) for row in cursor.fetchall()]
