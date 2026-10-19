# PLAN — Sprint 1 grouping (visual similarity)

**Status:** In progress (G3 done)  
**Branch:** `sprint1-grouping`  
**Date:** 2026-09-21  
**TODO:** Sprint 1 §5 Grouping Logic

---

## Product intent

A parent does not care that two photos were taken in the same second. They care that photos of the **same activity or subject** sit together, and that a **different moment in the same minute** does not.

Example:

- Karting session → those photos belong together.
- Child with a butterfly, taken while a sibling is racing → **separate** group.
- Two frames of the same karts can look very different (angle, motion blur, which car is in front) → pHash will **not** join them. That is expected in Sprint 1.

**Direction:** group by visual similarity (and later by activity). **Not** by time window. Older docs that say “burst within 5 seconds” are superseded for grouping.

---

## What Sprint 1 actually delivers

**Near-duplicate clusters via pHash Hamming distance.**

After Brawn writes `phash` metrics, Brain clusters files whose 64-bit hashes differ by ≤ `phash_hamming_max` (default 6). Each connected component with 2+ files becomes a `groups` row; `files.group_id` is set. Singletons stay `NULL`.

This catches: burst frames that barely changed, accidental double-taps, export/copy near-duplicates, slight exposure shifts.

This does **not** catch: “all the kart photos” vs “the butterfly.” Those need a scene/activity embedding (Sprint 2 CLIP). pHash is a 64-bit thumbnail of structure; two race shots from different angles hash like unrelated images (~distance 32).

```
Sprint 1  pHash Hamming     →  "these frames are almost the same picture"
Sprint 2  CLIP / embeddings →  "these pictures are about the same activity"
```

Starting with pHash is still the right first step: the metric exists, it is offline and cheap, and it will not glue the butterfly to the race.

---

## What / Why / Alignment

**What:** Post-scan Brain pass. Load `status=ok` files that have a `phash` metric. Union-find on Hamming ≤ threshold. Wipe and rewrite `groups` + `group_id`. No new analyzer. No new dependency. No capture-time extraction.

**Why:** `groups` / `group_id` exist but are unused. JSON already has `group_id` and `summary.duplicate_groups`. Sprint 2 Best-of and the UI grid need *some* cluster. Product goal is visual/activity, so the first cluster type is visual near-duplicates, not a clock.

**Alignment:**
- Brain-only (64-bit XOR). DAO-only SQL. Path objects unchanged.
- Additive: optional `phash_hamming_max` on `Config`; new DAO methods. No schema bump.
- Idempotent: regroup from current DB every scan. **Membership** is stable, not integer ids.
- Privacy: uses only in-DB `phash`. No network.

---

## Decisions

```
Decision: pHash-only grouping for Sprint 1. No time edges. No captured_at metric.
  Union-find: connect files if Hamming(phash_i, phash_j) ≤ phash_hamming_max (default 6).
  Persist a groups row only when size ≥ 2. Missing phash → no edges (stay NULL).
Alternatives:
  A) Time-window bursts — rejected. Same-second ≠ same activity (butterfly vs race).
  B) Time ∪ pHash — rejected. Time edges re-introduce the butterfly/race merge.
  C) CLIP activity clusters now — too early; no embedding pipeline yet (Sprint 2).
  D) Two group kinds (duplicate vs activity) — schema break; one group_id FK.
Rationale: Matches the parent use case for "do not group by clock." pHash is the
only visual signal we have. Hamming ≤ 6 is already documented in analyzers_sprint1.
Activity-level groups wait for embeddings.
```

```
Decision: No time cap on pHash edges.
  Hamming ≤ 6 is already a near-copy test; "same wall all afternoon" does not
  survive that threshold. A 1-hour cap would also drop true copies with stripped
  EXIF and a later download mtime (WhatsApp, AirDrop).
Alternatives:
  A) Require |Δt| ≤ N — rejects untimed duplicates; user does not want time as a key.
  B) Time as a soft prior only — defer until activity embeddings exist.
Rationale: For Sprint 1 the failure mode we must avoid is merging different
subjects. pHash≤6 already avoids that. Do not re-introduce a clock.
```

```
Decision: Regroup from current DB state every scan. If the computed membership
  equals the stored membership, write nothing. Otherwise wipe and rewrite
  (SET group_id=NULL, DELETE FROM groups, insert, assign) in one transaction.
  Stability = same membership for the same (phash set, threshold). Integer ids
  stay the same across unchanged rescans and are reassigned only when membership changes.
Alternatives:
  A) Always wipe and rewrite — ids change on every scan even when nothing changed;
     updated_at churns on every grouped file (noise for a UI watcher).
  B) Patch only changed groups — complex, easy to get wrong.
  C) Stable hash identity column — schema change; revisit when UI stores keepers.
Rationale: The no-op check is one extra read and a set comparison. It makes
"duplicate groups are stable across runs" (Sprint 1 verification) true for ids
too in the common case. Ids are still documented as ephemeral.
```

```
Decision: Leave Config.burst_window_seconds in place; do not use it for grouping.
  Removing or renaming it is a config-contract change. Unused is fine.
Rationale: Additive-only. A later embedding pass may still want an optional
time prior; that is a new decision, not this one.
```

---

## Risks

| Risk | Mitigation |
|---|---|
| Parents expect “karts folder” from Sprint 1 | Docs and CLI wording: “near-duplicates,” not “activities.” Sprint 2 owns activity. |
| Two race photos stay ungrouped | Expected. Do not loosen Hamming to “fix” it — that merges butterfly with karts. |
| Union-find is transitive (A≈B≈C) | Acceptable at Hamming ≤ 6 (near-copies of near-copies). |
| All-pairs Hamming on large libraries | 1k: well under a second. 10k: ~50M pairs, likely seconds on the Brain thread. G3 logs count and time (constraint 12); optimize only if the measurement says so. |
| Ephemeral `group_id` breaks later keepers | No-op on unchanged membership keeps ids stable in the common case; still documented as ephemeral. Stable identity is a later schema ASK. |
| `burst_window_seconds` in config looks like grouping still uses time | Plan + grouping docs state it is unused. |

---

## Out of scope

Thumbnailer, `--json`, progress events, SIGINT, blur calibration, capture-time / EXIF datetime, CLIP embeddings, Best-of keeper pick.

Stale DB rows (file deleted from disk but still `status=ok`) are an existing scan limitation, not a grouping task. Do not add a cleanup pass here.

Do not add `content_hash` edges. Identical bytes already share a pHash; an extra exact-hash rule would not change Sprint 1 groups.

---

## Implementation constraints (review 2026-09-28)

Direction is unchanged. These are holes that G1–G5 must cover:

1. **One transaction for regroup.** `reset_groups` + insert groups + assign `group_id` must commit together. If reset is committed first and assign fails, every file is left with `group_id = NULL`.
2. **Grouping must not lose metrics.** Wrap the pass in `run_scan` so an exception logs and leaves analysis rows intact. Add `ScanSummary` fields only additively (`duplicate_groups: int = 0` is enough; no need for a failure counter unless it is free).
3. **NULL `group_id` before `DELETE FROM groups`.** SQLite foreign keys are currently off (`connection.py` only sets WAL). Still write the SQL as if FKs were on, so enabling them later does not break reset.
4. **Config bounds.** `phash_hamming_max: int` with `ge=0`, `le=64`, default 6. In G4, keep `burst_window_seconds` but change its Field description to “unused by grouping; kept for config compatibility” so the config object does not keep claiming time-bursts.
5. **Always reconcile with the DB; never skip reset by candidate count.** *(Revised 2026-10-11; the earlier "skip reset when fewer than two valid phashes" rule was wrong.)* `insert_file` preserves `group_id` on rescan via `COALESCE`. A file that was grouped and is now `load_failed` therefore keeps its old `group_id` until grouping clears it. If reset were skipped whenever fewer than two valid hashes remain, those stale ids would survive. Grouping reads the DB, not the current scan, so a failed scan cannot "wipe good groups": those files really are no longer `ok`. The protection against partial failure is the transaction (constraint 1), not skipping. The pipeline does not reach grouping for an empty folder, because `run_scan` returns early (G4).
6. **Stable membership tests, not stable integer ids.** Assert frozensets of paths (or file ids) per group. AUTOINCREMENT ids will grow after wipe.
7. **Test layout.** `tests/grouping/test_phash_cluster.py` (G2), `tests/grouping/test_service.py` (G3). Pipeline coverage in `tests/scanner/test_pipeline.py` (G4): two copies of the same synthetic JPEG share a group; a different-colored image does not; `load_failed` / MIME-reject stay `NULL`.
8. **G5 doc targets.** Write `docs/grouping.md` as the contract. Point `docs/json_contract_scan_v1.md` at that file (it currently links this plan — too early). Also update README “burst” wording so Phase 1 matches visual near-duplicates.
9. **Invalid `phash` text.** Non-hex, wrong length, empty → treat as missing (no edges). Analyzer writes 16 hex chars; the clusterer must not throw on a bad row.
10. **The service owns its transaction.** `regroup` commits on success and calls `rollback()` on any exception, then re-raises; G4 catches and logs. On entry it raises if `conn.in_transaction` is already true, so it can never commit a caller's half-written batch. The pipeline already commits after `_process_files`.
11. **Pass the threshold, not `Config`.** `regroup(conn, *, hamming_max: int)`. It raises `ValueError` outside 0..64. This keeps `core/grouping` independent of config loading; G4 passes `config.phash_hamming_max`.
12. **Measure clustering cost.** All-pairs is O(n²) in pure Python, and it runs on the Brain thread. 1k files is about 0.5M comparisons (well under a second). 10k is about 50M, likely several seconds. Log candidate count and elapsed time at INFO so a real library shows the number. Optimizing (numpy, prefix buckets, `to_thread`) is a separate task, opened only if the measurement says so.

---

## Atomic tasks (one commit each)

Implement only after this plan is **Accepted**.

- [x] **G1. DAO group methods:** `insert_group`, `set_file_group`, `list_files_for_grouping` (`status=ok` + `phash`), `reset_groups` (NULL `group_id` **then** `DELETE FROM groups`), `count_multi_file_groups`. SQL only in `dao.py`. Tests in `tests/database/test_dao.py`. Caller owns the transaction (DAO methods do not commit).
- [x] **G2. pHash clustering (pure):** `core/grouping/phash_cluster.py` — hex → 64-bit, Hamming via XOR `int.bit_count()`, union-find if distance ≤ max. No timestamps. Invalid/missing hex → no edges, no throw. Tests in `tests/grouping/test_phash_cluster.py`: identical hash, distance 6 vs 7, missing/invalid hex, empty, singleton, transitivity, deterministic membership (sort by file id/path before union).
- [x] **G3. Grouping service:** `core/grouping/service.py` — `regroup(conn, *, hamming_max) -> GroupingResult`.
  - Steps: assert no open transaction → load candidates (DAO) → `cluster_by_phash` → read stored membership → if equal, return `changed=False` with no writes → else `reset_groups`, insert one group per cluster (ordered by smallest file id), `set_file_group` for members, commit. Rollback + re-raise on error.
  - DAO addition (same commit): `list_group_memberships(conn) -> dict[int, int]` (file_id → group_id for every file with non-NULL group_id, any status). Stored membership = files grouped by group_id, **including singletons**, so a stale one-file group also counts as a change and gets cleared.
  - `GroupingResult` (Pydantic): `candidates`, `invalid_phash` (ok files with missing/invalid hash), `duplicate_groups`, `grouped_files`, `changed`.
  - Tests in `tests/grouping/test_service.py`: identical pair grouped; unrelated hash stays NULL; **unchanged rescan keeps the same ids and writes nothing**; membership change rewrites; **stale `group_id` on a now-`load_failed` file is cleared**; stale ids cleared when **no** valid pairs remain; missing/invalid phash ignored and counted; empty project is a no-op; error mid-write rolls back (previous groups intact); open transaction on entry raises; `hamming_max` out of range raises.
- [ ] **G4. Pipeline + config:** After `_process_files` commit in `run_scan`, call grouping. Catch grouping errors so metrics remain. Add `phash_hamming_max: int = 6` (`ge=0`, `le=64`). Relabel `burst_window_seconds` as unused by grouping. `ScanSummary.duplicate_groups`. CLI prints near-duplicate group count. Pipeline tests: identical pair grouped, different image not, rejects ungrouped. Update `phaicull.toml.example`.
- [ ] **G5. Docs + DEC-009:** `docs/grouping.md` (algorithm, ephemeral ids, what pHash will / will not group). DEC-009 in `docs/decisions.md`. Retarget JSON contract from this plan to `docs/grouping.md`. README Phase 1 / burst wording. Mark TODO grouping done.

**Notes:**
- Package: `core/grouping/` — not an analyzer; do not subclass `BaseAnalyzer`.
- Hamming 6 is already in `docs/analyzers_sprint1.md`.
- Existing `insert_file` / `insert_metric` unchanged.
- Activity clustering is a **new plan** when Sprint 2 embeddings exist (`docs/plan/sprint2-activity-grouping.md`).

---

## Later (not this branch)

Activity grouping (“karts vs butterfly”) needs a vector close to meaning, not a 64-bit DCT hash. The existing Sprint 2 CLIP item is that signal. Likely shape: cosine-similarity graph on embeddings, threshold chosen so different subjects in the same minute stay apart. Time may return only as an optional prior, never as the primary key.
