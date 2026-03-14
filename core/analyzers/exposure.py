from __future__ import annotations

from pathlib import Path

from core.analyzers import AnalyzerResult, BaseAnalyzer


class ExposureAnalyzer(BaseAnalyzer):
    """Sprint 1 exposure/brightness metric analyzer stub.

    Computes a normalized brightness_score in later implementation based on
    mean brightness and RMS contrast.
    """

    @property
    def metric_name(self) -> str:
        return "brightness_score"

    def analyze(self, path: Path) -> AnalyzerResult | None:
        """Placeholder implementation for Sprint 1 wiring."""
        raise NotImplementedError(
            "ExposureAnalyzer.analyze will be implemented in Sprint 1 Core Analyzers."
        )

