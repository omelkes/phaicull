from __future__ import annotations

from pathlib import Path

from core.analyzers import AnalyzerResult, BaseAnalyzer


class BlurAnalyzer(BaseAnalyzer):
    """Sprint 1 blur metric analyzer stub.

    Computes a scalar blur score in later implementation. For now, only
    declares the stable metric name for wiring and contracts.
    """

    @property
    def metric_name(self) -> str:
        return "blur_score"

    def analyze(self, path: Path) -> AnalyzerResult | None:
        """Placeholder implementation for Sprint 1 wiring.

        The compute logic will be added under the Core Analyzers phase.
        """
        raise NotImplementedError("BlurAnalyzer.analyze will be implemented in Sprint 1 Core Analyzers.")

