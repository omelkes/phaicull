## JSON Contract for `phaicull scan` (v1)

This document defines the **machine-readable JSON output** for
`phaicull scan` in Sprint 1.

- Contract is **stable**: field names and types must remain backward‑compatible.
- Versioned by `json_schema_version`.

### Top‑Level Object

The CLI emits a single JSON object when run in JSON mode (for example,
`phaicull scan --folder <path> --json` in a future task):

- `json_schema_version` (integer): current JSON contract version. Starts at `1`.
- `project_root` (string): absolute path to the scanned folder.
- `schema_version` (string): SQLite schema version of the project DB.
- `scan_started_at` (ISO 8601 string, UTC).
- `scan_completed_at` (ISO 8601 string, UTC).
- `files` (array): list of per‑file scan results.
- `summary` (object, optional): aggregate information (counts, timings).

Example:

```json
{
  "json_schema_version": 1,
  "project_root": "/Users/alice/Pictures",
  "schema_version": "2",
  "scan_started_at": "2025-03-20T10:00:00Z",
  "scan_completed_at": "2025-03-20T10:03:12Z",
  "files": [ /* per-file objects, see below */ ],
  "summary": {
    "total_files": 1234,
    "scanned_files": 1100,
    "skipped_files": 134,
    "duplicate_groups": 42
  }
}
```

### Per‑File Object

Each entry in `files` has the following shape:

- `path` (string): path to the file. Typically project‑relative, but UIs must
  be prepared for absolute paths.
- `status` (string, optional): high‑level status, aligned with the `status`
  column in the `files` table (e.g., `"ok"`, `"skipped_invalid_mime"`,
  `"error_reading"`).
- `group_id` (integer or null, optional): foreign key to a row in `groups`
  (time‑based burst, near‑duplicate cluster, etc.).
- `metrics` (object): map from `metric_name` to an object with `value_real`
  and `value_text`, mirroring `AnalyzerResult`.

Example:

```json
{
  "path": "2025/party/img_0001.heic",
  "status": "ok",
  "group_id": 7,
  "metrics": {
    "blur_score":      { "value_real": 0.12, "value_text": null },
    "brightness_score":{ "value_real": 0.64, "value_text": null },
    "phash":           { "value_real": null, "value_text": "ff00aa55cc33dd99" }
  }
}
```

### Summary Object (Optional)

The `summary` section is optional but recommended:

- `total_files` (integer): number of filesystem entries considered.
- `scanned_files` (integer): files that passed MIME and other gates.
- `skipped_files` (integer): files skipped due to unsupported type, errors, etc.
- `duplicate_groups` (integer): number of groups that contain more than one file.

Additional fields may be added in later versions as **optional** keys.

### Versioning Rules

- `json_schema_version` starts at `1`.
- Future changes must be **additive**:
  - New optional top‑level fields are allowed.
  - New optional per‑file fields are allowed.
  - New optional keys in `summary` are allowed.
- Existing fields must not change meaning or type without a new major schema
  version and a corresponding migration plan.

