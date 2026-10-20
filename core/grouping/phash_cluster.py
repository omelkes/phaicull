"""Pure pHash clustering by Hamming distance.

No database and no timestamps. Invalid hashes form no edges and never raise.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

_PHASH_HEX_LEN = 16


class PhashRecord(Protocol):
    """Minimum fields the clusterer reads. GroupingCandidate satisfies this."""

    @property
    def file_id(self) -> int: ...

    @property
    def file_path(self) -> str: ...

    @property
    def phash(self) -> str | None: ...


def parse_phash(value: str | None) -> int | None:
    """Parse a 16-char hex pHash into an int. Anything else is missing."""
    if value is None:
        return None
    text = value.strip()
    if len(text) != _PHASH_HEX_LEN:
        return None
    try:
        return int(text, 16)
    except ValueError:
        return None


def hamming_distance(left: int, right: int) -> int:
    """Bit differences between two parsed hashes."""
    return (left ^ right).bit_count()


def cluster_by_phash(
    records: Sequence[PhashRecord],
    *,
    hamming_max: int,
) -> list[frozenset[int]]:
    """Return clusters of file ids whose hashes differ by at most hamming_max.

    Singletons are omitted. Missing or invalid hashes are omitted.
    Records are sorted by file id, then path, before union so membership
    does not depend on input order. Clusters are ordered by smallest file id.
    """
    valid: list[tuple[int, str, int]] = []
    for record in records:
        parsed = parse_phash(record.phash)
        if parsed is None:
            continue
        valid.append((record.file_id, record.file_path, parsed))
    valid.sort(key=lambda item: (item[0], item[1]))

    parent: dict[int, int] = {file_id: file_id for file_id, _, _ in valid}

    def find(node: int) -> int:
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != root:
            parent[node], node = root, parent[node]
        return root

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left == root_right:
            return
        if root_left < root_right:
            parent[root_right] = root_left
        else:
            parent[root_left] = root_right

    for i, (id_i, _, hash_i) in enumerate(valid):
        for id_j, _, hash_j in valid[i + 1 :]:
            if hamming_distance(hash_i, hash_j) <= hamming_max:
                union(id_i, id_j)

    members: dict[int, set[int]] = {}
    for file_id, _, _ in valid:
        root = find(file_id)
        members.setdefault(root, set()).add(file_id)

    groups = [frozenset(ids) for ids in members.values() if len(ids) >= 2]
    groups.sort(key=min)
    return groups
