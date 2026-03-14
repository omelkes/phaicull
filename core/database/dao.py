"""Data Access Objects for Phaicull SQLite databases.

All SQL lives in this module (per AGENTS.md). Two databases:
- Project DB: path = project_root / phaicull / phaicull.db (files, metrics, groups).
- Registry DB: path = base_dir / .projects / registry.db (list of projects).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from core.database import schema
from core.database.connection import enable_wal
from core.database.migrate import migrate, migrate_registry


def get_project_db_path(project_root: Path) -> Path:
    """Return the path to the project SQLite DB for the given project root."""
    return Path(project_root).resolve() / schema.PROJECT_PHAICULL_SUBDIR / schema.PROJECT_DB_NAME


def get_registry_db_path(base_dir: Path | None = None) -> Path:
    """Return the path to the registry DB. base_dir defaults to repo/install root (parent of core)."""
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
    """Insert a file row. Returns file id. Replaces on path conflict (upsert)."""
    conn.execute(
        """
        INSERT INTO files (file_path, content_hash, status, group_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(file_path) DO UPDATE SET
            content_hash=excluded.content_hash,
            status=excluded.status,
            group_id=excluded.group_id,
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


# --- Registry DB: projects ---


def add_project(conn: sqlite3.Connection, path: str, name: str | None = None) -> int:
    """Register a project path. Returns project id. path must be absolute."""
    conn.execute(
        "INSERT INTO projects (path, name) VALUES (?, ?) ON CONFLICT(path) DO UPDATE SET name=excluded.name",
        (path, name),
    )
    row = conn.execute("SELECT id FROM projects WHERE path = ?", (path,)).fetchone()
    return row[0] if row else 0


def list_projects(conn: sqlite3.Connection) -> list[dict]:
    """Return all registered projects (id, path, name, added_at)."""
    cursor = conn.execute(
        "SELECT id, path, name, added_at FROM projects ORDER BY added_at"
    )
    return [dict(row) for row in cursor.fetchall()]
