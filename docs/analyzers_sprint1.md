## Sprint 1 Analyzers and Metrics

This document defines the concrete analyzers for **Sprint 1** and their
stable metric identifiers. These names are used consistently across:

- SQLite `metrics` table (`metric_name` column).
- JSON scan output.
- Feature vector schema.

Per `AGENTS.md`, each analyzer:

- Inherits from `BaseAnalyzer`.
- Computes exactly **one** metric.
- Is idempotent and safe to re-run.

### Analyzer → Metric Mapping

- **BlurAnalyzer**  
  - Module: `core/analyzers/blur.py`  
  - Metric name: `blur_score`  
  - Type: numeric (`value_real` in `AnalyzerResult`)  
  - Range (normalized in later work): \[0, 1], where lower values indicate blurrier images.

- **ExposureAnalyzer**  
  - Module: `core/analyzers/exposure.py`  
  - Metric name: `brightness_score`  
  - Type: numeric (`value_real`)  
  - Interpretation: normalized brightness score derived from mean brightness and RMS contrast.

- **DuplicatesAnalyzer**  
  - Module: `core/analyzers/duplicates.py`  
  - Metric name: `phash`  
  - Type: text (`value_text`)  
  - Interpretation: perceptual hash (e.g., 64‑bit encoded as hex string) used to detect near-duplicate images.

### Usage Notes

- All analyzers return an `AnalyzerResult` with the `metric_name` fixed to the
  values above; callers must not override these names.
- The same `metric_name` values are used:
  - In the `metrics` table (`metric_name` column) defined by
    `core/database/migrations/002_project_schema.sql`.
  - In the JSON scan contract (`docs/json_contract_scan_v1.md`).
  - In the feature schema (`docs/features_schema_v1.md`).

