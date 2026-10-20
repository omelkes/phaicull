## Grouping (Sprint 1): visual near-duplicates

This document is the contract for `files.group_id` and the `groups` table.
Background and rejected alternatives: [`plan/sprint1-grouping.md`](plan/sprint1-grouping.md).
Decision record: DEC-009 in [`decisions.md`](decisions.md).

### What a group means

A group is a set of **two or more photos that are almost the same picture**:
burst frames that barely changed, an accidental double-tap, the same photo
saved or exported twice, a slightly brighter copy.

Grouping is **visual, not time-based**. Two photos taken in the same second
of different subjects (a child with a butterfly while a sibling races) are not
grouped. Two photos of the same activity from different angles are usually
**not** grouped either; "same activity" needs scene embeddings (Sprint 2).

### Algorithm

Runs at the end of every `phaicull scan`, after metrics are committed
(`core/grouping/service.py`, `regroup`).

1. Candidates: files with `status = 'ok'`. Each uses its `phash` metric
   (16 hex chars, 64 bits; see `analyzers_sprint1.md`).
2. Two candidates are connected when the Hamming distance between their
   hashes is at most `phash_hamming_max` (config, default 6, range 0–64).
3. Connected components (union-find, so A≈B and B≈C put A and C together)
   with two or more files become groups.
4. Files with a missing or invalid `phash`, files that are not `ok`
   (`load_failed`, `skipped_invalid_mime`), and singletons have
   `group_id = NULL`.

Grouping reads the whole project DB, not only the files in the current scan.

### Writing and stability

- If the computed membership equals what is stored, **nothing is written**:
  `group_id` values and `updated_at` stay unchanged across unchanged rescans.
- Otherwise all groups are wiped and rewritten in **one transaction**.
  On any error the transaction rolls back and the previous groups remain.
  A grouping failure never removes scan metrics.
- Stale ids are always cleared, e.g. a file that was grouped and now fails to load.

### What consumers may rely on

- `group_id` is either `NULL` or the id of a `groups` row shared by at least
  two files.
- **Membership is the stable contract; integer ids are not.** Ids stay the same
  while membership is unchanged and may all change when any group changes.
  Do not persist `group_id` as a long-lived identity (e.g. for keeper choices).
- `summary.duplicate_groups` (JSON) / "Near-duplicate groups" (CLI) is the
  number of groups after the pass.

### Configuration

```toml
# Max pHash Hamming distance (0-64) for two photos to be near-duplicates.
phash_hamming_max = 6
```

Lower is stricter. Raising it does not produce activity groups; it starts
merging different scenes. `burst_window_seconds` is not used by grouping and
is kept only for config compatibility.

### Known limits

- Comparison is all-pairs: fine for thousands of photos; the pass logs its
  candidate count and duration so large libraries can be measured.
- Files deleted from disk keep their DB rows (existing scan limitation) and can
  still be grouped until that is fixed separately.
