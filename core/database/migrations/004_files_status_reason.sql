-- Migration 004: Why a file was skipped (e.g. too_large, decode_failed)
-- migration: Nullable files.status_reason for load_failed files

ALTER TABLE files ADD COLUMN status_reason TEXT;
