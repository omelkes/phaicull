"""Tests for scripts/verify_sprint1.py (pure checks + synthetic photo generator)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from core.analyzers.blur import BlurAnalyzer
from core.analyzers.duplicates import DuplicatesAnalyzer
from core.grouping import parse_phash

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_sprint1.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_sprint1", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations via sys.modules
    spec.loader.exec_module(module)
    return module


v = _load()


def _entries(blurry: list[float | None], sharp: list[float | None]) -> list[object]:
    return [v.BlurEntry(f"b{i}", v.BLURRY, s) for i, s in enumerate(blurry)] + [
        v.BlurEntry(f"s{i}", v.SHARP, s) for i, s in enumerate(sharp)
    ]


# --- check_speed ---


def test_speed_pass_and_fail() -> None:
    assert v.check_speed(1000, 120.0).verdict == v.Verdict.PASS
    assert v.check_speed(1200, 301.0).verdict == v.Verdict.FAIL


def test_speed_needs_1000_files() -> None:
    result = v.check_speed(999, 1.0)
    assert result.verdict == v.Verdict.SKIP
    assert "need" in result.detail


def test_speed_no_files_is_skip() -> None:
    assert v.check_speed(0, 0.0).verdict == v.Verdict.SKIP


# --- check_blur_ranking ---


def test_blur_fails_when_a_sharp_photo_is_in_worst_10() -> None:
    entries = _entries([0.1 + i / 100 for i in range(12)], [0.5, 0.6, 0.15])
    result = v.check_blur_ranking(entries)
    assert result.verdict == v.Verdict.FAIL
    assert result.detail.startswith("9/10")


def test_blur_pass_clean_separation() -> None:
    entries = _entries([0.1] * 10 + [0.7], [0.5, 0.6])
    # One blurry photo scores above the sharp ones, but the worst 10 are still all blurry.
    assert v.check_blur_ranking(entries).verdict == v.Verdict.PASS


def test_blur_skip_with_fewer_than_10_blurry() -> None:
    assert v.check_blur_ranking(_entries([0.1] * 9, [0.9])).verdict == v.Verdict.SKIP


def test_blur_skip_without_sharp() -> None:
    assert v.check_blur_ranking(_entries([0.1] * 10, [])).verdict == v.Verdict.SKIP


def test_blur_missing_score_fails() -> None:
    result = v.check_blur_ranking(_entries([0.1] * 9 + [None], [0.9]))
    assert result.verdict == v.Verdict.FAIL
    assert "b9" in result.detail


def test_blur_ignores_unlabelled_files() -> None:
    entries = [*_entries([0.2] * 10, [0.9]), v.BlurEntry("loose.jpg", "", 0.0)]
    assert v.check_blur_ranking(entries).verdict == v.Verdict.PASS


# --- grouping stability ---


def test_partition_ignores_group_ids() -> None:
    assert v.partition({1: 7, 2: 7, 3: 9}) == v.partition({1: 40, 2: 40, 3: 41})


def test_grouping_stable_and_changed() -> None:
    a = v.partition({1: 1, 2: 1})
    b = v.partition({1: 1, 3: 1})
    assert v.check_grouping_stable(a, a).verdict == v.Verdict.PASS
    assert v.check_grouping_stable(a, b).verdict == v.Verdict.FAIL


# --- label_for ---


def test_label_for(tmp_path: Path) -> None:
    root = tmp_path / "benchmark"
    assert v.label_for(root / "blurry" / "a.jpg", root) == "blurry"
    assert v.label_for(root / "a.jpg", root) == ""
    assert v.label_for(tmp_path / "elsewhere.jpg", root) == ""


# --- synthetic photos ---


def test_make_photo_is_deterministic() -> None:
    a = v.make_photo(3, 320, 240)
    assert a.shape == (240, 320, 3) and a.dtype == np.uint8
    assert np.array_equal(a, v.make_photo(3, 320, 240))
    assert not np.array_equal(a, v.make_photo(4, 320, 240))


@pytest.mark.parametrize("seed", range(4))
def test_blurred_photo_scores_lower(seed: int) -> None:
    """Both blur kinds (gaussian, motion) must lower blur_score clearly."""
    img = v.make_photo(seed, 1008, 756)
    blur = BlurAnalyzer()
    sharp = blur.analyze(img, Path("x.jpg"))
    blurred = blur.analyze(v.apply_blur(img, seed), Path("x.jpg"))
    assert sharp is not None and blurred is not None
    assert sharp.value_real is not None and blurred.value_real is not None
    assert blurred.value_real < sharp.value_real - 0.1


def test_generated_duplicate_groups_with_original(tmp_path: Path) -> None:
    """Every DUPLICATE_EVERY-th photo is a near-duplicate of the one before (pHash ≤ 6)."""
    jobs = v.photo_jobs(tmp_path, v.DUPLICATE_EVERY, 640, 480)
    for job in jobs:
        v._render(job)
    dup = DuplicatesAnalyzer()

    def phash(path: Path) -> int:
        import cv2

        result = dup.analyze(cv2.imread(str(path)), path)
        assert result is not None and result.value_text is not None
        parsed = parse_phash(result.value_text)
        assert parsed is not None
        return parsed

    original, copy, other = jobs[-2].path, jobs[-1].path, jobs[0].path
    assert (phash(original) ^ phash(copy)).bit_count() <= 6
    assert (phash(original) ^ phash(other)).bit_count() > 6
