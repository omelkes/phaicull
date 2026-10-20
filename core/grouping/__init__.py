"""Visual grouping. Sprint 1 clusters near-duplicates by pHash Hamming distance."""

from core.grouping.phash_cluster import cluster_by_phash, parse_phash
from core.grouping.service import GroupingResult, regroup

__all__ = ["GroupingResult", "cluster_by_phash", "parse_phash", "regroup"]
