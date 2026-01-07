# 🤖 Agent Instructions (Project Context)

You are an AI Engineering Partner for **Phaicull**. Follow these rules when generating code or architectural advice:

## All tools mentioned in this file are preferred, not mandatory unless explicitly stated

### AI Output Expectations
When generating code:
- Prefer small, composable modules over large files
- Show the public interface first (class/method signatures)
- Avoid speculative features not listed in TODO
- If uncertain, ask before inventing new abstractions

### Terminology
- Analyzer: a module computing exactly one metric
- Scan: a run over files that may compute only a subset of metrics
- Project: a directory with a single SQLite database
- Base Model: immutable model shipped with Phaicull
- Personal Model: user-trained local model layered on top

### 1. Core Principles
- **Privacy First:** No cloud processing. All models must be local (ONNX, PyTorch, or OpenCV).
- **Speed is a Feature:** Optimize image loading. Use thumbnails. Offload heavy lifting to background threads.
- **CLI-First:** The Python core must remain a standalone, highly functional CLI tool.
- **Each analyzer** must be idempotent and independently runnable. Missing metrics are allowed and represented as NULL until computed.

### 2. Technical Standards
- **Python:** Version 3.12+. Use type hints, `pathlib` for paths, and `pydantic` for JSON schemas.
- **Analyzer Contract:** Every analyzer must inherit from a `BaseAnalyzer` abstract class and implement all required methods. Each analyzer must:
  - declare its output columns
  - declare dependencies (if any)
  - be safe to re-run multiple times
- **Database:** SQLite. Use a clean schema that allows for "partial scans" (e.g., scan blur now, scan faces later). **Requirement:** Enable `PRAGMA journal_mode=WAL;` to allow concurrent readers/writers during multi-process scanning.
  - **Databse migration:** Use simple manual schema versioning or Alembic if complexity increase
- **Architecture:** 
  - `Analyzers`: Modular classes for each metric (Blur, Brightness, etc.).
  - `Storage`: Data Access Object (DAO) pattern for SQLite.
  - `CLI`: Entry point that outputs structured JSON.

### 3. Image Analysis Strategy
1. **Metadata Phase:** Extract EXIF (date, camera, orientation).
2. **Fast Scan Phase:** Laplacian Variance (Blur), Histogram (Brightness), pHash (Duplicates).
3. **Deep Scan Phase (Later):** MediaPipe/YOLO for faces, CLIP for quality scoring.

### 4. AI Training & Model Strategy
- **Embedding-First:** Use CLIP (via `sentence-transformers` or `open_clip`) to generate image embeddings.
- **Lightweight Inference:** For the MVP, use a pre-trained Aesthetic Predictor (MLP or Linear Regression) on top of CLIP embeddings to keep CPU/GPU usage low.
- **Training Pipeline:** 
    - Dataset: Public aesthetic datasets (e.g. AVA) for pretraining only, supplemented by family-style photos and synthetic degradations.
    - Objective: Predict a score from 0.0 to 1.0.
- **Local Learning:** Implement a "User Preference" weight. If a user consistently keeps "candid/blurry" photos, the model should adjust its sensitivity locally using a small SQLite-backed weight matrix.

### 5. Performance & Concurrency
- **Multi-Core Processing:** Use Python’s `multiprocessing` for CPU-bound tasks (Blur, CLIP, OpenCV).
  - **Async I/O:** Use `asyncio` for the main orchestrator to handle DB writes and file-walking without blocking. Async is for orchestration only; all CPU-heavy work must live outside the event loop.
- **Memory Safety (The Golden Rule):** 
  - Never pass raw image bytes (`bytes`) between processes; pass the `Path`.
  - Use **Lazy Loading**: Load the image only when the specific analyzer needs it. 
  - For AI models (CLIP/MediaPipe), process images in batches to optimize GPU/NPU utilization.
  - Always check image dimensions/file size before loading to avoid "Decompression Bomb" crashes.

### 6. Project Features:
- **The CLI** should either accept a `--project-path` flag or automatically detect a `.phaicull` project file in the target directory to know which SQLite database to update. **The  CLI must use standard exit codes** (0 for success, non-zero for failure) in addition to JSON output for easy crash detection in UI.
- **Auto-Orientation:** Before any analysis, use EXIF data to determine the correct orientation. Ensure all coordinate-based results (like face bounding boxes) are relative to the oriented image, not the raw pixel grid. *(Crucial for iPhone photos which are often 'rotated' via metadata).*
- **Logging Standard:** Use a structured logging library (e.g., `loguru` or standard `logging` with a JSON formatter). The UI needs to be able to parse the log stream to show real-time status messages.
- **Thumbnail Strategy:** Thumbnails should be generated once during the 'Fast Scan' and stored in a `.cache/thumbnails` folder (git-ignored) or as BLOBs in the SQLite database to prevent the UI from having to resize 40MB images on the fly.
- **Graceful Shutdown:** Ensure the orchestrator handles `SIGINT` (Ctrl+C) gracefully, ensuring the SQLite connection is closed and the current batch is either committed or safely rolled back.
- **MIME-Type Validation:** Verify file signatures (magic bytes) rather than just extensions before processing to avoid crashing on renamed non-image files.
- **Progress Reporting:** The CLI must implement a `--json-progress` flag that outputs machine-readable percentage updates to `stdout` for the UI to consume.

### 7. Resilience & Error Handling
- **Graceful Failure:** If a file is corrupted, unsupported, or has a read-permission error, the tool must NOT crash. 
- **DB Logging:** Record failures in the SQLite `status` column as `failed` with the error message.
- **Validation:** Use `Pydantic v2` to validate all data before it enters the database or is output as JSON.

### 8. Dependency & Environment
- **Tooling:** Use `uv` (preferred) or `poetry` for lightning-fast dependency resolution and deterministic environments.
- **Portability:** Ensure all AI models are packaged (or auto-downloaded on first run) into a local `.models/` directory within the project root.

### 9. Anti-Patterns (Do NOT do this)
- **Do not** mix UI concerns into the Python core.
- **Do not** introduce a long-running daemon or server for the MVP.
- **Do not** hard-code model paths; use a centralized `ModelRegistry` or environment variables.
- **Do not** perform heavy computation inside the SQLite write-lock. Compute first, then write the results in a batch.
- **Do not** use `os.path`; always use `pathlib.Path` for cross-platform compatibility.
- **Do not** add ML before deterministic metrics are implemented and tested.


### Project Principles
- CLI-first, UI later
- Offline by default
- Fast scan first; tiered analysis later
- Deterministic metrics + tests before ML scoring
- Results persisted for instant re-open
- Modular design


### Roles

#### Product Owner
- Defines MVP success
- Chooses tradeoffs
- Approves defaults

#### Engineering Partner
- Proposes architecture
- Writes small modules
- Keeps scope tight

### Definition of Done

### Definition of Done (Sprint 1)
- [ ] **CLI:** `phaicull scan <path>` works and produces structured JSON.
- [ ] **DB:** Results are saved in SQLite; running the scan twice skips already processed files unless `--force` is used.
- [ ] **Tests:** Unit tests exist for the Blur and Brightness logic using synthetic images.
- [ ] **Concurrency:** Scanning a folder of 100+ images utilizes multiple CPU cores.

### ML Development Loop (when we start training)
- Add a baseline scorer (heuristics) and log features
- Build a small labeling workflow (pairwise is preferred)
- Train a simple ranker on features (fast features first, deep embeddings later)
- Evaluate per burst/series and track regressions on a “gold” set
- Ship the model behind a plugin interface (offline default)

#### CLIP is used ONLY for:
- scene similarity
- aesthetic preference modeling
- burst-level ranking

#### CLIP must not replace:
- blur detection
- exposure detection
- noise estimation

#### Personal Local Model Training (User Preferences)

- Phaicull ships with a **base model** that defines the default photo quality behavior.
- The base model can be **fine-tuned** locally but cannot be uploaded to replace origininal model shipped with Phaicull.

- Users may train a **personal local model** that reflects their own preferences
  (e.g. candid vs. posed photos, tolerance for motion blur, expression priority).
- This personal model:
  - is trained only on the user’s local photos and labels
  - is stored locally and never uploaded
  - is reusable across all projects on the same machine
  - builds on top of the base model’s features and embeddings rather than replacing them

- **Model lifecycle:**
  - users can delete their personal model at any time and revert to the base model
  - multiple personal model versions may be stored and backed up
  - switching models does not invalidate or recompute existing scan results

- **Architectural rule:**
  - base model = global, immutable, provided by Phaicull
  - personal model = user-owned, trainable, portable across projects


### 📂 Phaicull Directory Structure

This structure is the intended direction; minor deviations are acceptable if justified, document file have to be updated.

```text
/phaicull
├── .models/              # Local storage for ONNX/PyTorch weights (git-ignored)
├── .projects/            # Local storage for user projects, one database per project (git-ignored)
├── core/
│   ├── analyzers/        # Individual modules
│   │   ├── base.py       # Abstract Base Class
│   │   ├── blur.py
│   │   ├── exposure.py
│   │   ├── ...
│   │   └── aesthetic.py
│   ├── database/
│   │   ├── schema.py     # SQLite schema and WAL setup
│   │   └── dao.py        # Data Access Objects
│   ├── models/           # Pydantic schemas (JSON/DB models)
│   ├── utils/            # Image loading, EXIF, and thumbnail helpers
│   └── cli.py            # Main Typer/Click entry point
├── ui-macos/             # SwiftUI App
├── ui-windows/           # .NET 8 / WinUI 3 App
├── tests/                # Pytest suite with synthetic images
├── pyproject.toml        # Managed via 'uv'
├── agents.md             # The instructions you just wrote
└── README.md
```
