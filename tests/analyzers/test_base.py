"""Tests for BaseAnalyzer contract and AnalyzerResult.

Per AGENTS.md: BaseAnalyzer defines the analyzer interface (v2: decoded
image array + source path in, AnalyzerResult | None out).
Concrete analyzers (Blur, Exposure, pHash) require 4-category tests — those are Sprint 1.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from core.analyzers.base import AnalyzerResult, BaseAnalyzer

# --- Abstract class contract ---


def test_base_analyzer_cannot_be_instantiated() -> None:
    """BaseAnalyzer is abstract and cannot be instantiated."""
    with pytest.raises(TypeError, match="abstract"):
        BaseAnalyzer()  # type: ignore[abstract]


def test_subclass_without_implementations_raises() -> None:
    """Subclass that does not implement metric_name and analyze raises."""

    class IncompleteAnalyzer(BaseAnalyzer):
        pass

    with pytest.raises(TypeError, match="abstract"):
        IncompleteAnalyzer()  # type: ignore[abstract]


# --- AnalyzerResult validation ---


def test_analyzer_result_requires_metric_name() -> None:
    """AnalyzerResult requires non-empty metric_name (min_length=1)."""
    with pytest.raises(ValidationError):
        AnalyzerResult(metric_name="")


def test_analyzer_result_numeric_only() -> None:
    """AnalyzerResult with value_real, no value_text."""
    r = AnalyzerResult(metric_name="blur_score", value_real=0.42)
    assert r.metric_name == "blur_score"
    assert r.value_real == 0.42
    assert r.value_text is None


def test_analyzer_result_text_only() -> None:
    """AnalyzerResult with value_text, no value_real."""
    r = AnalyzerResult(metric_name="phash", value_text="abc123")
    assert r.metric_name == "phash"
    assert r.value_real is None
    assert r.value_text == "abc123"


def test_analyzer_result_both_values() -> None:
    """AnalyzerResult can have both value_real and value_text."""
    r = AnalyzerResult(
        metric_name="combined",
        value_real=0.5,
        value_text="hash",
    )
    assert r.metric_name == "combined"
    assert r.value_real == 0.5
    assert r.value_text == "hash"


# --- Minimal concrete implementation and contract ---


class StubAnalyzer(BaseAnalyzer):
    """Minimal concrete analyzer for contract tests.

    Returns mean pixel value so idempotency can be verified against real data.
    """

    @property
    def metric_name(self) -> str:
        return "stub_score"

    def analyze(self, image: np.ndarray, path: Path) -> AnalyzerResult | None:
        if image.size == 0:
            return None
        return AnalyzerResult(
            metric_name=self.metric_name,
            value_real=float(image.mean()),
            value_text=None,
        )


def _make_image(width: int = 16, height: int = 16, value: int = 128) -> np.ndarray:
    return np.full((height, width, 3), value, dtype=np.uint8)


def test_stub_analyzer_implements_contract(tmp_path: Path) -> None:
    """Concrete analyzer returns AnalyzerResult for valid decoded image."""
    analyzer = StubAnalyzer()
    result = analyzer.analyze(_make_image(), tmp_path / "img.jpg")
    assert result is not None
    assert isinstance(result, AnalyzerResult)
    assert result.metric_name == "stub_score"
    assert result.value_real == 128.0


def test_stub_analyzer_returns_none_for_empty_image(tmp_path: Path) -> None:
    """Concrete analyzer returns None for degenerate input — no crash."""
    analyzer = StubAnalyzer()
    empty = np.zeros((0, 0, 3), dtype=np.uint8)
    result = analyzer.analyze(empty, tmp_path / "img.jpg")
    assert result is None


def test_stub_analyzer_handles_1x1_image(tmp_path: Path) -> None:
    """Edge case: 1x1 pixel image is valid input."""
    analyzer = StubAnalyzer()
    result = analyzer.analyze(_make_image(1, 1, value=200), tmp_path / "tiny.png")
    assert result is not None
    assert result.value_real == 200.0


def test_stub_analyzer_handles_extreme_aspect_ratio(tmp_path: Path) -> None:
    """Edge case: extreme aspect ratio image is valid input."""
    analyzer = StubAnalyzer()
    result = analyzer.analyze(_make_image(1000, 1), tmp_path / "wide.png")
    assert result is not None
    assert result.metric_name == "stub_score"


def test_stub_analyzer_idempotent(tmp_path: Path) -> None:
    """Same image yields same result (idempotent)."""
    analyzer = StubAnalyzer()
    image = _make_image(value=77)
    path = tmp_path / "img.jpg"
    r1 = analyzer.analyze(image, path)
    r2 = analyzer.analyze(image, path)
    assert r1 is not None and r2 is not None
    assert r1.metric_name == r2.metric_name
    assert r1.value_real == r2.value_real
