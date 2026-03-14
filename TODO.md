# ✅ Project TODO

## 🏗 Sprint 0: Foundation

### 1. Decisions First (must be resolved before ANY code is written)
- [x] **Research and Decide:** SQLite via raw `sqlite3` or `SQLAlchemy` (document choice in docs/).
- [x] **Decide tool for structured logging.** The UI must be able to parse the log stream for real-time progress. Consider `loguru` for its structured logging and ease of use.
- [x] **Decide framework for CLI.** Should we use **`typer`** (preferred) or `click`.
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
- [ ] **Database:** Extend SQLite schema to store `file_path`, `hash`, `blur_score`, `brightness_score`.
- [ ] **Schema version wiring:** Update `schema_version` table (e.g., to `v2` or apply migration).
- [ ] **DAO metrics:** Add `insert_metric(conn, file_id, metric_name, value_real, value_text)` (or upsert) in dao.py. All analyzer output is persisted via this method.

### 3. Infrastructure & Pre-processing (The Loader phase)
- [ ] **Format Support:** Add basic JPG/PNG + **HEIC** support (essential for iPhone photos).
- [ ] **MIME validation gate:** Call `core/utils/mime.py` at the start of every scan. Reject files that fail magic byte validation and log rejection to SQLite `status`.
- [ ] **EXIF orientation:** Implement auto-orientation in `core/utils/exif.py`. Read EXIF orientation tag and rotate/flip image data before passing to any analyzer.
- [ ] **High-Perf Image Loader:** Implement threaded/multiprocess image loading (using `ProcessPoolExecutor`).
- [ ] **Brain/Brawn pipeline:** Implement scan orchestration: Brain handles file-walking, I/O, and batch DB writes; Brawn (ProcessPoolExecutor) runs image loading and analyzers. Pass Path objects; never raw bytes between processes.
- [ ] **Image load safety:** Verify image dimensions and file size before decode to prevent decompression bombs (per AGENTS.md). Reject and log oversized images.
- [ ] **Path scope safety:** Ensure all scanned file paths stay within the scan folder root. Use Path.resolve(); reject or skip symlinks/paths that escape project scope.
- [ ] **Benchmark Set:** Create a 'Ground Truth' folder with 10 blurry and 10 sharp photos to test algorithm accuracy locally.
- [ ] **Test project structure:** Create two directories: (1) `tests/fixtures/images/` — committed basic images for unit tests; (2) `.local-photos/` — gitignored directory for real photo testing/training. Add `.local-photos/*` and `!.local-photos/.gitkeep` to .gitignore. Create `.local-photos/.gitkeep`. Document both in README or docs.

### 4. Core Analyzers (The Compute phase)
- [ ] **Normalization Logic:** Implement utilities to normalize all metrics to comparable scales (0–1).
- [ ] **Blur Analyzer:** Laplacian Variance. Stable across resolutions, normalized to 0–1.
- [ ] **Exposure Analyzer:** RMS Contrast & Mean Brightness.
- [ ] **Duplicates Analyzer:** Perceptual Hashing (pHash) to find near-matches.
- [ ] **Analyzer tests:** Each analyzer (Blur, Exposure, Duplicates) must have 4-category tests: happy path, corrupted (truncated/zero-byte), invalid type (non-image), edge cases (1x1 px, extreme aspect ratio). Per AGENTS.md Technical Standards.

### 5. Post-Processing (Grouping & Caching)
- [ ] **Grouping Logic:** Algorithm to group photos by time-window (e.g., "bursts" within 5 seconds). Uses EXIF time if available, file mtime as fallback.
- [ ] **Thumbnailer:** Generate and cache 300px thumbnails locally.

### 6. CLI Integration & Resilience
- [ ] **CLI scan command:** Create `cli.py scan --folder ~/Pictures`.
- [ ] **Deterministic scan mode:** Fixed seeds, stable ordering.
- [ ] **Error handling:** Gracefully skip unreadable/corrupted images and log reason.
- [ ] **Interrupt handling:** Handle Ctrl+C to end scan gracefully, close DB connection, and write correct output to stdout/stderr.

### 7. Verification
- [ ] **Sprint 1 success check:**
  - Scan 1k photos < 5 minutes.
  - Blur ranking correctly surfaces worst 10 images in the Benchmark Set.
  - Duplicate groups are stable across runs.


## 🧠 Sprint 2: The Smart Perception (AI & Aesthetic Scoring)
- [ ] **Face Analysis:** Integrate MediaPipe to detect faces, count them, and check for "Eyes Open" (EAR).
- [ ] **Aesthetic Backbone:** Integrate **CLIP** (via ONNX) to extract image embeddings.
- [ ] **The "Best of" Logic:** Logic to auto-flag the 1-2 "Keepers" within a time-based group.
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


## Ongoing
- [ ] Keep TODO aligned with actual code structure
- [ ] Move completed tasks into CHANGELOG or release notes
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
1) **Pairwise ranking** (recommended): show A vs B from the same burst/scene and pick the better one.
2) **Keep/Discard**: mark photos you would keep.

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
