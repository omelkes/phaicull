"""Tests for schema migration runner."""

import sqlite3
from pathlib import Path

import pytest

from core.database.migrate import (
    PhaicullDatabaseError,
    get_applied_migrations,
    get_schema_version,
    migrate,
    migrate_registry,
)


def test_migrate_creates_db_and_schema_version(tmp_path: Path) -> None:
    """Fresh DB: migrate creates file, schema_version table, and applies all migrations."""
    db_path = tmp_path / "test.db"
    assert not db_path.exists()

    version = migrate(db_path)

    assert db_path.exists()
    assert version == "002"


def test_migrate_idempotent(tmp_path: Path) -> None:
    """Running migrate twice on same DB does not fail and returns same version."""
    db_path = tmp_path / "test.db"
    v1 = migrate(db_path)
    v2 = migrate(db_path)

    assert v1 == v2 == "002"


def test_get_schema_version_returns_none_for_missing_db(tmp_path: Path) -> None:
    """get_schema_version returns None when DB file does not exist."""
    db_path = tmp_path / "nonexistent.db"
    assert get_schema_version(db_path) is None


def test_get_schema_version_returns_version_after_migrate(tmp_path: Path) -> None:
    """get_schema_version returns current version after migrate."""
    db_path = tmp_path / "test.db"
    migrate(db_path)
    assert get_schema_version(db_path) == "002"


def test_schema_version_table_has_correct_structure(tmp_path: Path) -> None:
    """schema_version table has version, description, applied_at and migration history."""
    db_path = tmp_path / "test.db"
    migrate(db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("PRAGMA table_info(schema_version)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    cursor = conn.execute("SELECT version, description, applied_at FROM schema_version ORDER BY version")
    rows = cursor.fetchall()
    conn.close()

    assert "version" in columns
    assert "description" in columns
    assert "applied_at" in columns
    assert len(rows) >= 1
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

    assert len(applied) >= 1
    assert applied[0]["version"] == "001"
    assert applied[0]["description"] == "Initial schema_version table with version, description, applied_at"
    assert applied[0]["applied_at"]


def test_get_applied_migrations_returns_empty_for_missing_db(tmp_path: Path) -> None:
    """get_applied_migrations returns empty list when DB does not exist."""
    db_path = tmp_path / "nonexistent.db"
    assert get_applied_migrations(db_path) == []


def test_old_schema_version_fails_get_schema_version(tmp_path: Path) -> None:
    """DB with old schema_version (version only) causes get_schema_version to raise."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE schema_version (version TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO schema_version (version) VALUES ('001')")
    conn.commit()
    conn.close()

    with pytest.raises(PhaicullDatabaseError, match="corrupted or not a Phaicull"):
        get_schema_version(db_path)


def test_old_schema_version_fails_get_applied_migrations(tmp_path: Path) -> None:
    """DB with old schema_version (version only) causes get_applied_migrations to raise."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE schema_version (version TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO schema_version (version) VALUES ('001')")
    conn.commit()
    conn.close()

    with pytest.raises(PhaicullDatabaseError, match="corrupted or not a Phaicull"):
        get_applied_migrations(db_path)


def test_old_schema_version_fails_migrate(tmp_path: Path) -> None:
    """DB with old schema_version (version only) causes migrate to raise."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE schema_version (version TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO schema_version (version) VALUES ('001')")
    conn.commit()
    conn.close()

    with pytest.raises(PhaicullDatabaseError, match="corrupted or not a Phaicull"):
        migrate(db_path)


def test_migrate_creates_project_tables(tmp_path: Path) -> None:
    """Project DB has files, metrics, groups tables after migrate."""
    db_path = tmp_path / "project.db"
    migrate(db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('files','metrics','groups') ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert tables == ["files", "groups", "metrics"]


def test_migrate_registry_creates_db_and_projects(tmp_path: Path) -> None:
    """Registry migrate creates DB and projects table."""
    db_path = tmp_path / "registry.db"
    assert not db_path.exists()

    version = migrate_registry(db_path)

    assert db_path.exists()
    assert version == "001"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
    )
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "projects"


def test_migrate_registry_idempotent(tmp_path: Path) -> None:
    """Running migrate_registry twice returns same version."""
    db_path = tmp_path / "registry.db"
    v1 = migrate_registry(db_path)
    v2 = migrate_registry(db_path)
    assert v1 == v2 == "001"


def test_get_schema_version_uses_numeric_ordering(tmp_path: Path) -> None:
    """get_schema_version returns highest numeric version, not lexicographic max."""
    db_path = tmp_path / "versions.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE schema_version ("
        "version TEXT PRIMARY KEY, "
        "description TEXT NOT NULL, "
        "applied_at TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "INSERT INTO schema_version (version, description, applied_at) "
        "VALUES ('9', 'v9', '2024-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO schema_version (version, description, applied_at) "
        "VALUES ('10', 'v10', '2024-01-02T00:00:00Z')"
    )
    conn.commit()
    conn.close()

    # Lexicographically, "9" > "10", but numerically 9 < 10.
    # We expect the function to honor numeric ordering and return "10".
    assert get_schema_version(db_path) == "10"
