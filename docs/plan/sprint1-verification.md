# PLAN — Sprint 1 §7: Verification

**Status:** In progress — V1–V3 done; waiting for real benchmark photos (V4) (accepted 2026-10-20: verify script + generated photos now, real photos later; blur rule "worst 10")  
**Branch:** `sprint1-verification`  
**TODO:** Sprint 1 §7

---

## What / Why

**What:** A repeatable script, `scripts/verify_sprint1.py`, that checks the three Sprint 1 success criteria and exits non-zero if any fails.

**Why:** The checks must be rerun when real photos are added and after every blur-constant change. A one-off manual run cannot be repeated.

**Alignment:** Uses `run_scan` and the DAO only (no SQL in the script). Fully offline. Dev tool, not a CLI command, so no stable-API change.

---

## Checks

| Criterion | How | Pass |
|---|---|---|
| Scan 1k photos < 5 min | Time `run_scan` on a folder with ≥ 1000 photos, default config | elapsed < 300 s with ≥ 1000 files; fewer files → reported as extrapolated, not a pass |
| Blur ranking surfaces worst 10 | Scan `benchmark/` (subfolders `blurry/`, `sharp/`), sort by `blur_score` ascending | The 10 lowest scores are all in `blurry/` (needs ≥ 10 blurry, ≥ 1 sharp); a missing score fails |
| Duplicate groups stable across runs | Scan the 1k folder twice | Same group membership (partition of file ids) both times |

---

## Photos

- `generate` writes phone-size (4032×3024) photo-like JPEGs: shapes, gradients and sensor-like noise, so the blur metric sees real edges. About 10 % are near-duplicate re-saves (different JPEG quality, small brightness shift), so grouping has something to keep stable.
- Synthetic benchmark: sharp images vs Gaussian- and motion-blurred ones.
- Output goes to `.local-photos/synthetic/` (gitignored). The real benchmark stays at `.local-photos/benchmark/{blurry,sharp}`.

Generated photos prove speed and stability. They only **indicate** blur ranking: synthetic blur is easier than real camera shake or missed focus. Sprint 1 blur sign-off needs the real benchmark run.

---

## Risks

| Risk | Mitigation |
|---|---|
| Timing depends on the machine | Report CPU count and workers next to the time. |
| Synthetic blur is too easy | Recorded as provisional; rerun on real photos. |
| Generating 1000 × 12 MP JPEGs is slow/big (~3 GB) | Parallel generation; `--count` and `--size` options. |

---

## Atomic tasks

- [x] **V1. DAO read:** `list_metric_values(conn, metric_name)` for `status='ok'` files. Tests.
- [x] **V2. Verify script:** `generate` and `run`; pure check helpers unit-tested; docs (README).
- [x] **V3. Results:** run on generated photos, record results here, update TODO.
- [ ] **V4. Real benchmark:** rerun the blur check on real photos in `.local-photos/benchmark/`.

---

## Results — 2026-10-20 (generated photos)

Machine: 6 CPUs (WSL2), 6 workers, default config. 1000 JPEGs 4032×3024 (2.1 GB), 100 of them near-duplicates.

| Check | Verdict | Detail |
|---|---|---|
| Scan 1000 photos < 5 min | PASS | 172.5 s (≈ 0.17 s per photo; 43 % headroom) |
| Groups stable across runs | PASS | 100 groups, identical membership; exactly the 100 planted pairs |
| Blur worst 10 | PASS (synthetic only) | 10/10 blurry; max blurry 0.296, min sharp 0.421 (15 + 15 photos) |

Notes:
- Per-photo cost on one core is about 0.5 s, mostly JPEG decode (≈ 0.3–0.4 s); analyzers + thumbnail ≈ 0.2 s.
- Synthetic blur is strong (Gaussian σ 6–16 px or 40–100 px motion at 12 MP). Real slight blur and missed focus will sit closer to sharp photos, so the real run (V4) is the actual sign-off.
- The real benchmark folders were empty on this date; `run --benchmark .local-photos/benchmark` reports SKIP (exit 2) until photos are added.
