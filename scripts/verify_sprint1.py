"""Sprint 1 verification: scan speed, blur ranking, grouping stability.

Plan and pass rules: docs/plan/sprint1-verification.md

    uv run python scripts/verify_sprint1.py generate
    uv run python scripts/verify_sprint1.py run --photos .local-photos/synthetic/photos \
        --benchmark .local-photos/synthetic/benchmark

Exit code of `run`: 0 all checks passed, 1 a check failed, 2 a check could not run
(not enough photos). Fully offline; writes only inside the given folders.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import cv2
import numpy as np
import typer
from loguru import logger

from core.config import Config
from core.database.dao import list_group_memberships, list_metric_values, open_project_connection
from core.scanner.pipeline import ScanSummary, run_scan

SPEED_FILES = 1000
SPEED_LIMIT_S = 300.0
WORST_N = 10
BLURRY = "blurry"
SHARP = "sharp"
DEFAULT_OUT = Path(".local-photos/synthetic")
DEFAULT_BENCHMARK = Path(".local-photos/benchmark")
DUPLICATE_EVERY = 10  # every 10th generated photo is a near-duplicate of the one before

app = typer.Typer(add_completion=False, no_args_is_help=True)


# --- Checks (pure) ---


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class CheckResult:
    name: str
    verdict: Verdict
    detail: str


@dataclass(frozen=True)
class BlurEntry:
    name: str
    label: str
    score: float | None


def check_speed(files: int, seconds: float) -> CheckResult:
    """PASS needs at least SPEED_FILES files scanned within SPEED_LIMIT_S."""
    name = f"Scan {SPEED_FILES} photos < {SPEED_LIMIT_S / 60:.0f} min"
    if files <= 0:
        return CheckResult(name, Verdict.SKIP, "no photos scanned")
    per_1000 = seconds / files * 1000
    detail = f"{files} files in {seconds:.1f} s ({per_1000:.1f} s per 1000)"
    if files < SPEED_FILES:
        return CheckResult(name, Verdict.SKIP, f"{detail}; need ≥ {SPEED_FILES} files")
    verdict = Verdict.PASS if seconds < SPEED_LIMIT_S else Verdict.FAIL
    return CheckResult(name, verdict, detail)


def check_blur_ranking(entries: list[BlurEntry], worst_n: int = WORST_N) -> CheckResult:
    """PASS when the worst_n lowest blur scores all belong to blurry/ photos."""
    name = f"Blur ranking surfaces worst {worst_n}"
    blurry = [e for e in entries if e.label == BLURRY]
    sharp = [e for e in entries if e.label == SHARP]
    if len(blurry) < worst_n or not sharp:
        return CheckResult(
            name,
            Verdict.SKIP,
            f"need ≥ {worst_n} blurry and ≥ 1 sharp photo; found {len(blurry)} / {len(sharp)}",
        )
    missing = [e.name for e in blurry + sharp if e.score is None]
    if missing:
        return CheckResult(name, Verdict.FAIL, f"no blur_score for: {', '.join(missing)}")

    ranked = sorted(blurry + sharp, key=lambda e: (e.score, e.name))
    hits = sum(1 for e in ranked[:worst_n] if e.label == BLURRY)
    max_blurry = max(e.score for e in blurry if e.score is not None)
    min_sharp = min(e.score for e in sharp if e.score is not None)
    detail = (
        f"{hits}/{worst_n} of the lowest scores are blurry "
        f"({len(blurry)} blurry, {len(sharp)} sharp; "
        f"max blurry {max_blurry:.3f}, min sharp {min_sharp:.3f})"
    )
    return CheckResult(name, Verdict.PASS if hits == worst_n else Verdict.FAIL, detail)


def partition(memberships: dict[int, int]) -> frozenset[frozenset[int]]:
    """Group membership as a set of file-id sets (group ids themselves are not stable)."""
    groups: dict[int, set[int]] = {}
    for file_id, group_id in memberships.items():
        groups.setdefault(group_id, set()).add(file_id)
    return frozenset(frozenset(members) for members in groups.values())


def check_grouping_stable(
    first: frozenset[frozenset[int]], second: frozenset[frozenset[int]]
) -> CheckResult:
    name = "Duplicate groups stable across runs"
    if first == second:
        return CheckResult(name, Verdict.PASS, f"{len(first)} groups, identical membership")
    changed = len(first ^ second)
    return CheckResult(name, Verdict.FAIL, f"{changed} groups differ between runs")


def label_for(path: Path, benchmark_root: Path) -> str:
    """First folder under the benchmark root (blurry / sharp / other)."""
    try:
        parts = path.resolve().relative_to(benchmark_root.resolve()).parts
    except ValueError:
        return ""
    return parts[0] if len(parts) > 1 else ""


# --- Synthetic photos ---


def make_photo(seed: int, width: int, height: int) -> np.ndarray:
    """Photo-like BGR image: gradient, hard-edged shapes. No noise (added on save)."""
    rng = np.random.default_rng(seed)
    small_w, small_h = max(2, width // 16), max(2, height // 16)
    top, bottom = rng.integers(0, 256, (2, 3)).astype(np.float32)
    t = np.linspace(0.0, 1.0, small_h, dtype=np.float32)[:, None, None]
    gradient = np.broadcast_to(top * (1 - t) + bottom * t, (small_h, small_w, 3))
    img = cv2.resize(gradient.astype(np.uint8), (width, height), interpolation=cv2.INTER_LINEAR)

    scale = max(width, height) / 1000
    for _ in range(int(rng.integers(25, 60))):
        color = tuple(int(c) for c in rng.integers(0, 256, 3))
        x, y = int(rng.integers(0, width)), int(rng.integers(0, height))
        size = int(rng.integers(20, 250) * scale)
        thickness = -1 if rng.random() < 0.6 else max(1, int(rng.integers(2, 10) * scale))
        shape = rng.integers(0, 3)
        if shape == 0:
            cv2.rectangle(img, (x, y), (x + size, y + size // 2), color, thickness)
        elif shape == 1:
            cv2.circle(img, (x, y), size // 2, color, thickness)
        else:
            end = (x + int(rng.integers(-size, size)), y + int(rng.integers(-size, size)))
            cv2.line(img, (x, y), end, color, max(1, int(3 * scale)))
    return img


def apply_blur(img: np.ndarray, seed: int) -> np.ndarray:
    """Gaussian (missed focus) or linear motion blur (camera shake), scaled to image size."""
    rng = np.random.default_rng(seed)
    scale = max(img.shape[:2]) / 1000
    if rng.random() < 0.5:
        sigma = float(rng.uniform(1.5, 4.0) * scale)
        return cv2.GaussianBlur(img, (0, 0), sigma)
    length = max(3, int(rng.uniform(10, 25) * scale))
    kernel = np.zeros((length, length), np.float32)
    kernel[length // 2, :] = 1.0
    angle = float(rng.uniform(0, 180))
    rotation = cv2.getRotationMatrix2D((length / 2 - 0.5, length / 2 - 0.5), angle, 1.0)
    rotated = cv2.warpAffine(kernel, rotation, (length, length))
    normalized = (rotated / max(float(rotated.sum()), 1e-6)).astype(np.float32)
    return cv2.filter2D(img, -1, normalized)


def _save(img: np.ndarray, path: Path, seed: int, quality: int, brightness: int = 0) -> None:
    """Add sensor-like noise (real blurry photos are noisy too) and write a JPEG."""
    rng = np.random.default_rng(seed + 1_000_003)
    noise = rng.integers(-6, 7, size=(*img.shape[:2], 1), dtype=np.int16)
    noisy = np.clip(img.astype(np.int16) + noise + brightness, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", noisy, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError(f"JPEG encode failed: {path}")
    path.write_bytes(buf.tobytes())


@dataclass(frozen=True)
class PhotoJob:
    path: Path
    seed: int
    width: int
    height: int
    blurred: bool = False
    duplicate: bool = False


def _render(job: PhotoJob) -> None:
    if job.path.exists():
        return
    img = make_photo(job.seed, job.width, job.height)
    if job.blurred:
        img = apply_blur(img, job.seed)
    if job.duplicate:
        _save(img, job.path, job.seed + 7, quality=75, brightness=6)
    else:
        _save(img, job.path, job.seed, quality=90)


def photo_jobs(out: Path, count: int, width: int, height: int) -> list[PhotoJob]:
    jobs: list[PhotoJob] = []
    for i in range(count):
        duplicate = i % DUPLICATE_EVERY == DUPLICATE_EVERY - 1
        seed = i - 1 if duplicate else i  # same content as the previous photo
        jobs.append(PhotoJob(out / f"img_{i:04d}.jpg", seed, width, height, duplicate=duplicate))
    return jobs


def benchmark_jobs(out: Path, per_class: int, width: int, height: int) -> list[PhotoJob]:
    sharp = [
        PhotoJob(out / SHARP / f"sharp_{i:02d}.jpg", 100_000 + i, width, height)
        for i in range(per_class)
    ]
    blurry = [
        PhotoJob(out / BLURRY / f"blurry_{i:02d}.jpg", 200_000 + i, width, height, blurred=True)
        for i in range(per_class)
    ]
    return sharp + blurry


def _parse_size(size: str) -> tuple[int, int]:
    width, _, height = size.lower().partition("x")
    return int(width), int(height)


@app.command()
def generate(
    out: Annotated[Path, typer.Option(help="Output folder (keep it under .local-photos/).")] = (
        DEFAULT_OUT
    ),
    count: Annotated[int, typer.Option(help="Photos for the speed/stability folder.")] = 1000,
    benchmark_per_class: Annotated[int, typer.Option(help="Sharp and blurry photos each.")] = 15,
    size: Annotated[str, typer.Option(help="WIDTHxHEIGHT; default is a 12 MP phone.")] = (
        "4032x3024"
    ),
) -> None:
    """Write photo-like JPEGs to OUT/photos and OUT/benchmark/{sharp,blurry}."""
    width, height = _parse_size(size)
    (out / "photos").mkdir(parents=True, exist_ok=True)
    (out / "benchmark" / SHARP).mkdir(parents=True, exist_ok=True)
    (out / "benchmark" / BLURRY).mkdir(parents=True, exist_ok=True)
    jobs = photo_jobs(out / "photos", count, width, height)
    jobs += benchmark_jobs(out / "benchmark", benchmark_per_class, width, height)

    started = time.perf_counter()
    with ProcessPoolExecutor() as pool:
        for done, _ in enumerate(pool.map(_render, jobs, chunksize=4), start=1):
            if done % 100 == 0 or done == len(jobs):
                typer.echo(f"  generated {done}/{len(jobs)}")
    typer.echo(f"Done in {time.perf_counter() - started:.0f} s → {out}")


# --- Run ---


def _scan(folder: Path, config: Config) -> tuple[ScanSummary, float]:
    started = time.perf_counter()
    summary = asyncio.run(run_scan(folder, config))
    return summary, time.perf_counter() - started


def _memberships(folder: Path) -> frozenset[frozenset[int]]:
    conn = open_project_connection(folder)
    try:
        return partition(list_group_memberships(conn))
    finally:
        conn.close()


def _blur_entries(benchmark: Path) -> list[BlurEntry]:
    conn = open_project_connection(benchmark)
    try:
        rows = list_metric_values(conn, "blur_score")
    finally:
        conn.close()
    return [
        BlurEntry(Path(r.file_path).name, label_for(Path(r.file_path), benchmark), r.value_real)
        for r in rows
    ]


def _has_photos(folder: Path) -> bool:
    return folder.is_dir() and any(p.is_file() for p in folder.rglob("*.*"))


@app.command()
def run(
    photos: Annotated[Path, typer.Option(help="Folder with ≥ 1000 photos (speed + stability).")],
    benchmark: Annotated[Path, typer.Option(help="Folder with blurry/ and sharp/.")] = (
        DEFAULT_BENCHMARK
    ),
) -> None:
    """Run the three Sprint 1 checks and print a report."""
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    config = Config()
    workers = config.scanner.max_workers or os.cpu_count()
    typer.echo(f"Machine: {os.cpu_count()} CPUs, {workers} workers")

    results: list[CheckResult] = []
    if _has_photos(photos):
        typer.echo(f"Scanning {photos} (run 1, timed)…")
        summary, seconds = _scan(photos, config)
        results.append(check_speed(summary.processed, seconds))
        first = _memberships(photos)
        typer.echo(f"Scanning {photos} (run 2)…")
        _scan(photos, config)
        results.append(check_grouping_stable(first, _memberships(photos)))
    else:
        results.append(CheckResult("Speed / stability", Verdict.SKIP, f"no photos in {photos}"))

    if _has_photos(benchmark):
        typer.echo(f"Scanning {benchmark}…")
        _scan(benchmark, config)
        entries = _blur_entries(benchmark)
        results.append(check_blur_ranking(entries))
        ranked = sorted(entries, key=lambda e: (e.score is None, e.score or 0.0, e.name))
        typer.echo("Lowest blur scores:")
        for e in ranked[:WORST_N]:
            score = "none" if e.score is None else f"{e.score:.3f}"
            typer.echo(f"  {score}  {e.label or '-':6}  {e.name}")
    else:
        results.append(
            CheckResult("Blur ranking", Verdict.SKIP, f"no photos in {benchmark}")
        )

    typer.echo("\nSprint 1 verification")
    for r in results:
        typer.echo(f"  [{r.verdict}] {r.name}: {r.detail}")
    if any(r.verdict == Verdict.FAIL for r in results):
        raise typer.Exit(1)
    if any(r.verdict == Verdict.SKIP for r in results):
        raise typer.Exit(2)


if __name__ == "__main__":
    app()
