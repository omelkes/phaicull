"""RMS contrast via grayscale standard deviation.

RMS contrast is the root-mean-square of deviations from the mean intensity —
identical to the pixel standard deviation. A flat image has score 0.0; a
50/50 black-and-white image reaches the theoretical uint8 maximum (127.5)
and maps to 1.0.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.analyzers import AnalyzerResult, BaseAnalyzer
from core.utils.normalization import linear_norm

# Theoretical maximum std of uint8 values: half the pixels 0, half 255.
_STD_HI = 127.5


class ContrastAnalyzer(BaseAnalyzer):
    """Computes contrast_score in [0, 1]: 0 = flat, 1 = max RMS contrast."""

    @property
    def metric_name(self) -> str:
        return "contrast_score"

    def analyze(self, image: np.ndarray, path: Path) -> AnalyzerResult | None:
        if image.size == 0:
            return None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        rms = float(gray.std())
        score = linear_norm(rms, 0.0, _STD_HI)
        if score is None:
            return None
        return AnalyzerResult(metric_name=self.metric_name, value_real=score, value_text=None)
