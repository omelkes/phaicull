## Progress Reporting Contract

This document defines the **progress event schema** emitted by the CLI during
scans, for consumption by UIs.

- Logging library: `loguru` (see DEC-002 in `docs/decisions.md`).
- Transport: JSON lines (one JSON object per log line) on stdout or a
  dedicated progress stream, depending on CLI configuration.

### Event Types

Minimum required events:

- `progress` — ongoing scan progress.

Recommended additional events:

- `start` — scan has begun.
- `end` — scan has finished (successfully or with errors).
- `error` — non-fatal error that the UI may want to surface.

### Common Fields

All events share these fields:

- `event` (string): `"start"`, `"progress"`, `"end"`, or `"error"`.
- `timestamp` (ISO 8601 string, UTC): when the event was emitted.

### `progress` Event

Fields:

- `event`: `"progress"`.
- `timestamp`: ISO 8601 timestamp.
- `percent` (float): 0.0–100.0, approximate completion percentage.
- `processed` (integer): number of files processed so far.
- `total` (integer): total number of files discovered in the scan.
- `current_file` (string, optional): path of the file currently being processed.

Example:

```json
{
  "event": "progress",
  "timestamp": "2025-03-20T10:01:23Z",
  "percent": 42.5,
  "processed": 425,
  "total": 1000,
  "current_file": "2025/party/img_0001.heic"
}
```

### `start` Event

Fields:

- `event`: `"start"`.
- `timestamp`: ISO 8601 timestamp.
- `project_root` (string): absolute path to the folder being scanned.

Example:

```json
{
  "event": "start",
  "timestamp": "2025-03-20T10:00:00Z",
  "project_root": "/Users/alice/Pictures"
}
```

### `end` Event

Fields:

- `event`: `"end"`.
- `timestamp`: ISO 8601 timestamp.
- `project_root` (string).
- `duration_seconds` (float, optional): total scan duration.
- `status` (string): `"ok"` or `"error"`.

### `error` Event

Fields:

- `event`: `"error"`.
- `timestamp`: ISO 8601 timestamp.
- `message` (string): human-readable message.
- `exception` (string, optional): serialized exception information.
- `file` (string, optional): path associated with the error, if any.

### CLI Flags (Future Work)

The CLI should eventually support flags to control progress output style, e.g.:

- `--progress-json`: emit JSON events as described here.
- `--quiet`: suppress human-readable progress while still emitting JSON.

Sprint 1 only **documents** this contract; wiring loguru sinks and CLI flags
can be implemented under separate TODO items.

