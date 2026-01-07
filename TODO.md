# ✅ Project TODO

## 🏗 Sprint 0: Foundation
- [ ] **Environment:** Initialize Python 3.12 environment with `pyproject.toml`.
- [ ] **Structure:** Create correct directory sctructure, see AgentsMd. Setup .gitignore-
- [ ] **Research and Decide:** SQLite via raw sqlite3 or SQLAlchemy (document choice in docs/)
- [ ] **DB schema versioning:** Implement lightweight migration strategy
- [ ] **Persistence:** Design & implement SQLite schema (Tables: `files`, `metrics`, `groups`, `projects`).
- [ ] **CLI Scaffold:** Create `culler.py` entry point with `rich` for beautiful terminal output.
- [ ] **Config system:** (YAML or TOML):
  - thresholds (blur, brightness)
  - burst window
  - enable/disable heavy features
- [ ] **Architecture decision record (ADR-001):**
  - CLI-first execution model
  - SQLite default DB
  - Offline-first, plugin-based AI

## ⚙️ Sprint 1: Core Analyzer (The Junk Filter)
- [ ] **Benchmark Set:** Create a 'Ground Truth' folder with 10 blurry and 10 sharp photos to test algorithm accuracy during development.
- [ ] **Database:** Create SQLite schema to store `file_path`, `hash`, `blur_score`, `brightness_score`.
- [ ] **CLI:** Create `culler.py scan --folder ~/Pictures` command.
- [ ] **High-Perf Image Loader:** Implement image loading (using `ProcessPoolExecutor`).
- [ ] **Format Support:** Basic JPG/PNG + **HEIC** (essential for iPhone photos).
- [ ] **CV Modules:**
    - [ ] **Normalization**: Normalize all metrics to comparable scales (0–1)
    - [ ] **Blur:** Laplacian Variance.  Acceptable: stable across resolutions, normalized to 0–1
    - [ ] **Exposure:** RMS Contrast & Mean Brightness.
    - [ ] **Duplicates:** Perceptual Hashing (pHash) to find near-matches.
- [ ] **Error handling:** gracefully skip unreadable/corrupted images and log reason
- [ ] **Interrupt handling:** end scan gracefully, close DB connection, write correct output to stdio or stderr
- [ ] **Grouping Logic:** Algorithm to group photos by time-window (e.g., "bursts" within 5 seconds).
   - uses EXIF time if available, file mtime as fallback
- [ ] **Thumbnail Strategy:** Decide if thumbnails are stored as BLOBs in SQLite or as hidden files in a .culler_cache folder (Recommendation: .cache folder for DB performance).
- [ ] **Thumbnailer:** Generate and cache 300px thumbnails (needed for future UI speed).
- [ ] **Deterministic scan mode:** fixed seeds, stable ordering
- [ ] **JSON Contract:** Document the JSON structure the UI will expect from a scan.
- [ ] **Progress Reporting:** Implement a standard way (stdout or status table in DB) to report % completion for the UI progress bars.
- [ ] **Feature logging contract:**
  - define exact feature vector saved per image
  - version feature schema (v1, v2)
- [ ] **Sprint 1 success check:**
  - scan 1k photos < 5 minutes
  - blur ranking correctly surfaces worst 10 images
  - duplicate groups are stable across runs

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
    - [ ]  Eye closure (EAR - Eye Aspect Ratio).
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
