"""Scanner — Brain/Brawn scan pipeline for Phaicull.

Brain (asyncio): file-walking, I/O, DB writes.
Brawn (ProcessPoolExecutor): image loading and analyzers.
"""

from core.scanner.pipeline import ScanSummary, run_scan
from core.scanner.worker import FileResult

__all__ = ["FileResult", "ScanSummary", "run_scan"]
