## Feature Schema v1

This document defines the **v1 feature vector** stored and/or derived from
Sprint 1 analyzers.

- Version: `features_schema_version = 1`
- Backed by the `metrics` table (`metric_name`, `value_real`, `value_text`)
  and aligned with the JSON scan contract.

### Feature List

| Feature name       | Type   | Source analyzer     | Interpretation                                      |
|--------------------|--------|---------------------|-----------------------------------------------------|
| `blur_score`       | float  | `BlurAnalyzer`      | Normalized blur measure; lower = blurrier image    |
| `brightness_score` | float  | `ExposureAnalyzer`  | Normalized brightness / exposure score             |
| `phash`            | string | `DuplicatesAnalyzer`| Perceptual hash used for duplicate detection       |

### Storage Mapping

- In SQLite (`metrics` table):
  - `metric_name` is one of the feature names above.
  - `value_real` holds numeric values (`blur_score`, `brightness_score`).
  - `value_text` holds string values (`phash`).

- In JSON (`docs/json_contract_scan_v1.md`):
  - Features appear under `file.metrics[metric_name]` with the same semantics.

### Versioning Rules

- New features may be added in future versions as additional `metric_name`
  values, provided they are **optional** and do not break existing consumers.
- Changes to the meaning or type of existing features require a new
  `features_schema_version` and coordination with UI/DB consumers.

