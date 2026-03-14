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

