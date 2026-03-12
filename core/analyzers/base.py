"""Base analyzer contract for Phaicull.

Per AGENTS.md:
- Each analyzer inherits from BaseAnalyzer, is idempotent, and handles exactly one metric.
- Pass Path objects between processes (never raw bytes). Load images only when needed.
- Missing metrics = NULL (return None), not an error — never crash the scan.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field


class AnalyzerResult(BaseModel):
    """Output contract for a single analyzer run.

    Maps directly to the metrics table: metric_name, value_real, value_text.
    All values are optional; NULL in DB when omitted.
    """

    metric_name: str = Field(..., min_length=1, description="Name of the metric (e.g. blur_score)")
    value_real: float | None = Field(None, description="Numeric metric value, or None")
    value_text: str | None = Field(None, description="Text metric value (e.g. pHash), or None")


class BaseAnalyzer(ABC):
    """Abstract base for all Phaicull analyzers.

    Contract:
    - One analyzer = one metric. The metric name is stable and identifies the analyzer.
    - Input: Path to image file (never raw bytes; memory-safe for multiprocessing).
    - Output: AnalyzerResult | None. None means skip/failed — log but do not raise.
    - Idempotent: re-running on the same file yields the same result.
    - Runs in Brawn (multiprocessing); no DB access or heavy I/O orchestration here.

    Implementations must define:
    - metric_name: str — the stable metric identifier (DB column, JSON key).
    - analyze(path: Path) -> AnalyzerResult | None — compute the metric for one file.
    """

    @property
    @abstractmethod
    def metric_name(self) -> str:
        """The stable name of this metric. Used in DB and JSON output."""
        ...

    @abstractmethod
    def analyze(self, path: Path) -> AnalyzerResult | None:
        """Compute this analyzer's metric for the given image file.

        Args:
            path: Path to the image file. Must exist and be readable.

        Returns:
            AnalyzerResult with metric_name, value_real, value_text on success.
            None on skip/failure — caller should log and continue (never crash).
        """
        ...
