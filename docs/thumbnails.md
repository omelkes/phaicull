## Thumbnail Strategy (Sprint 1)

Thumbnails provide fast preview images for UI grid views without loading
full‑resolution photos.

### Storage Location

- Thumbnails are stored as **files on disk**, not as BLOBs in SQLite.
- Per project, thumbnails live under:
  - `{project_root}/phaicull/thumbs/`

This keeps the SQLite database small and avoids large BLOB I/O while scanning.

### File Naming

Two reasonable strategies are possible; for Sprint 1 we adopt a simple,
deterministic scheme based on the `files.id` primary key:

- File name pattern: `thumb_<file_id>.jpg`
- Example: `thumb_42.jpg` for the row with `files.id = 42`.

Rationale:

- `id` is stable within a project DB.
- Easy for UIs to look up thumbnails given a `files` row.

If needed in later sprints, a hash‑based scheme
(`{content_hash}_300.jpg`) can be added alongside this without breaking
existing consumers.

### Size and Format

- Default longest side: **300px** (max(width, height) = 300).
- Format: JPEG for photos by default.
- PNG may be used for images where lossless thumbnails are preferred; UIs
  should not assume a particular extension beyond what is present on disk.

### UI Lookup Contract

Given a `files` row:

- The UI reads `files.id` from the project DB.
- Thumbnails are expected at:
  - `{project_root}/phaicull/thumbs/thumb_<id>.jpg`
  - UIs should handle the thumbnail being missing (e.g., show placeholder and
    allow lazy generation).

### Regeneration and Caching

- Thumbnails may be generated:
  - During scan.
  - Lazily when the UI first needs them.
- If a thumbnail is missing or stale, it is safe to regenerate it; the
  filename remains the same.

### Implemented (Sprint 1)

- Generated **during every scan** for each file with `status = 'ok'`
  (`core/utils/thumbnail.py`, called from the Brawn worker).
- Made from the **same decoded, EXIF-oriented image** the analyzers use — the
  source file is never decoded twice.
- JPEG, quality 85, longest side 300px. Smaller images are **not upscaled**.
- Thumbnails are regenerated on every scan, so a changed photo gets a fresh one.
- A file that becomes `load_failed` has its old `thumb_<id>.jpg` **removed**, so
  the UI does not keep showing a photo that no longer opens.
- A thumbnail failure never fails the file: status and metrics are kept, and the
  scan summary reports `thumbnail_errors` (CLI: "Thumbnail errors").

How the `files.id` name is assigned: the worker does not know the row id (the
Brain assigns it on insert), so it writes the thumbnail under a random name in
`thumbs/.staging/`, and the Brain atomically renames it to `thumb_<id>.jpg` right
after writing the row. `.staging/` is cleared at the start and end of each scan.
UIs should ignore it.

Thumbnails are renamed before the DB batch commits. On Ctrl+C the batch is
rolled back and thumbnails placed for rows that no longer exist are deleted.

Known limit: if the process is killed hard (SIGKILL, power loss) between rename
and commit, a `thumb_<id>.jpg` may remain for an id with no row. It is not
reused reliably, because the upsert in `insert_file` advances the AUTOINCREMENT
counter, so the next scan can give that file a different id. UIs should only
show thumbnails for ids present in `files`.

