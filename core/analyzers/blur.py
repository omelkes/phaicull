"""Blur detection via Laplacian variance.

Sharp images have strong edges, so the Laplacian (second derivative) response
has high variance; blurry images have weak edges and low variance. The image
is downscaled to a fixed working size first so the metric is comparable
across resolutions, then the variance is log-normalized to 0-1 (it spans
several orders of magnitude).
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.analyzers import AnalyzerResult, BaseAnalyzer
from core.utils.normalization import log_norm

# Working size: longest image side is downscaled to this before analysis so
# Laplacian variance is stable across resolutions (DEC-007 gives us the
# decoded array; resizing a small copy is cheap).
_WORKING_MAX_DIM = 1024

# Provisional calibration for log_norm (Laplacian variance at working size).
# Below _VAR_LO => 0.0 (extremely blurry); above _VAR_HI => 1.0 (very sharp).
# To be tuned against the local benchmark set (Sprint 1 verification).
_VAR_LO = 5.0
_VAR_HI = 2000.0


def _to_working_gray(image: np.ndarray) -> np.ndarray:
    """Convert BGR to grayscale and downscale so max dimension <= working size."""
    gray: np.ndarray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    longest = max(height, width)
    if longest > _WORKING_MAX_DIM:
        scale = _WORKING_MAX_DIM / longest
        new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
        gray = cv2.resize(gray, new_size, interpolation=cv2.INTER_AREA)
    return gray


class BlurAnalyzer(BaseAnalyzer):
    """Computes blur_score in [0, 1]: lower = blurrier (see features schema v1)."""

    @property
    def metric_name(self) -> str:
        return "blur_score"

    def analyze(self, image: np.ndarray, path: Path) -> AnalyzerResult | None:
        if image.size == 0:
            return None
        gray = _to_working_gray(image)
        variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        score = log_norm(variance, _VAR_LO, _VAR_HI)
        if score is None:
            return None
        return AnalyzerResult(metric_name=self.metric_name, value_real=score, value_text=None)
