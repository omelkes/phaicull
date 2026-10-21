# ✅ Project TODO

## 🏗 Sprint 0: Foundation

### 1. Decisions First (must be resolved before ANY code is written)

- [x] **Research and Decide:** SQLite via raw `sqlite3` or `SQLAlchemy` (document choice in docs/).
- [x] **Decide tool for structured logging.** The UI must be able to parse the log stream for real-time progress. Consider `loguru` for its structured logging and ease of use.
- [x] **Decide framework for CLI.** Should we use `typer` (preferred) or `click`.
- [x] **Decide Migration Strategy:** Decide how SQLite schema versioning and migrations will be handled (e.g., custom lightweight script vs. Alembic).
- [x] **Decision outputs:** All decisions above must produce a written record in `docs/decisions.md`.
- [x] **Architecture decision record (ADR-001):**
  - CLI-first execution model
  - SQLite default DB
  - Offline-first, plugin-based AI
  - Define contracts for UI integration (JSON output, progress reporting, DB schema)



### 2. Environment & Structure

- [x] **Environment:** Initialize Python 3.12 environment with `pyproject.toml`.
- [x] **Structure:** Create correct directory structure (see AGENTS.md). Setup `.gitignore`.
- [x] **Directory initialization:** Create `.models/.gitkeep` and `.projects/.gitkeep` so git-ignored directories exist in the repo without committing real content.



### 3. Database Foundation

- [x] **Schema Versioning implementation:** Implement the chosen migration strategy. Include a `schema_version` table seeded with `v1` in the initial setup.
- [x] **Persistence Scaffold:** Design & implement the base SQLite schema (Tables: `files`, `metrics`, `groups`, `projects`).
  - Project DB: `{project}/phaicull/phaicull.db` — tables `files`, `metrics`, `groups`. Registry DB: `.projects/registry.db` — table `projects`.



### 4. Shared Utilities & Testing (Depends on DB)

- [x] **Test infrastructure:** Create `tests/conftest.py` with shared pytest fixtures: synthetic valid image, zero-byte file, non-image file, extreme aspect ratio image, and a temp SQLite DB factory.
- [x] **MIME validation utility:** Implement `core/utils/mime.py` — magic byte checker for supported image types. 
- [x] **BaseAnalyzer scaffold:** Create `core/analyzers/base.py` with the abstract `BaseAnalyzer` class, input/output type contracts, and docstring.



### 5. Config & CLI

- [x] **Config system:** (YAML or TOML) to handle: thresholds (blur, brightness), burst window, and enable/disable heavy features.
- [x] **CLI Scaffold:** Create `cli.py` entry point with `rich` for terminal output.



## ⚙️ Sprint 1: Core Analyzer (The Junk Filter)



### 1. Contracts & Decisions First

- [x] **BaseAnalyzer wiring:** Confirm all Sprint 1 analyzers (Blur, Exposure, pHash) inherit from `BaseAnalyzer` before implementation begins. See `core/analyzers/blur.py`, `core/analyzers/exposure.py`, `core/analyzers/duplicates.py`, and `core/analyzers/__init__.py#get_sprint1_analyzers`, plus `docs/analyzers_sprint1.md`.
- [x] **JSON Contract:** Document the exact JSON structure the UI will expect from a scan. See `docs/json_contract_scan_v1.md`.
- [x] **Feature logging contract:** Define exact feature vector saved per image and version the feature schema (e.g., v1). See `docs/features_schema_v1.md`.
- [x] **Thumbnail Strategy:** Decide if thumbnails are stored as BLOBs in SQLite or as files in a `.cache` folder (Recommendation: `.cache` folder for DB performance). See `docs/thumbnails.md`.
- [x] **Progress Reporting Contract:** Decide standard way (stdout or status table in DB) to report % completion for UI progress bars. See `docs/progress_contract.md`.



### 2. Database Update

- [x] **Database:** Extend SQLite schema to store `file_path`, `hash`, `blur_score`, `brightness_score`. Schema 002 already supports these via `files` (file_path, content_hash) and `metrics` (generic key-value). Migration 003 adds `idx_metrics_metric_name`.
- [x] **Schema version wiring:** Update `schema_version` table (e.g., to `v2` or apply migration). Migration 003 bumps version to "003" via existing runner.
- [x] **DAO metrics:** Add `insert_metric(conn, file_id, metric_name, value_real, value_text)` (or upsert) in dao.py. All analyzer output is persisted via this method.



### 3. Infrastructure & Pre-processing (The Loader phase)

- [x] **Decode on test environment:** how to handle database? Clear after each test run or use in-memory database or cleanup on demmand? Resarch and decide overall testing strategy for the project.
- [x] **Test project structure:** Create two directories: (1) `tests/fixtures/images/` — committed basic images for unit tests; (2) `.local-photos/` — gitignored directory for real photo testing/training. Add `.local-photos/`* and `!.local-photos/.gitkeep` to .gitignore. Create `.local-photos/.gitkeep`. Document both in README or docs. 
- [x] **Format Support:** Add basic JPG/PNG + **HEIC** support (essential for iPhone photos). Runtime deps: `pillow`, `pillow-heif`, `opencv-python-headless`, `numpy`. HEIC registered via `pillow_heif.register_heif_opener()`. See `core/loader/image_loader.py`.
- [x] **MIME validation gate:** Call `core/utils/mime.py` at the start of every scan. Reject files that fail magic byte validation and log rejection to SQLite `status`. Wired into `core/scanner/walker.py` via `is_supported_image()`.
- [x] **EXIF orientation:** Implement auto-orientation in `core/utils/exif.py`. Read EXIF orientation tag and rotate/flip image data before passing to any analyzer. Uses `PIL.ImageOps.exif_transpose()`.
- [x] **High-Perf Image Loader:** Implement threaded/multiprocess image loading (using `ProcessPoolExecutor`). See `core/scanner/pipeline.py` (Brain dispatches to Brawn via `loop.run_in_executor`).
- [x] **Brain/Brawn pipeline:** Implement scan orchestration: Brain handles file-walking, I/O, and batch DB writes; Brawn (ProcessPoolExecutor) runs image loading and analyzers. Pass Path objects; never raw bytes between processes. See `core/scanner/` package.
- [x] **Image load safety:** Verify image dimensions and file size before decode to prevent decompression bombs (per AGENTS.md). Reject and log oversized images. Config: `loader.max_file_size_mb`, `loader.max_image_dimension`. See `core/loader/image_loader.py`.
- [x] **Path scope safety:** Ensure all scanned file paths stay within the scan folder root. Use Path.resolve(); reject or skip symlinks/paths that escape project scope. See `core/utils/path_safety.py`.
- [x] **Benchmark Set:** Create a 'Ground Truth' folder with 10 blurry and 10 sharp photos to test algorithm accuracy locally. Convention: `.local-photos/benchmark/blurry/` and `.../sharp/`. See `docs/testing_strategy.md`.



### 4. Core Analyzers (The Compute phase)

- [x] **Normalization Logic:** Implement utilities to normalize all metrics to comparable scales (0–1). See `core/utils/normalization.py`: `clamp01`, `linear_norm` (bounded metrics), `log_norm` (wide-dynamic-range metrics). Per-image deterministic (no dataset-relative scaling — keeps analyzers idempotent); NaN/inf → None (NULL metric).
- [x] **Blur Analyzer:** Laplacian Variance. Stable across resolutions (downscaled to 1024px working size), log-normalized to 0–1 (lower = blurrier). Calibration constants `_VAR_LO=5, _VAR_HI=2000` are provisional — tune against benchmark set in Verification.
- [x] **Exposure Analyzer:** Mean brightness, linearly normalized to 0–1 (0 = black, 1 = white); thresholds.brightness_min/max apply directly.
- [x] **Contrast Analyzer:** RMS contrast as separate `contrast_score` metric (one analyzer = one metric per AGENTS.md; split out of the original Exposure item). Grayscale std, `linear_norm(std, 0, 127.5)` — 0 = flat, 1 = theoretical uint8 max.
- [x] **Duplicates Analyzer:** Perceptual Hashing (pHash) to find near-matches. DCT-based via OpenCV (no new dependency); AC-median convention (brightness-shift robust); 64-bit hash as 16-char hex in `value_text`. Hamming-distance grouping is `[docs/plan/sprint1-grouping.md](docs/plan/sprint1-grouping.md)`.
- [x] **Analyzer tests:** Each analyzer (Blur, Exposure, Contrast, Duplicates) has 4-category tests: happy path, corrupted (truncated/zero-byte), invalid type (non-image), edge cases (1x1 px, extreme aspect ratio). Corrupted/invalid files are gated by the loader — verified end-to-end through the Brawn worker in each analyzer's test file.



### 5. Post-Processing (Grouping & Caching)

- [x] **Grouping Logic:** Visual near-duplicate clusters via pHash Hamming (not time), run at the end of every scan. Activity/scene groups wait for embeddings. Contract: `[docs/grouping.md](docs/grouping.md)`; DEC-009; plan: `[docs/plan/sprint1-grouping.md](docs/plan/sprint1-grouping.md)`.
- [x] **Thumbnailer:** 300px JPEG thumbnails at `phaicull/thumbs/thumb_<id>.jpg`, generated during each scan from the already-decoded image (no second decode). See `core/utils/thumbnail.py` and `[docs/thumbnails.md](docs/thumbnails.md)`.



### 6. CLI Integration & Resilience

Plan for this section: [`docs/plan/sprint1-cli-resilience.md`](docs/plan/sprint1-cli-resilience.md).

- [x] **CLI scan command:** `phaicull scan <folder> [--config]` (positional folder; no `--folder` flag).
- [x] **Deterministic scan mode:** Results are written in sorted discovery order, so the same folder gets the same `files.id` / `thumb_<id>.jpg` for any worker count. Fixed seeds: none needed (no randomness in Sprint 1 analyzers or grouping).
- [x] **Error handling:** Unreadable/corrupted images are skipped (`status=load_failed`), the reason is logged (WARNING) and stored in `files.status_reason`; the CLI summary lists failures by reason. **Migration 004** adds the nullable column (additive; old rows read NULL). DEC-010.
- [x] **Interrupt handling:** Ctrl+C keeps committed batches, rolls back the partial batch (and its new thumbnails), cancels queued files, skips grouping, prints "Scan interrupted" to stderr and exits 130. Workers ignore SIGINT; repeated Ctrl+C (or `uv run` forwarding) cannot abort cleanup. Verified end-to-end with `uv run` on 400 photos.



### 7. Verification

Plan for this section: [`docs/plan/sprint1-verification.md`](docs/plan/sprint1-verification.md).

- [x] **Sprint 1 success check** — `scripts/verify_sprint1.py run` (final run 2026-10-21, exit 0, 6 CPUs; details in the plan):
  - [x] Scan 1k photos < 5 minutes — 168.2 s for 1000 generated 12 MP JPEGs.
  - [x] Duplicate groups are stable across runs — 100 groups, identical membership in both scans (all 100 planted near-duplicates found).
  - [x] Blur ranking correctly surfaces worst 10 images in the Benchmark Set — real photos (14 blurry, 10 sharp): 10/10. Separation is not perfect: 3 blurry photos and 1 motion-blur photo of busy scenes score above some sharp ones (Laplacian variance depends on scene content) → Sprint 2+ blur model.



## 🧠 Sprint 2: The Smart Perception (AI & Aesthetic Scoring)

- [ ] **Face Analysis:** Integrate MediaPipe to detect faces, count them, and check for "Eyes Open" (EAR).
- [ ] **Aesthetic Backbone:** Integrate **CLIP** (via ONNX) to extract image embeddings. This is also the signal for activity/scene grouping (karts vs butterfly); see `[docs/plan/sprint1-grouping.md](docs/plan/sprint1-grouping.md)`.
- [ ] **The "Best of" Logic:** Logic to auto-flag the 1-2 "Keepers" within a visual / activity group.
- [ ] **CLI Finalization:** `culler.py scan --report` (Output a JSON summary of "Keep vs Junk").



## 💡 Sprint 3: The Brain Training and experiment (AI fine tuning learning phase)

Sprint 3 is experimental and may be partially abandoned without blocking the product.
Try and decide the best result

- [ ] **Dataset Curation:** Create a small test set of "Good" vs "Bad" family photos for internal benchmarking.
- [ ] **Aesthetic Scorer:** Research/Train a lightweight MLP (Multi-Layer Perceptron) that maps CLIP embeddings to an "Aesthetic Score."
- [ ] **Scoring Engine:** 
  - [ ] Implement the "Heuristic Scorer" (Weights: Focus + Eyes Open + Smile).
  - [ ] Implement the "Aesthetic Scorer" (Small MLP/Linear model on top of CLIP).
- [ ] **Face Analysis:** Integrate MediaPipe for "Face Mesh" to detect:
  - [ ] Eye closure (EAR - Eye Aspect Ratio).
  - [ ] Smile detection (Mouth curvature).
  - [ ] Expression signals (eye openness, mouth state – experimental)
- [ ] **Model Export:** Convert models to ONNX format for high-speed cross-platform execution (CoreML on Mac, DirectML/ONNX on Windows).

- 



## 🖼 Sprint 4: Native UI (The Viewer)

- **Data Protocol:** Establish the "Watcher" pattern (UI reads SQLite as the Python CLI populates it).

- [ ] **macOS (SwiftUI):** 
  - [ ] Watcher for CLI output and SQLite changes
  - [ ] Grid View using lazy loading for thumbnails.
  - [ ] Detail View with "Metrics Overlay."
  - [ ] Filtering for different score
  - [ ] **Manual Keeper Selection** User should be override AI decision about selected photo.   
  - [ ] **Interaction:** Keyboard shortcuts for "Keep (K)" / "Discard (X)".
- [ ] **Windows (.NET 8 / WinUI 3):**
  - [ ] Watcher for CLI output and SQLite changes
  - [ ] Grid View using lazy loading for thumbnails.
  - [ ] Detail View with "Metrics Overlay."
  - [ ] Filtering for different score
  - [ ] **Manual Keeper Selection** User should be override AI decision about selected photo.   
  - [ ] **Interaction:** Keyboard shortcuts for "Keep (K)" / "Discard (X)".
- [ ] **Packaging:** Research and setup PyInstaller or Nuitka to bundle the Python core as a standalone executable for the macOS/Windows installers.



## 🚀 Sprint 5: Refinement & Active Learning

- [ ] **Export Workflow:** "Move Discarded to Trash" or "Copy Keepers to Folder" functionality.
- [ ] **User Feedback Loop:** Store user "overrides" in SQLite (if user keeps a photo AI hated).
- [ ] **Personalization:** Basic script to re-train the Aesthetic Scorer based on user's local "Keep" history.
- [ ] **RAW Support:** Integrate `rawpy` for professional camera support.



## 🐞 Bugs / Tech Debt (found during 2026-07-03 code review — ALL FIXED 2026-07-03)

- [x] **Analyzer errors not counted:** `FileResult.analyzer_errors` now records analyzers that raise; pipeline sums into `ScanSummary.analyzer_errors`; CLI displays it.
- [x] `skipped_mime` **never incremented:** `discover_files()` now returns `DiscoveryResult(valid, rejected_mime)`; MIME-rejected files get a `files` row with status `skipped_invalid_mime` (per JSON contract) and are counted in `ScanSummary.skipped_mime`. Walker also excludes the project's own `phaicull/` data dir from scans (prevents the DB recording itself on rescan).
- [x] **Rescan wipes** `group_id`**:** `insert_file()` upsert now uses `COALESCE(excluded.group_id, files.group_id)` — rescans (group_id=None) preserve grouping; explicit non-NULL still updates.
- [x] **Double-decode design flaw:** Analyzer contract v2 — `analyze(image: np.ndarray, path: Path)`. Worker decodes once and shares the array. Decision recorded as DEC-007 in `docs/decisions.md` (changed while all analyzers were stubs; no migration needed).
- [x] **Worker pool size hardcoded:** now `os.cpu_count()` by default, overridable via `[scanner] max_workers` in phaicull.toml.
- [x] **Supported-format mismatch:** decided to keep GIF/WebP (DEC-008); README and loader docs updated to list JPEG/PNG/HEIC/GIF/WebP.
- [x] **No linter/type-checker/CI:** added `ruff` + `mypy --strict` (dev deps, config in pyproject.toml) and `.github/workflows/ci.yml` (ruff + mypy + pytest). Both pass clean on `core/`.



## Ongoing

- [ ] Keep TODO aligned with actual code structure. Detailed plans live in `[docs/plan/](docs/plan/README.md)`; TODO stays a checklist.
- [ ] Move completed tasks into CHANGELOG or release notes
- [ ] **Rows for moved/deleted files are never removed:** a rescan keeps `files` rows (status `ok`, metrics, groups, thumbnails) for files no longer on disk, so they still show up as photos. Needs a "missing" status or pruning step (schema/contract decision). Found 2026-10-21 (Sprint 1 verification, after re-sorting the benchmark).
- [ ] **Orphan thumbnails after a hard kill:** a SIGKILL between thumbnail rename and batch commit can leave `thumb_<id>.jpg` with no row (upsert advances AUTOINCREMENT, so the id is not reliably reused). Consider sweeping `thumbs/` for ids not in `files` at scan start. Found 2026-10-11 (Sprint 1 §6).
- [ ] **Schema pragmatism:** start denormalized, refactor after Sprints if needed
- [x] Fix `schema_version` numeric ordering bug in migrations (TEXT vs integer ordering)

---



## 🧭 DESIGN NOTES (for humans + AI agents)

The following section is NOT a task list.
It documents how to think about photo quality, ranking, and training.
It exists to guide future implementation and AI-assisted development.

## Training a “Best Photo” Model (broad plan)

The goal is not “beauty”. It’s **pick the best family shot**: sharp faces, open eyes, good exposure, low noise, pleasant moment.

### Step 0: Start with a strong baseline (no training)

- Use deterministic metrics + face/eyes signals as inputs
- Add simple heuristics per use case (kids photos):
  - prefer photos with faces
  - prefer open eyes / non-blinking
  - prefer higher sharpness on faces (not background)
  - avoid extreme highlights/shadows



### Step 1: Collect training data (privacy-friendly)

Two practical labeling strategies:

1. **Pairwise ranking** (recommended): show A vs B from the same burst/scene and pick the better one.
2. **Keep/Discard**: mark photos you would keep.

Pairwise labels are easier and more consistent than absolute 1–10 scores.

Where to get examples:

- your own family sets (local)
- opt-in community dataset (only if contributors agree)
- synthetic “bad” augmentations: blur, noise, exposure shifts (to teach robustness)



### Step 2: Represent images (features)

Tiered feature approach:

- **Fast features**: blur/brightness/noise/resolution + EXIF + face count
- **Deep features** (later): CLIP embeddings or a lightweight vision backbone
- **Face-focused features**: crop faces and embed them; score sharpness/eyes on face crops



### Step 3: Train the model (simple first)

Start small and interpretable:

- **Learning-to-rank** model (pairwise):
  - inputs: feature vectors (fast + deep embeddings)
  - model: Logistic Regression / XGBoost / small MLP
  - loss: pairwise (Bradley–Terry / RankNet style)

This produces a “preference score” that is excellent for burst selection.

### Step 4: Evaluate realistically

- Evaluate per **photo series** (burst/group), not only per-image
- Metrics: Top-1 accuracy in burst, Top-k hit rate, and “regret” (how often the chosen photo is worse)
- Keep a small “gold set” of your curated albums for regression tests



### Step 5: Ship as a plugin (offline default)

- Ship a small default model file with the app
- Provide a **plugin interface** so users can swap models (local) or optionally use cloud
- Optional future: personal fine-tuning on-device (never uploading photos)



### Step 6: Active learning loop (the secret sauce)

- When user overrides a choice (keeps a photo we’d discard), store that as a new label
- Periodically retrain a personal model (optional)

