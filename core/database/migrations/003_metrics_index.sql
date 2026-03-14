-- Migration 003: Index on metrics(metric_name) for filter queries
-- migration: Index for metric_name to support queries filtering by metric (e.g. blur_score)

CREATE INDEX IF NOT EXISTS idx_metrics_metric_name ON metrics(metric_name);
