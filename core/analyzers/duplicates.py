"""Near-duplicate detection via perceptual hash (pHash).

Standard DCT-based pHash implemented with OpenCV (no extra dependency,
DEC per sprint1-analyzers plan):

1. Grayscale, resize to 32x32 (INTER_AREA).
2. 2D DCT; keep the top-left 8x8 low-frequency block.
3. Threshold each coefficient against the median of the AC coefficients
   (DC term excluded — classic pHash convention). Excluding DC makes the
   hash robust to uniform brightness shifts: they change only the DC
   coefficient, so at most 1 bit flips.
4. Encode the 64 bits as a 16-character hex string (value_text).

Perceptually similar images differ in only a few bits (small Hamming
distance); unrelated images differ in ~32. Grouping by Hamming distance
is a separate Sprint 1 task.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.analyzers import AnalyzerResult, BaseAnalyzer

_DCT_SIZE = 32
_HASH_SIZE = 8


def phash_hex(image: np.ndarray) -> str:
    """Compute the 64-bit perceptual hash of a BGR image as 16 hex chars."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (_DCT_SIZE, _DCT_SIZE), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(resized.astype(np.float32))
    low_freq = dct[:_HASH_SIZE, :_HASH_SIZE]
    ac_coefficients = low_freq.flatten()[1:]  # exclude DC term (index 0)
    median = np.median(ac_coefficients)
    bits = (low_freq > median).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


class DuplicatesAnalyzer(BaseAnalyzer):
    """Computes phash (64-bit perceptual hash, hex string) for duplicate detection."""

    @property
    def metric_name(self) -> str:
        return "phash"

    def analyze(self, image: np.ndarray, path: Path) -> AnalyzerResult | None:
        if image.size == 0:
            return None
        return AnalyzerResult(
            metric_name=self.metric_name,
            value_real=None,
            value_text=phash_hex(image),
        )
