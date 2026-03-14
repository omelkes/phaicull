from __future__ import annotations

from core.analyzers import (
    AnalyzerResult,
    BaseAnalyzer,
    BlurAnalyzer,
    DuplicatesAnalyzer,
    ExposureAnalyzer,
    get_sprint1_analyzers,
)


def test_sprint1_analyzers_metric_names_are_stable() -> None:
    """Ensure Sprint 1 analyzers expose the expected metric_name values."""
    blur = BlurAnalyzer()
    exposure = ExposureAnalyzer()
    duplicates = DuplicatesAnalyzer()

    assert isinstance(blur, BaseAnalyzer)
    assert isinstance(exposure, BaseAnalyzer)
    assert isinstance(duplicates, BaseAnalyzer)

    assert blur.metric_name == "blur_score"
    assert exposure.metric_name == "brightness_score"
    assert duplicates.metric_name == "phash"


def test_get_sprint1_analyzers_returns_all_analyzers() -> None:
    analyzers = get_sprint1_analyzers()
    metric_names = sorted(a.metric_name for a in analyzers)

    assert metric_names == ["blur_score", "brightness_score", "phash"]

    # Ensure return types align with BaseAnalyzer and AnalyzerResult contracts.
    for analyzer in analyzers:
        assert isinstance(analyzer, BaseAnalyzer)
        # analyze() is not implemented yet; it will raise NotImplementedError.
        # This test only validates wiring and metric names, not compute logic.

