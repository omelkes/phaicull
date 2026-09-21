"""Metric normalization utilities for Phaicull.

All analyzer metrics are normalized to a comparable 0-1 scale so that
config thresholds (e.g. thresholds.blur_min) and future scoring logic can
treat them uniformly.

Design (per Sprint 1 plan):
- Pure, deterministic, per-image functions — no dataset-relative scaling,
  which would break analyzer idempotency (a photo's score must not depend
  on its neighbors).
- Non-finite measurement values (NaN/inf) return None so analyzers can map
  them to a NULL metric ("missing = NULL, not an error").
- Invalid reference ranges (lo >= hi) raise ValueError — that is a
  programmer error, not a data condition.
"""

from __future__ import annotations

import math


def clamp01(x: float) -> float:
    """Clamp a finite float into [0.0, 1.0].

    Raises:
        ValueError: if x is NaN or infinite (programmer error — measurement
            values should be filtered via linear_norm/log_norm instead).
    """
    if not math.isfinite(x):
        raise ValueError(f"clamp01 requires a finite value, got {x!r}")
    return min(1.0, max(0.0, x))


def linear_norm(x: float, lo: float, hi: float) -> float | None:
    """Linearly map x from [lo, hi] to [0.0, 1.0], clamping outside the range.

    Use for naturally bounded metrics (e.g. mean brightness with lo=0, hi=255).

    Args:
        x: Measured value. NaN/inf returns None.
        lo: Value mapped to 0.0. Values <= lo return 0.0.
        hi: Value mapped to 1.0. Values >= hi return 1.0.

    Returns:
        Normalized score in [0.0, 1.0], or None for non-finite input.

    Raises:
        ValueError: if lo >= hi.
    """
    if lo >= hi:
        raise ValueError(f"linear_norm requires lo < hi, got lo={lo}, hi={hi}")
    if not math.isfinite(x):
        return None
    return clamp01((x - lo) / (hi - lo))


def log_norm(x: float, lo: float, hi: float) -> float | None:
    """Map x from [lo, hi] to [0.0, 1.0] on a log10 scale, clamping outside.

    Use for wide-dynamic-range metrics spanning orders of magnitude
    (e.g. Laplacian variance: ~1 for very blurry to ~10,000 for sharp images),
    where linear scaling would crush the useful resolution into a tiny band.

    Args:
        x: Measured value. NaN/inf returns None. Values <= lo (including
            zero/negative) return 0.0.
        lo: Positive value mapped to 0.0.
        hi: Positive value mapped to 1.0.

    Returns:
        Normalized score in [0.0, 1.0], or None for non-finite input.

    Raises:
        ValueError: if lo <= 0 or lo >= hi.
    """
    if lo <= 0:
        raise ValueError(f"log_norm requires lo > 0, got lo={lo}")
    if lo >= hi:
        raise ValueError(f"log_norm requires lo < hi, got lo={lo}, hi={hi}")
    if not math.isfinite(x):
        return None
    if x <= lo:
        return 0.0
    if x >= hi:
        return 1.0
    return (math.log10(x) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
