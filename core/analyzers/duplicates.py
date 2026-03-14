from __future__ import annotations

from pathlib import Path

from core.analyzers import AnalyzerResult, BaseAnalyzer


class DuplicatesAnalyzer(BaseAnalyzer):
    """Sprint 1 perceptual hash (pHash) analyzer stub.

    Computes a perceptual hash used for duplicate detection in later
    implementation.
    """

    @property
    def metric_name(self) -> str:
        return "phash"

    def analyze(self, path: Path) -> AnalyzerResult | None:
        """Placeholder implementation for Sprint 1 wiring."""
        raise NotImplementedError(
            "DuplicatesAnalyzer.analyze will be implemented in Sprint 1 Core Analyzers."
        )

