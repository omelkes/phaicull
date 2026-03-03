-- Migration 001: Initial schema versioning
-- migration: Initial schema_version table with version, description, applied_at
-- Per DEC-004: custom lightweight migration strategy.
-- Table stores history of all applied migrations for audit and recovery.

CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
