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
- Receives the **decoded BGR image array** plus source `Path` (contract v2,
  DEC-007 in `docs/decisions.md`): the Brawn worker decodes each file once and
  shares the array with all analyzers. Analyzers must not re-decode from disk
  or mutate the shared array.

### Analyzer → Metric Mapping

- **BlurAnalyzer**  
  - Module: `core/analyzers/blur.py`  
  - Metric name: `blur_score`  
  - Type: numeric (`value_real` in `AnalyzerResult`)  
  - Range: \[0, 1], where lower values indicate blurrier images.  
  - Computation: grayscale → downscale to 1024px working size (resolution
    stability) → Laplacian variance → `log_norm(var, 5, 2000)`. Calibration
    constants are provisional pending benchmark validation.

- **ExposureAnalyzer**  
  - Module: `core/analyzers/exposure.py`  
  - Metric name: `brightness_score`  
  - Type: numeric (`value_real`)  
  - Interpretation: mean grayscale brightness, `linear_norm(mean, 0, 255)` —
    0 = black, 1 = white. Config `thresholds.brightness_min/max` flag too-dark
    and blown-out images directly. RMS contrast is a separate future metric
    (`contrast_score`, see TODO).

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

