"""Tests for BaseAnalyzer contract and AnalyzerResult.

Per AGENTS.md: BaseAnalyzer defines the analyzer interface.
Concrete analyzers (Blur, Exposure, pHash) require 4-category tests — those are Sprint 1.
"""

from __future__ import annotations

from pathlib import Path

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
        IncompleteAnalyzer()


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
    """Minimal concrete analyzer for contract tests."""

    @property
    def metric_name(self) -> str:
        return "stub_score"

    def analyze(self, path: Path) -> AnalyzerResult | None:
        if not path.exists():
            return None
        # Return result for any existing file (contract test only)
        return AnalyzerResult(
            metric_name=self.metric_name,
            value_real=1.0,
            value_text=None,
        )


def test_stub_analyzer_implements_contract(synthetic_valid_image: Path) -> None:
    """Concrete analyzer returns AnalyzerResult for valid input."""
    analyzer = StubAnalyzer()
    result = analyzer.analyze(synthetic_valid_image)
    assert result is not None
    assert isinstance(result, AnalyzerResult)
    assert result.metric_name == "stub_score"
    assert result.value_real == 1.0


def test_stub_analyzer_returns_none_for_missing_file(tmp_path: Path) -> None:
    """Concrete analyzer returns None for non-existent path — no crash."""
    analyzer = StubAnalyzer()
    missing = tmp_path / "does_not_exist.jpg"
    assert not missing.exists()
    result = analyzer.analyze(missing)
    assert result is None


def test_stub_analyzer_handles_zero_byte_file(zero_byte_file: Path) -> None:
    """Concrete analyzer can return result or None; contract allows either."""
    analyzer = StubAnalyzer()
    result = analyzer.analyze(zero_byte_file)
    # Stub returns result for any existing path; real analyzers may return None for corrupt
    assert result is not None
    assert result.metric_name == "stub_score"


def test_stub_analyzer_handles_non_image_file(non_image_file: Path) -> None:
    """Contract: Path in, AnalyzerResult | None out. Non-image is valid Path input."""
    analyzer = StubAnalyzer()
    result = analyzer.analyze(non_image_file)
    assert result is not None  # Stub treats any existing file as ok
    assert isinstance(result, AnalyzerResult)


def test_stub_analyzer_idempotent(synthetic_valid_image: Path) -> None:
    """Same path yields same result (idempotent)."""
    analyzer = StubAnalyzer()
    r1 = analyzer.analyze(synthetic_valid_image)
    r2 = analyzer.analyze(synthetic_valid_image)
    assert r1 is not None and r2 is not None
    assert r1.metric_name == r2.metric_name
    assert r1.value_real == r2.value_real
