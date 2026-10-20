"""Tests for database DAO (project and registry)."""

from pathlib import Path

from core.database.dao import (
    add_project,
    count_multi_file_groups,
    ensure_project_db,
    ensure_registry_db,
    get_project_db_path,
    get_registry_db_path,
    insert_file,
    insert_group,
    insert_metric,
    list_files_for_grouping,
    list_group_memberships,
    list_projects,
    open_project_connection,
    open_registry_connection,
    reset_groups,
    set_file_group,
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
        row = conn.execute(
            "SELECT file_path, content_hash, status FROM files WHERE id = ?", (fid,)
        ).fetchone()
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


def test_insert_file_rescan_preserves_group_id(tmp_path: Path) -> None:
    """Upsert with group_id=None (a rescan) must not wipe an existing group_id."""
    project_root = tmp_path / "photos"
    conn = open_project_connection(project_root)
    try:
        conn.execute("INSERT INTO groups DEFAULT VALUES")
        group_id = conn.execute("SELECT id FROM groups").fetchone()[0]

        fid = insert_file(conn, "/photos/burst1.jpg", status="ok", group_id=group_id)
        conn.commit()

        # Rescan: same path, no group information
        fid2 = insert_file(conn, "/photos/burst1.jpg", content_hash="new", status="ok")
        conn.commit()

        assert fid == fid2
        row = conn.execute(
            "SELECT group_id, content_hash FROM files WHERE id = ?", (fid,)
        ).fetchone()
        assert row["group_id"] == group_id  # preserved
        assert row["content_hash"] == "new"  # still updated
    finally:
        conn.close()


def test_insert_file_can_set_new_group_id(tmp_path: Path) -> None:
    """Upsert with a non-NULL group_id still updates it (grouping pass)."""
    project_root = tmp_path / "photos"
    conn = open_project_connection(project_root)
    try:
        conn.execute("INSERT INTO groups DEFAULT VALUES")
        conn.execute("INSERT INTO groups DEFAULT VALUES")
        g1, g2 = [r[0] for r in conn.execute("SELECT id FROM groups ORDER BY id").fetchall()]

        fid = insert_file(conn, "/photos/img.jpg", status="ok", group_id=g1)
        insert_file(conn, "/photos/img.jpg", status="ok", group_id=g2)
        conn.commit()

        row = conn.execute("SELECT group_id FROM files WHERE id = ?", (fid,)).fetchone()
        assert row["group_id"] == g2
    finally:
        conn.close()


def test_insert_file_status_reason_set_and_cleared(tmp_path: Path) -> None:
    """status_reason is stored on failure and reset to NULL when the file loads again."""
    conn = open_project_connection(tmp_path / "photos")
    try:
        fid = insert_file(
            conn, "/photos/a.jpg", status="load_failed", status_reason="decode_failed"
        )
        row = conn.execute("SELECT status_reason FROM files WHERE id = ?", (fid,)).fetchone()
        assert row["status_reason"] == "decode_failed"

        insert_file(conn, "/photos/a.jpg", status="ok")
        row = conn.execute("SELECT status_reason FROM files WHERE id = ?", (fid,)).fetchone()
        assert row["status_reason"] is None
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
            "SELECT metric_name, value_real, value_text FROM metrics "
            "WHERE file_id = ? ORDER BY metric_name",
            (fid,),
        ).fetchall()
        assert len(rows) == 3
        assert tuple(rows[0]) == ("blur_score", 0.15, None)
        assert tuple(rows[1]) == ("brightness_score", 0.82, None)
        assert tuple(rows[2]) == ("phash", None, "deadbeef")
    finally:
        conn.close()


# --- groups ---


def test_insert_group_returns_id(tmp_path: Path) -> None:
    """insert_group creates a groups row and returns its id."""
    conn = open_project_connection(tmp_path / "photos")
    try:
        group_id = insert_group(conn)
        conn.commit()
        row = conn.execute("SELECT id FROM groups WHERE id = ?", (group_id,)).fetchone()
        assert row is not None
        assert row["id"] == group_id
    finally:
        conn.close()


def test_set_file_group_assigns_and_clears(tmp_path: Path) -> None:
    """set_file_group writes group_id and can clear it with None."""
    conn = open_project_connection(tmp_path / "photos")
    try:
        fid = insert_file(conn, "/photos/a.jpg", status="ok")
        group_id = insert_group(conn)
        set_file_group(conn, fid, group_id)
        conn.commit()
        row = conn.execute("SELECT group_id FROM files WHERE id = ?", (fid,)).fetchone()
        assert row["group_id"] == group_id

        set_file_group(conn, fid, None)
        conn.commit()
        row = conn.execute("SELECT group_id FROM files WHERE id = ?", (fid,)).fetchone()
        assert row["group_id"] is None
    finally:
        conn.close()


def test_list_files_for_grouping_ok_only(tmp_path: Path) -> None:
    """Only status=ok files are listed; phash is NULL when the metric is missing."""
    conn = open_project_connection(tmp_path / "photos")
    try:
        ok = insert_file(conn, "/photos/ok.jpg", status="ok")
        missing = insert_file(conn, "/photos/nophash.jpg", status="ok")
        insert_file(conn, "/photos/bad.jpg", status="load_failed")
        insert_file(conn, "/photos/skip.jpg", status="skipped_invalid_mime")
        insert_metric(conn, ok, "phash", value_text="0123456789abcdef")
        conn.commit()

        rows = list_files_for_grouping(conn)
        by_path = {row.file_path: row for row in rows}
        assert set(by_path) == {"/photos/ok.jpg", "/photos/nophash.jpg"}
        assert by_path["/photos/ok.jpg"].file_id == ok
        assert by_path["/photos/ok.jpg"].phash == "0123456789abcdef"
        assert by_path["/photos/nophash.jpg"].file_id == missing
        assert by_path["/photos/nophash.jpg"].phash is None
        assert [row.file_id for row in rows] == sorted(row.file_id for row in rows)
    finally:
        conn.close()


def test_list_group_memberships_includes_any_status(tmp_path: Path) -> None:
    """Memberships cover every grouped file, including non-ok ones; ungrouped are absent."""
    conn = open_project_connection(tmp_path / "photos")
    try:
        ok = insert_file(conn, "/photos/ok.jpg", status="ok")
        failed = insert_file(conn, "/photos/failed.jpg", status="load_failed")
        insert_file(conn, "/photos/loose.jpg", status="ok")
        group_id = insert_group(conn)
        set_file_group(conn, ok, group_id)
        set_file_group(conn, failed, group_id)
        conn.commit()
        assert list_group_memberships(conn) == {ok: group_id, failed: group_id}
    finally:
        conn.close()


def test_reset_groups_nulls_then_deletes(tmp_path: Path) -> None:
    """reset_groups clears file membership and removes groups rows; files stay."""
    conn = open_project_connection(tmp_path / "photos")
    try:
        fid = insert_file(conn, "/photos/a.jpg", status="ok")
        group_id = insert_group(conn)
        set_file_group(conn, fid, group_id)
        conn.commit()

        reset_groups(conn)
        conn.commit()

        file_row = conn.execute("SELECT group_id FROM files WHERE id = ?", (fid,)).fetchone()
        group_count = conn.execute("SELECT COUNT(*) FROM groups").fetchone()
        assert file_row["group_id"] is None
        assert group_count is not None
        assert group_count[0] == 0
    finally:
        conn.close()


def test_count_multi_file_groups(tmp_path: Path) -> None:
    """Only groups with two or more files are counted."""
    conn = open_project_connection(tmp_path / "photos")
    try:
        a = insert_file(conn, "/photos/a.jpg", status="ok")
        b = insert_file(conn, "/photos/b.jpg", status="ok")
        c = insert_file(conn, "/photos/c.jpg", status="ok")
        pair = insert_group(conn)
        solo = insert_group(conn)
        set_file_group(conn, a, pair)
        set_file_group(conn, b, pair)
        set_file_group(conn, c, solo)
        conn.commit()
        assert count_multi_file_groups(conn) == 1
    finally:
        conn.close()


def test_group_dao_does_not_commit(tmp_path: Path) -> None:
    """Group DAO methods leave the transaction to the caller."""
    project_root = tmp_path / "photos"
    conn = open_project_connection(project_root)
    try:
        insert_group(conn)
    finally:
        conn.close()

    conn2 = open_project_connection(project_root)
    try:
        count = conn2.execute("SELECT COUNT(*) FROM groups").fetchone()
        assert count is not None
        assert count[0] == 0
    finally:
        conn2.close()
