-- Migration 001: Registry database (list of projects)
-- migration: Registry schema_version and projects table
-- Registry DB lives in Phaicull install dir (e.g. .projects/registry.db). One DB for all projects.

CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Projects: one row per known project (photo directory). Path = absolute path to project root.
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    name TEXT,
    added_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path);
