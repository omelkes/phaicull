"""Exposure analysis via mean brightness.

brightness_score is the mean grayscale value linearly normalized to 0-1:
0.0 = pure black, 1.0 = pure white. Config thresholds interpret it directly
(thresholds.brightness_min flags "too dark", brightness_max "blown out").

RMS contrast is a separate candidate metric (one analyzer = one metric per
AGENTS.md) — tracked as its own TODO item.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.analyzers import AnalyzerResult, BaseAnalyzer
from core.utils.normalization import linear_norm


class ExposureAnalyzer(BaseAnalyzer):
    """Computes brightness_score in [0, 1]: 0 = black, 1 = white."""

    @property
    def metric_name(self) -> str:
        return "brightness_score"

    def analyze(self, image: np.ndarray, path: Path) -> AnalyzerResult | None:
        if image.size == 0:
            return None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(gray.mean())
        score = linear_norm(mean_brightness, 0.0, 255.0)
        if score is None:
            return None
        return AnalyzerResult(metric_name=self.metric_name, value_real=score, value_text=None)
