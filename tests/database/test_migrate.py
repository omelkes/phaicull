"""Tests for schema migration runner."""

import sqlite3
from pathlib import Path

import pytest

from core.database.migrate import get_applied_migrations, get_schema_version, migrate


def test_migrate_creates_db_and_schema_version(tmp_path: Path) -> None:
    """Fresh DB: migrate creates file, schema_version table, and seeds v1."""
    db_path = tmp_path / "test.db"
    assert not db_path.exists()

    version = migrate(db_path)

    assert db_path.exists()
    assert version == "001"


def test_migrate_idempotent(tmp_path: Path) -> None:
    """Running migrate twice on same DB does not fail and returns same version."""
    db_path = tmp_path / "test.db"
    v1 = migrate(db_path)
    v2 = migrate(db_path)

    assert v1 == v2 == "001"


def test_get_schema_version_returns_none_for_missing_db(tmp_path: Path) -> None:
    """get_schema_version returns None when DB file does not exist."""
    db_path = tmp_path / "nonexistent.db"
    assert get_schema_version(db_path) is None


def test_get_schema_version_returns_version_after_migrate(tmp_path: Path) -> None:
    """get_schema_version returns current version after migrate."""
    db_path = tmp_path / "test.db"
    migrate(db_path)
    assert get_schema_version(db_path) == "001"


def test_schema_version_table_has_correct_structure(tmp_path: Path) -> None:
    """schema_version table has version, description, applied_at and one row."""
    db_path = tmp_path / "test.db"
    migrate(db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("PRAGMA table_info(schema_version)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    cursor = conn.execute("SELECT version, description, applied_at FROM schema_version")
    rows = cursor.fetchall()
    conn.close()

    assert "version" in columns
    assert "description" in columns
    assert "applied_at" in columns
    assert len(rows) == 1
    assert rows[0][0] == "001"
    assert rows[0][1] == "Initial schema_version table with version, description, applied_at"
    assert rows[0][2]  # applied_at is non-empty


def test_wal_mode_enabled(tmp_path: Path) -> None:
    """WAL journal mode is enabled after migrate."""
    db_path = tmp_path / "test.db"
    migrate(db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("PRAGMA journal_mode")
    mode = cursor.fetchone()[0].upper()
    conn.close()

    assert mode == "WAL"


def test_get_applied_migrations_returns_history(tmp_path: Path) -> None:
    """get_applied_migrations returns list of all applied migrations."""
    db_path = tmp_path / "test.db"
    migrate(db_path)

    applied = get_applied_migrations(db_path)

    assert len(applied) == 1
    assert applied[0]["version"] == "001"
    assert applied[0]["description"] == "Initial schema_version table with version, description, applied_at"
    assert applied[0]["applied_at"]


def test_get_applied_migrations_returns_empty_for_missing_db(tmp_path: Path) -> None:
    """get_applied_migrations returns empty list when DB does not exist."""
    db_path = tmp_path / "nonexistent.db"
    assert get_applied_migrations(db_path) == []


def test_upgrade_from_old_schema(tmp_path: Path) -> None:
    """DB with old schema_version (version only) is upgraded to new schema."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE schema_version (version TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO schema_version (version) VALUES ('001')")
    conn.commit()
    conn.close()

    # get_schema_version triggers upgrade
    assert get_schema_version(db_path) == "001"

    applied = get_applied_migrations(db_path)
    assert len(applied) == 1
    assert applied[0]["version"] == "001"
    assert applied[0]["description"] == "001_initial.sql"  # default when no custom desc
    assert applied[0]["applied_at"]
