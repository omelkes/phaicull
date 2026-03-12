"""Shared SQLite connection setup for Phaicull databases.

WAL mode and other pragmas are defined here so they stay in sync across
migrations and DAO usage. Per AGENTS.md: SQLite must use WAL mode.
"""

from __future__ import annotations

import sqlite3

WAL_PRAGMA = "PRAGMA journal_mode=WAL;"


def enable_wal(conn: sqlite3.Connection) -> None:
    """Enable WAL mode on the connection. Required per AGENTS.md."""
    conn.execute(WAL_PRAGMA)
