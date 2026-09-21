"""Tests for metric normalization utilities."""

from __future__ import annotations

import math

import pytest

from core.utils.normalization import clamp01, linear_norm, log_norm

# --- clamp01 ---


def test_clamp01_passthrough_in_range() -> None:
    assert clamp01(0.5) == 0.5
    assert clamp01(0.0) == 0.0
    assert clamp01(1.0) == 1.0


def test_clamp01_clamps_out_of_range() -> None:
    assert clamp01(-3.0) == 0.0
    assert clamp01(42.0) == 1.0


def test_clamp01_rejects_non_finite() -> None:
    with pytest.raises(ValueError, match="finite"):
        clamp01(math.nan)
    with pytest.raises(ValueError, match="finite"):
        clamp01(math.inf)


# --- linear_norm ---


def test_linear_norm_midpoint() -> None:
    assert linear_norm(128.0, 0.0, 256.0) == 0.5


def test_linear_norm_boundaries() -> None:
    assert linear_norm(0.0, 0.0, 255.0) == 0.0
    assert linear_norm(255.0, 0.0, 255.0) == 1.0


def test_linear_norm_clamps_outside_range() -> None:
    assert linear_norm(-10.0, 0.0, 255.0) == 0.0
    assert linear_norm(300.0, 0.0, 255.0) == 1.0


def test_linear_norm_non_finite_returns_none() -> None:
    assert linear_norm(math.nan, 0.0, 1.0) is None
    assert linear_norm(math.inf, 0.0, 1.0) is None
    assert linear_norm(-math.inf, 0.0, 1.0) is None


def test_linear_norm_invalid_range_raises() -> None:
    with pytest.raises(ValueError, match="lo < hi"):
        linear_norm(0.5, 1.0, 1.0)
    with pytest.raises(ValueError, match="lo < hi"):
        linear_norm(0.5, 2.0, 1.0)


def test_linear_norm_monotonic() -> None:
    values = [linear_norm(x, 0.0, 100.0) for x in (10.0, 30.0, 50.0, 90.0)]
    assert all(v is not None for v in values)
    assert values == sorted(values)  # type: ignore[type-var]


# --- log_norm ---


def test_log_norm_boundaries() -> None:
    assert log_norm(1.0, 1.0, 10000.0) == 0.0
    assert log_norm(10000.0, 1.0, 10000.0) == 1.0


def test_log_norm_midpoint_on_log_scale() -> None:
    # log10(100) is halfway between log10(1) and log10(10000)
    assert log_norm(100.0, 1.0, 10000.0) == pytest.approx(0.5)


def test_log_norm_clamps_outside_range() -> None:
    assert log_norm(0.5, 1.0, 10000.0) == 0.0
    assert log_norm(99999.0, 1.0, 10000.0) == 1.0


def test_log_norm_zero_and_negative_input_clamp_to_zero() -> None:
    assert log_norm(0.0, 1.0, 100.0) == 0.0
    assert log_norm(-5.0, 1.0, 100.0) == 0.0


def test_log_norm_non_finite_returns_none() -> None:
    assert log_norm(math.nan, 1.0, 100.0) is None
    assert log_norm(math.inf, 1.0, 100.0) is None


def test_log_norm_invalid_range_raises() -> None:
    with pytest.raises(ValueError, match="lo > 0"):
        log_norm(1.0, 0.0, 100.0)
    with pytest.raises(ValueError, match="lo > 0"):
        log_norm(1.0, -1.0, 100.0)
    with pytest.raises(ValueError, match="lo < hi"):
        log_norm(1.0, 100.0, 100.0)


def test_log_norm_monotonic() -> None:
    values = [log_norm(x, 1.0, 10000.0) for x in (2.0, 20.0, 200.0, 2000.0)]
    assert all(v is not None for v in values)
    assert values == sorted(values)  # type: ignore[type-var]
