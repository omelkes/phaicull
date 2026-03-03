"""Schema migration runner for Phaicull SQLite databases.

Per DEC-004: custom lightweight migration strategy. Migrations live as
sequential SQL files in core/database/migrations/. This module applies
them and updates the schema_version table.

The schema_version table stores a history of all applied migrations:
- version: migration id (e.g. "001")
- description: from migration file (-- migration: ...) or filename
- applied_at: when the migration was applied
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
WAL_PRAGMA = "PRAGMA journal_mode=WAL;"

# First line matching this pattern provides the migration description.
DESCRIPTION_PATTERN = re.compile(r"^\s*--\s*(?:migration|description):\s*(.+)$", re.IGNORECASE)


def _enable_wal(conn: sqlite3.Connection) -> None:
    """Enable WAL mode on the connection. Required per AGENTS.md."""
    conn.execute(WAL_PRAGMA)


def _get_schema_version_columns(conn: sqlite3.Connection) -> list[str]:
    """Return list of column names in schema_version table. Empty if table doesn't exist."""
    try:
        cursor = conn.execute("PRAGMA table_info(schema_version)")
        return [row[1] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []


def _upgrade_schema_version_table(conn: sqlite3.Connection) -> None:
    """Upgrade old schema_version (version only) to new (version, description, applied_at)."""
    cols = _get_schema_version_columns(conn)
    if not cols:
        return
    if "description" in cols and "applied_at" in cols:
        return
    # Old schema: version only. Add description and applied_at.
    if "description" not in cols:
        conn.execute("ALTER TABLE schema_version ADD COLUMN description TEXT")
    if "applied_at" not in cols:
        conn.execute("ALTER TABLE schema_version ADD COLUMN applied_at TEXT")
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE schema_version SET description = COALESCE(description, '001_initial.sql'), applied_at = COALESCE(applied_at, ?)",
        (now,),
    )
    conn.commit()


def _get_current_version(conn: sqlite3.Connection) -> str | None:
    """Return the current schema version, or None if schema_version table doesn't exist."""
    try:
        cursor = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None


def _parse_description(path: Path) -> str:
    """Extract description from migration file. First line with '-- migration: ...' or '-- description: ...'.
    Otherwise returns the filename."""
    text = path.read_text()
    for line in text.splitlines():
        m = DESCRIPTION_PATTERN.match(line)
        if m:
            return m.group(1).strip()
    return path.name


def _list_migrations() -> list[tuple[str, Path]]:
    """Return sorted list of (version, path) for migration files.
    Version is extracted from filename prefix, e.g. 001_initial.sql -> 001.
    """
    if not MIGRATIONS_DIR.exists():
        return []
    migrations: list[tuple[str, Path]] = []
    for p in MIGRATIONS_DIR.glob("*.sql"):
        prefix = p.stem.split("_")[0]
        if prefix.isdigit():
            migrations.append((prefix, p))
    migrations.sort(key=lambda x: x[0])
    return migrations


def migrate(db_path: Path) -> str:
    """Apply pending migrations to the database at db_path.

    Creates the database file if it doesn't exist. Enables WAL mode.
    Runs migrations in order and appends each to schema_version (history).

    Returns:
        The current schema version after migration (e.g. "001" for v1).
    """
    db_path = Path(db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        _enable_wal(conn)
        _upgrade_schema_version_table(conn)
        current = _get_current_version(conn)
        migrations = _list_migrations()

        for version, path in migrations:
            if current is not None and version <= current:
                continue
            description = _parse_description(path)
            logger.info("Applying migration {} ({}) from {}", version, description, path.name)
            sql = path.read_text()
            conn.executescript(sql)
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


def get_schema_version(db_path: Path) -> str | None:
    """Return the current schema version without running migrations.
    Returns None if the database doesn't exist or schema_version is missing.
    """
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    try:
        _upgrade_schema_version_table(conn)
        return _get_current_version(conn)
    finally:
        conn.close()


def get_applied_migrations(db_path: Path) -> list[dict[str, str]]:
    """Return list of all applied migrations (version, description, applied_at).
    Returns empty list if DB doesn't exist or schema_version is missing.
    """
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        _upgrade_schema_version_table(conn)
        cols = _get_schema_version_columns(conn)
        if not cols:
            return []
        cursor = conn.execute(
            "SELECT version, description, applied_at FROM schema_version ORDER BY version"
        )
        rows = cursor.fetchall()
        result: list[dict[str, str]] = []
        for row in rows:
            d = dict(row)
            # Handle old schema: may have only version
            result.append(
                {
                    "version": str(d.get("version", "")),
                    "description": str(d.get("description", "")),
                    "applied_at": str(d.get("applied_at", "")),
                }
            )
        return result
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
