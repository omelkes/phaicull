"""Analyzers — modules that compute exactly one metric (e.g., blur score)."""

from core.analyzers.base import AnalyzerResult, BaseAnalyzer
from core.analyzers.blur import BlurAnalyzer
from core.analyzers.exposure import ExposureAnalyzer
from core.analyzers.duplicates import DuplicatesAnalyzer

__all__ = [
    "AnalyzerResult",
    "BaseAnalyzer",
    "BlurAnalyzer",
    "ExposureAnalyzer",
    "DuplicatesAnalyzer",
    "get_sprint1_analyzers",
]


def get_sprint1_analyzers() -> list[BaseAnalyzer]:
    """Return instances of all Sprint 1 analyzers.

    This factory is used by the scan pipeline to obtain the list of
    analyzers without importing concrete classes at call sites.
    """
    return [
        BlurAnalyzer(),
        ExposureAnalyzer(),
        DuplicatesAnalyzer(),
    ]

