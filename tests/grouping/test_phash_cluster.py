"""Pure pHash Hamming clustering. No database."""

from __future__ import annotations

from typing import NamedTuple

from core.grouping.phash_cluster import cluster_by_phash, hamming_distance, parse_phash


class _File(NamedTuple):
    file_id: int
    file_path: str
    phash: str | None


def _hex(mask: int) -> str:
    return f"{mask:016x}"


def test_identical_hashes_form_one_group() -> None:
    files = [
        _File(1, "a.jpg", _hex(0)),
        _File(2, "b.jpg", _hex(0)),
    ]
    assert cluster_by_phash(files, hamming_max=6) == [frozenset({1, 2})]


def test_distance_6_groups_and_7_does_not() -> None:
    near = [
        _File(1, "a.jpg", _hex(0)),
        _File(2, "b.jpg", _hex((1 << 6) - 1)),
    ]
    far = [
        _File(1, "a.jpg", _hex(0)),
        _File(2, "b.jpg", _hex((1 << 7) - 1)),
    ]
    assert hamming_distance(0, (1 << 6) - 1) == 6
    assert hamming_distance(0, (1 << 7) - 1) == 7
    assert cluster_by_phash(near, hamming_max=6) == [frozenset({1, 2})]
    assert cluster_by_phash(far, hamming_max=6) == []


def test_missing_and_invalid_hashes_are_ignored() -> None:
    files = [
        _File(1, "a.jpg", _hex(0)),
        _File(2, "b.jpg", _hex(0)),
        _File(3, "c.jpg", None),
        _File(4, "d.jpg", ""),
        _File(5, "e.jpg", "not-hex-at-all!!"),
        _File(6, "f.jpg", "abc"),
        _File(7, "g.jpg", "0123456789abcde"),
        _File(8, "h.jpg", "0123456789abcdef0"),
    ]
    assert parse_phash(None) is None
    assert parse_phash("zzzzzzzzzzzzzzzz") is None
    assert cluster_by_phash(files, hamming_max=6) == [frozenset({1, 2})]


def test_empty_and_singleton_produce_no_groups() -> None:
    assert cluster_by_phash([], hamming_max=6) == []
    solo = [_File(1, "only.jpg", _hex(0))]
    assert cluster_by_phash(solo, hamming_max=6) == []


def test_transitive_chain_is_one_group() -> None:
    """A≈B and B≈C join A even when A and C are farther than the threshold."""
    hash_a = 0
    hash_b = (1 << 6) - 1  # bits 0..5
    hash_c = hash_b ^ (((1 << 6) - 1) << 4)  # flip bits 4..9; A xor C is 8 bits
    assert hamming_distance(hash_a, hash_b) == 6
    assert hamming_distance(hash_b, hash_c) == 6
    assert hamming_distance(hash_a, hash_c) == 8

    unrelated = 0xFFFFFFFFFFFFFFFF
    files = [
        _File(1, "a.jpg", _hex(hash_a)),
        _File(2, "b.jpg", _hex(hash_b)),
        _File(3, "c.jpg", _hex(hash_c)),
        _File(4, "other.jpg", _hex(unrelated)),
    ]
    assert cluster_by_phash(files, hamming_max=6) == [frozenset({1, 2, 3})]


def test_membership_is_independent_of_input_order() -> None:
    pair_low = [
        _File(10, "z.jpg", _hex(0xFFFF)),
        _File(11, "y.jpg", _hex(0xFFFF)),
    ]
    pair_high = [
        _File(1, "b.jpg", _hex(0)),
        _File(2, "a.jpg", _hex(0)),
    ]
    forward = pair_high + pair_low
    backward = list(reversed(forward))
    expected = [frozenset({1, 2}), frozenset({10, 11})]
    assert cluster_by_phash(forward, hamming_max=6) == expected
    assert cluster_by_phash(backward, hamming_max=6) == expected
