# PLAN — Sprint 1 §7: Verification

**Status:** In progress (accepted 2026-10-20: verify script + generated photos now, real photos later; blur rule "worst 10")  
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
- [ ] **V2. Verify script:** `generate` and `run`; pure check helpers unit-tested; docs (README).
- [ ] **V3. Results:** run on generated photos, record results here, update TODO.
