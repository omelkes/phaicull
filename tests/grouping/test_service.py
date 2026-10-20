"""Grouping service: reconcile stored groups with pHash clusters."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from core.database.dao import (
    insert_file,
    insert_group,
    insert_metric,
    list_group_memberships,
    open_project_connection,
    set_file_group,
)
from core.grouping import service
from core.grouping.service import regroup

SAME = "0000000000000000"
OTHER = "ffffffffffffffff"


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = open_project_connection(tmp_path / "photos")
    try:
        yield connection
    finally:
        connection.close()


def _add(
    conn: sqlite3.Connection, name: str, phash: str | None, status: str = "ok"
) -> int:
    file_id = insert_file(conn, f"/photos/{name}", status=status)
    if phash is not None:
        insert_metric(conn, file_id, "phash", value_text=phash)
    conn.commit()
    return file_id


def _groups_by_path(conn: sqlite3.Connection) -> set[frozenset[str]]:
    rows = conn.execute(
        "SELECT file_path, group_id FROM files WHERE group_id IS NOT NULL"
    ).fetchall()
    by_group: dict[int, set[str]] = {}
    for row in rows:
        by_group.setdefault(row["group_id"], set()).add(row["file_path"])
    return {frozenset(paths) for paths in by_group.values()}


def _group_rows(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM groups").fetchone()
    return int(row[0])


def test_identical_pair_grouped_and_unrelated_stays_null(conn: sqlite3.Connection) -> None:
    _add(conn, "a.jpg", SAME)
    _add(conn, "b.jpg", SAME)
    other = _add(conn, "c.jpg", OTHER)

    result = regroup(conn, hamming_max=6)

    assert result.changed
    assert result.candidates == 3
    assert result.duplicate_groups == 1
    assert result.grouped_files == 2
    assert _groups_by_path(conn) == {frozenset({"/photos/a.jpg", "/photos/b.jpg"})}
    assert other not in list_group_memberships(conn)
    assert _group_rows(conn) == 1


def test_unchanged_rescan_keeps_ids_and_writes_nothing(conn: sqlite3.Connection) -> None:
    _add(conn, "a.jpg", SAME)
    _add(conn, "b.jpg", SAME)
    regroup(conn, hamming_max=6)
    before = list_group_memberships(conn)

    result = regroup(conn, hamming_max=6)

    assert not result.changed
    assert result.duplicate_groups == 1
    assert list_group_memberships(conn) == before


def test_membership_change_rewrites(conn: sqlite3.Connection) -> None:
    _add(conn, "a.jpg", SAME)
    _add(conn, "b.jpg", SAME)
    regroup(conn, hamming_max=6)

    _add(conn, "c.jpg", SAME)
    result = regroup(conn, hamming_max=6)

    assert result.changed
    assert _groups_by_path(conn) == {
        frozenset({"/photos/a.jpg", "/photos/b.jpg", "/photos/c.jpg"})
    }
    assert _group_rows(conn) == 1


def test_stale_group_on_load_failed_file_is_cleared(conn: sqlite3.Connection) -> None:
    """insert_file keeps group_id on rescan; grouping must clear it once a file fails."""
    a = _add(conn, "a.jpg", SAME)
    b = _add(conn, "b.jpg", SAME)
    regroup(conn, hamming_max=6)

    insert_file(conn, "/photos/b.jpg", status="load_failed")
    conn.commit()
    assert b in list_group_memberships(conn)

    result = regroup(conn, hamming_max=6)

    assert result.changed
    assert result.duplicate_groups == 0
    memberships = list_group_memberships(conn)
    assert a not in memberships
    assert b not in memberships
    assert _group_rows(conn) == 0


def test_stale_singleton_cleared_when_no_valid_pairs(conn: sqlite3.Connection) -> None:
    only = _add(conn, "only.jpg", SAME)
    group_id = insert_group(conn)
    set_file_group(conn, only, group_id)
    conn.commit()

    result = regroup(conn, hamming_max=6)

    assert result.changed
    assert list_group_memberships(conn) == {}
    assert _group_rows(conn) == 0


def test_missing_and_invalid_phash_ignored_and_counted(conn: sqlite3.Connection) -> None:
    _add(conn, "a.jpg", SAME)
    _add(conn, "b.jpg", SAME)
    no_hash = _add(conn, "nohash.jpg", None)
    bad_hash = _add(conn, "bad.jpg", "zzzz")

    result = regroup(conn, hamming_max=6)

    assert result.candidates == 4
    assert result.invalid_phash == 2
    memberships = list_group_memberships(conn)
    assert no_hash not in memberships
    assert bad_hash not in memberships


def test_non_ok_files_are_not_grouped(conn: sqlite3.Connection) -> None:
    _add(conn, "a.jpg", SAME)
    failed = _add(conn, "failed.jpg", SAME, status="load_failed")

    result = regroup(conn, hamming_max=6)

    assert result.candidates == 1
    assert result.duplicate_groups == 0
    assert failed not in list_group_memberships(conn)


def test_empty_project_is_a_no_op(conn: sqlite3.Connection) -> None:
    result = regroup(conn, hamming_max=6)

    assert not result.changed
    assert result.candidates == 0
    assert result.duplicate_groups == 0


def test_error_mid_write_rolls_back(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add(conn, "a.jpg", SAME)
    _add(conn, "b.jpg", SAME)
    regroup(conn, hamming_max=6)
    before = list_group_memberships(conn)
    _add(conn, "c.jpg", SAME)

    def fail(*_args: object) -> None:
        raise sqlite3.OperationalError("disk full")

    monkeypatch.setattr(service, "set_file_group", fail)
    with pytest.raises(sqlite3.OperationalError):
        regroup(conn, hamming_max=6)

    assert not conn.in_transaction
    assert list_group_memberships(conn) == before
    assert _group_rows(conn) == 1


def test_open_transaction_on_entry_raises(conn: sqlite3.Connection) -> None:
    insert_file(conn, "/photos/pending.jpg", status="ok")
    assert conn.in_transaction

    with pytest.raises(RuntimeError, match="no open transaction"):
        regroup(conn, hamming_max=6)

    conn.rollback()


@pytest.mark.parametrize("bad", [-1, 65])
def test_hamming_max_out_of_range_raises(conn: sqlite3.Connection, bad: int) -> None:
    with pytest.raises(ValueError, match="hamming_max"):
        regroup(conn, hamming_max=bad)
