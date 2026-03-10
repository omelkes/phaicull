"""Schema migration runner for Phaicull SQLite databases.

Per DEC-004: custom lightweight migration strategy. Migrations live as
sequential SQL files in core/database/migrations/. This module applies
them and updates the schema_version table.

The schema_version table has exactly three columns (no upgrades of legacy schemas):
- version: migration id (e.g. "001")
- description: from migration file (-- migration: ...) or filename
- applied_at: when the migration was applied

If the database has a different schema (e.g. missing columns), the application
fails with PhaicullDatabaseError — the database is treated as corrupted or not Phaicull.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from core.database.connection import enable_wal

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
REGISTRY_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations_registry"

# Required columns for schema_version. No upgrade path; wrong schema → fail.
SCHEMA_VERSION_COLUMNS = frozenset({"version", "description", "applied_at"})

# First line matching this pattern provides the migration description.
DESCRIPTION_PATTERN = re.compile(r"^\s*--\s*(?:migration|description):\s*(.+)$", re.IGNORECASE)


class PhaicullDatabaseError(RuntimeError):
    """Raised when the database is not a valid Phaicull DB (wrong or corrupted schema)."""


def _get_schema_version_columns(conn: sqlite3.Connection) -> list[str]:
    """Return list of column names in schema_version table. Empty if table doesn't exist."""
    try:
        cursor = conn.execute("PRAGMA table_info(schema_version)")
        return [row[1] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []


def _validate_schema_version_table(conn: sqlite3.Connection) -> None:
    """Ensure schema_version table has exactly version, description, applied_at.
    Raises PhaicullDatabaseError if the table exists but has a different schema.
    """
    cols = _get_schema_version_columns(conn)
    if not cols:
        return
    if set(cols) != SCHEMA_VERSION_COLUMNS:
        raise PhaicullDatabaseError(
            "Database is corrupted or not a Phaicull database. "
            "schema_version table has unexpected columns."
        )


def _get_current_version(conn: sqlite3.Connection) -> str | None:
    """Return the current schema version, or None if schema_version table doesn't exist."""
    try:
        cursor = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None


def _execute_migration_sql(conn: sqlite3.Connection, sql: str) -> None:
    """Execute migration SQL as individual statements within the current transaction.

    Unlike executescript(), this does NOT issue an implicit COMMIT, so schema changes
    and the subsequent schema_version INSERT stay in the same transaction.
    Strips line comments (-- to EOL) before splitting to avoid semicolons in comments.
    """
    # Remove line comments so semicolons inside (e.g. "Nullable; partial scans") don't split.
    sql_no_comments = re.sub(r"--[^\n]*", "", sql)
    for stmt in sql_no_comments.split(";"):
        stmt = stmt.strip()
        if not stmt:
            continue
        conn.execute(stmt)


def _parse_description(path: Path) -> str:
    """Extract description from migration file. First line with '-- migration: ...' or '-- description: ...'.
    Otherwise returns the filename."""
    text = path.read_text()
    for line in text.splitlines():
        m = DESCRIPTION_PATTERN.match(line)
        if m:
            return m.group(1).strip()
    return path.name


def _list_migrations(migrations_dir: Path) -> list[tuple[str, Path]]:
    """Return sorted list of (version, path) for migration files in migrations_dir.
    Version is extracted from filename prefix, e.g. 001_initial.sql -> 001.
    """
    if not migrations_dir.exists():
        return []
    migrations: list[tuple[str, Path]] = []
    for p in migrations_dir.glob("*.sql"):
        prefix = p.stem.split("_")[0]
        if prefix.isdigit():
            migrations.append((prefix, p))
    migrations.sort(key=lambda x: x[0])
    return migrations


def _run_migrations(db_path: Path, migrations_dir: Path) -> str:
    """Apply pending migrations from migrations_dir to db_path. Internal helper."""
    db_path = Path(db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        enable_wal(conn)
        _validate_schema_version_table(conn)
        current = _get_current_version(conn)
        migrations = _list_migrations(migrations_dir)

        for version, path in migrations:
            if current is not None and version <= current:
                continue
            description = _parse_description(path)
            logger.info("Applying migration {} ({}) from {}", version, description, path.name)
            sql = path.read_text()
            _execute_migration_sql(conn, sql)
            conn.execute(
                "INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)",
                (version, description, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            current = version

        if current is None:
            raise RuntimeError(
                "No migrations applied and schema_version is empty. "
                "Ensure 001_initial.sql exists and creates schema_version."
            )
        return current
    finally:
        conn.close()


def migrate(db_path: Path) -> str:
    """Apply pending migrations to the project database at db_path.

    Use for per-project DB at {project}/phaicull/phaicull.db. Creates the file
    if it doesn't exist. Enables WAL mode. Runs migrations from migrations/.

    Returns:
        The current schema version after migration (e.g. "002").
    """
    return _run_migrations(db_path, MIGRATIONS_DIR)


def migrate_registry(db_path: Path) -> str:
    """Apply pending migrations to the registry database at db_path.

    Use for the single registry DB in the Phaicull install dir (e.g.
    .projects/registry.db) that holds the list of projects. Creates the file
    if it doesn't exist. Enables WAL mode. Runs migrations from
    migrations_registry/.

    Returns:
        The current schema version after migration (e.g. "001").
    """
    return _run_migrations(db_path, REGISTRY_MIGRATIONS_DIR)


def get_schema_version(db_path: Path) -> str | None:
    """Return the current schema version without running migrations.
    Returns None if the database doesn't exist or schema_version table is missing.
    Raises PhaicullDatabaseError if schema_version exists but has wrong columns.
    """
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    try:
        _validate_schema_version_table(conn)
        return _get_current_version(conn)
    finally:
        conn.close()


def get_applied_migrations(db_path: Path) -> list[dict[str, str]]:
    """Return list of all applied migrations (version, description, applied_at).
    Returns empty list if DB doesn't exist or schema_version table is missing.
    Raises PhaicullDatabaseError if schema_version exists but has wrong columns.
    """
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        _validate_schema_version_table(conn)
        if not _get_schema_version_columns(conn):
            return []
        cursor = conn.execute(
            "SELECT version, description, applied_at FROM schema_version ORDER BY version"
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
