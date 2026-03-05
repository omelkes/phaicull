-- Migration 002: Project database base schema (files, metrics, groups)
-- migration: Base tables for per-project file and metric storage
-- Project DB lives at {project}/phaicull/phaicull.db. Registry (list of projects) is separate.

-- Groups: e.g. time-based burst groups. One row per group.
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Files: one row per file in the project. Path is project-relative or absolute per consumer.
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    content_hash TEXT,
    status TEXT,
    group_id INTEGER REFERENCES groups(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_files_group_id ON files(group_id);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);

-- Metrics: key-value per file. Nullable; partial scans supported.
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    value_real REAL,
    value_text TEXT,
    UNIQUE(file_id, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_metrics_file_id ON metrics(file_id);
