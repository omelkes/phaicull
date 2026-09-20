"""Base analyzer contract for Phaicull.

Per AGENTS.md:
- Each analyzer inherits from BaseAnalyzer, is idempotent, and handles exactly one metric.
- Pass Path objects between processes (never raw bytes). Within the Brawn worker
  process, the image is decoded once and the resulting array is shared with all
  analyzers (contract v2 — see TODO.md decision note).
- Missing metrics = NULL (return None), not an error — never crash the scan.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
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

    Contract (v2):
    - One analyzer = one metric. The metric name is stable and identifies the analyzer.
    - Input: decoded BGR image array (uint8, HxWx3, OpenCV convention) plus the
      source Path for context/logging. The image is decoded exactly once per file
      by the Brawn worker and shared across analyzers — analyzers must NOT
      re-decode from disk.
    - Output: AnalyzerResult | None. None means skip/failed — log but do not raise.
    - Idempotent: re-running on the same image yields the same result.
    - Runs in Brawn (multiprocessing); no DB access or heavy I/O orchestration here.
    - Analyzers must not mutate the input array (it is shared across analyzers).

    Implementations must define:
    - metric_name: str — the stable metric identifier (DB column, JSON key).
    - analyze(image, path) -> AnalyzerResult | None — compute the metric for one image.
    """

    @property
    @abstractmethod
    def metric_name(self) -> str:
        """The stable name of this metric. Used in DB and JSON output."""
        ...

    @abstractmethod
    def analyze(self, image: np.ndarray, path: Path) -> AnalyzerResult | None:
        """Compute this analyzer's metric for the given decoded image.

        Args:
            image: Decoded BGR image array (uint8, HxWx3). Already safety-checked,
                EXIF-oriented, and shared across all analyzers — do not mutate.
            path: Source file path, for logging and context only. Analyzers must
                not re-read image data from disk.

        Returns:
            AnalyzerResult with metric_name, value_real, value_text on success.
            None on skip/failure — caller should log and continue (never crash).
        """
        ...
