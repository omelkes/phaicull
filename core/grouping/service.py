"""Grouping pass: reconcile stored groups with pHash near-duplicate clusters.

Runs on the Brain after metrics are committed. Reads only the project DB.
"""

from __future__ import annotations

import sqlite3
import time

from loguru import logger
from pydantic import BaseModel, Field

from core.database.dao import (
    insert_group,
    list_files_for_grouping,
    list_group_memberships,
    reset_groups,
    set_file_group,
)
from core.grouping.phash_cluster import cluster_by_phash, parse_phash

_HASH_BITS = 64


class GroupingResult(BaseModel):
    """Outcome of one grouping pass."""

    candidates: int = Field(default=0, description="status=ok files considered.")
    invalid_phash: int = Field(
        default=0, description="Candidates with a missing or invalid phash (no edges)."
    )
    duplicate_groups: int = Field(default=0, description="Groups with two or more files.")
    grouped_files: int = Field(default=0, description="Files that belong to a group.")
    changed: bool = Field(
        default=False, description="False when stored membership already matched; nothing written."
    )


def _stored_membership(memberships: dict[int, int]) -> set[frozenset[int]]:
    by_group: dict[int, set[int]] = {}
    for file_id, group_id in memberships.items():
        by_group.setdefault(group_id, set()).add(file_id)
    return {frozenset(ids) for ids in by_group.values()}


def regroup(conn: sqlite3.Connection, *, hamming_max: int) -> GroupingResult:
    """Cluster status=ok files by pHash and make files.group_id match.

    Writes nothing when the stored membership already equals the computed one,
    so group ids stay stable across unchanged rescans. Otherwise wipes and
    rewrites all groups in one transaction: commits on success, rolls back and
    re-raises on error.
    """
    if not 0 <= hamming_max <= _HASH_BITS:
        raise ValueError(f"hamming_max must be 0..{_HASH_BITS}, got {hamming_max}")
    if conn.in_transaction:
        raise RuntimeError("regroup needs a connection with no open transaction; commit first")

    started = time.perf_counter()
    try:
        candidates = list_files_for_grouping(conn)
        clusters = cluster_by_phash(candidates, hamming_max=hamming_max)
        stored = _stored_membership(list_group_memberships(conn))
        result = GroupingResult(
            candidates=len(candidates),
            invalid_phash=sum(1 for c in candidates if parse_phash(c.phash) is None),
            duplicate_groups=len(clusters),
            grouped_files=sum(len(cluster) for cluster in clusters),
            changed=set(clusters) != stored,
        )
        if result.changed:
            reset_groups(conn)
            for cluster in clusters:
                group_id = insert_group(conn)
                for file_id in sorted(cluster):
                    set_file_group(conn, file_id, group_id)
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    logger.info(
        "Grouping: {} candidates, {} near-duplicate groups ({} files), "
        "{} without valid phash, changed={}, {:.3f}s",
        result.candidates,
        result.duplicate_groups,
        result.grouped_files,
        result.invalid_phash,
        result.changed,
        time.perf_counter() - started,
    )
    return result
