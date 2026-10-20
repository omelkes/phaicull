# PLAN — Sprint 1 §6: CLI integration & resilience

**Status:** In progress (accepted 2026-10-11: status_reason column, keep positional CLI)  
**Branch:** `sprint1-cli-resilience`  
**Date:** 2026-10-11  
**TODO:** Sprint 1 §6

---

## Current state (checked against code)

| TODO item | State | Evidence |
|---|---|---|
| CLI scan command | Effectively done | `phaicull scan <folder> [--config]` exists since Sprint 0. TODO and `json_contract_scan_v1.md` still say `--folder`. |
| Deterministic scan | Not done | Discovery is sorted, but `pipeline.py` writes results in **completion order** (`asyncio.as_completed`). With >1 worker, new files get different `files.id` per run → different `thumb_<id>.jpg` names and group ids. No randomness exists anywhere, so "fixed seeds" has nothing to fix. |
| Error handling | Half done | Unreadable files never crash the scan and get `status = load_failed`. The **reason** (too large, zero-byte, cannot decode…) is only a DEBUG log; it is not stored. |
| Ctrl+C | Not done | No handling. `ProcessPoolExecutor`'s `with` waits for **all queued files** on exit, so Ctrl+C can hang. Spawned workers also get SIGINT and print tracebacks. |

---

## What / Why / Alignment

**What:** Make scans reproducible, record why a file was skipped, and stop cleanly on Ctrl+C. Align the TODO/contract wording with the CLI that exists.

**Why:** Sprint 1 verification needs "groups stable across runs" (needs stable ids). UIs need to explain a skipped photo. AGENTS.md requires graceful SIGINT with rollback of the uncommitted batch.

**Alignment:** Brain/Brawn unchanged. DAO-only SQL. Additive contract changes only (nullable column, optional DAO param, optional summary fields). No new dependency.

---

## Decisions

```
Decision: Deterministic = write results in discovery (sorted path) order.
  Await futures in submission order instead of as_completed. Workers stay busy
  (the pool queue is unchanged); only DB writes wait for the earliest file.
Alternatives:
  A) Pre-insert all rows before dispatch — needs a "pending" status and leaves
     junk rows on crash.
  B) Keep completion order — ids differ per run and per worker count.
Rationale: Smallest change; same folder → same ids regardless of max_workers.
  Cost: a slow file delays later writes (not processing). Progress logs stay correct.
```

```
Decision: Store the skip reason in a new nullable column files.status_reason (migration 004).
  status stays "load_failed" (stable value). Reason codes: zero_byte, too_large,
  dimensions_too_large, unreadable, cannot_open, decode_failed. NULL when ok.
  insert_file gets an optional status_reason parameter (additive). The loader
  returns a reason instead of a bare None (internal API).
Alternatives:
  A) Log only — satisfies the TODO wording but UIs cannot explain a skip;
     AGENTS.md: "Silent failures → log to SQLite status column".
  B) New status values (load_failed_too_large…) — changes the meaning of a stable field.
Rationale: Additive, nullable, keeps every existing consumer working.
  Schema change approved by user 2026-10-11 (AGENTS.md decision matrix).
```

```
Decision: Ctrl+C stops dispatch, cancels queued work, rolls back the uncommitted
  batch, skips grouping, cleans thumbnail staging, prints "Scan interrupted" to
  stderr, exits with code 130.
  Workers ignore SIGINT (pool initializer) so only the Brain handles it.
  Committed batches (every 50 files) are kept; a rescan continues normally.
Alternatives:
  A) Commit the partial batch — AGENTS.md says roll back.
  B) Let KeyboardInterrupt propagate — hangs on pool shutdown, tracebacks.
Rationale: AGENTS.md "Graceful Shutdown"; 130 is the shell convention for SIGINT.
```

```
Decision: Keep `phaicull scan <folder>`; do not add --folder.
  Update TODO wording and json_contract_scan_v1.md example.
Alternatives: add --folder as an alias (two ways to say one thing).
Rationale: The positional form is the shipped CLI; changing it is a contract change.
```

Output streams: human summary on stdout (Rich), logs on stderr (loguru default). No change needed; documented for C4.

---

## Risks

| Risk | Mitigation |
|---|---|
| In-order writes stall behind one huge file | Only DB writes wait; workers keep processing. Acceptable for Sprint 1. |
| Ctrl+C during the final commit or grouping | Grouping already has its own transaction + rollback; commit is atomic in SQLite. |
| Existing DBs lack `status_reason` | Migration 004 adds it as nullable; old rows read NULL. |
| SIGINT testing is flaky across OSes | Test the cancellation path by raising `KeyboardInterrupt` from inside the pipeline (monkeypatch), not by sending real signals. |

---

## Out of scope

`--json` output (JSON contract) and progress events (`--progress-json`) — separate TODO items. Blur calibration and §7 verification.

---

## Atomic tasks (one commit each)

- [x] **C1. CLI command wording:** Mark "CLI scan command" done; fix `--folder` wording in TODO and `json_contract_scan_v1.md`. Docs only.
- [x] **C2. Deterministic order:** Await results in submission order in `_process_files`. Tests: same folder scanned into two fresh DBs with `max_workers=1` and `max_workers=4` → identical `(id, file_path)` lists and thumbnail names; rescan keeps ids. Document "fixed seeds: none needed" in TODO.
- [x] **C3. Skip reasons:** Loader returns a reason code; `FileResult.status_reason`; migration 004 `files.status_reason TEXT NULL`; `insert_file(..., status_reason=None)`; cleared to NULL when a file loads again. Log reason at WARNING with path. CLI prints load failures grouped by reason. Tests: each reason code via loader; pipeline stores it; recovery clears it; migration test. Docs: JSON contract per-file `status_reason` (optional), schema docs.
- [ ] **C4. Ctrl+C:** Worker initializer ignores SIGINT; pipeline catches `KeyboardInterrupt`/`CancelledError`, `executor.shutdown(cancel_futures=True)`, `conn.rollback()`, skips grouping, re-raises; CLI prints "Scan interrupted" to stderr, exit 130. Tests: interrupt after N results → committed batches kept, partial batch rolled back, no grouping, staging dir removed, CLI exit 130.
