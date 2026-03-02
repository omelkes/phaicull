Hi, I have my personal photo culling project and I want to use AI for development.  What do you think about this AGENTS.MD file? Do you think it  is good or bad? Is this file helpfull for agents or not? Should I improve it? 

Thank you 


-----------


# 🤖 AGENTS.md — AI Engineering Partner for Phaicull

> This file is the **authoritative guide** for any AI agent working on this codebase.
> Read it fully before writing any code. Source of truth for task status: [`TODO.md`](./TODO.md).

---

## 📋 Table of Contents
1. [Workflow Protocols](#workflow-protocols)
2. [Before Writing Code](#before-writing-code)
3. [When to Ask vs. When to Decide](#when-to-ask-vs-when-to-decide)
4. [Core Principles](#core-principles)
5. [Technical Standards](#technical-standards)
6. [Architecture & Image Analysis](#architecture--image-analysis)
7. [Performance & Concurrency](#performance--concurrency)
8. [Resilience & Error Handling](#resilience--error-handling)
9. [Testing Standards](#testing-standards)
10. [Dependency & Environment](#dependency--environment)
11. [Anti-Patterns](#anti-patterns)
12. [Terminology Glossary](#terminology-glossary)
13. [Directory Structure](#directory-structure)
14. [Definition of Done](#definition-of-done)

---

## Workflow Protocols

> All protocols marked **[MANDATORY]** must be followed on every task. Others are strong defaults.

### 1. Atomic Tasks **[MANDATORY]**

- **One TODO item per response..** Do not implement multiple items from [`TODO.md`](./TODO.md) in a single r qesponse. Item includes code + tests + docs + TODO update. 
- **Break it down first.** If a task seems too large for one response, propose sub-tasks and wait for confirmation before coding.
- **No speculative work.** Do not implement features not listed in [`TODO.md`](./TODO.md) or explicitly requested.
- **Reuse before creating.** Before writing a new module, search the codebase for existing patterns. If a similar utility exists, reuse or refactor it.
- **Completion gate.** A task is "done" only when: implemented, explained, and ready for basic testing.

### 2. Living Documentation **[MANDATORY]**

After every task:
- Update [`TODO.md`](./TODO.md): mark completed items, add newly discovered tasks or bugs.
- Update `README.md` or `docs/` if the public interface, setup steps, or architecture changed.
- End your response with a **"Project State"** note if the roadmap changed (e.g., new blockers, scope changes).

### 3. Before Writing Code **[MANDATORY]**

For any non-trivial change (new module, analyzer, DB schema change, concurrency, or ML logic), you must first provide a short plan:

```
PLAN
────
What: [what will be built]
Why this approach: [why over simpler alternatives]
Assumptions: [key assumptions made]
Risks: [performance, correctness, scope concerns]
TODO alignment: [which TODO.md item this addresses]
```

Only proceed to code after this plan is acknowledged.

---

## When to Ask vs. When to Decide

Use this table to avoid unnecessary back-and-forth while still surfacing real blockers.

| Situation | Action |
|---|---|
| Two valid approaches with different trade-offs | **Ask** — describe options briefly, recommend one |
| Ambiguous requirement in [`TODO.md`](./TODO.md) | **Ask** before coding |
| Minor implementation detail (variable name, helper method) | **Decide** and note your choice |
| Approach matches existing codebase patterns | **Decide** and proceed |
| New abstraction not in [`TODO.md`](./TODO.md) | **Ask** — do not invent it |
| Discovered a bug or missing requirement mid-task | **Add to [`TODO.md`](./TODO.md)**, note it, continue current task |

### Decision template

Use in commit message, docs or TODO note.

```
Decision: X, 
Alternatives: Y, 
Rationale: Z” (2-3 lines) 
```

---

## Core Principles

| Principle | Rule |
|---|---|
| **Privacy First** | No cloud processing. All models must run locally (ONNX, PyTorch, OpenCV). |
| **Speed is a Feature** | Use thumbnails. Lazy-load images. Offload CPU work to background processes. |
| **CLI-First** | The Python core is a standalone, functional CLI tool. UI is a consumer, not the driver. |
| **Idempotent Analyzers** | Every analyzer must be safely re-runnable. Missing metrics = `NULL`, not an error. |
| **TDD First** | Write tests before or alongside implementation. See [Testing Standards](#testing-standards). |

---

## Interface Stability & Security

### Interface Stability **[MANDATORY]**

The following are considered **stable APIs**. Once introduced, they must not be renamed, removed, or structurally changed without an explicit version bump and migration plan documented in [`TODO.md`](./TODO.md):

| Stable API | Examples |
|---|---|
| **CLI commands & flags** | `phaicull scan <path>`, `--output-format` |
| **JSON output schema** | Field names, types, and nesting in `stdout` output |
| **SQLite schema** | Table names, column names, column types |
| **Analyzer contract** | `BaseAnalyzer` interface, input/output types |
| **DAO public methods** | Method signatures in `core/database/dao.py` |

**Rules for evolving stable APIs:**

- **Adding** new fields: always backward-compatible — use nullable DB columns and optional JSON fields with defaults.
- **Changing or removing** anything: requires a `schema_version` increment in the `schema_version` table, a migration note added to [`TODO.md`](./TODO.md), updated documentation, and a corresponding test.
- **Internal refactoring** (private methods, variable names, implementation details) is free — stable interfaces must remain predictable for UI and automation consumers.

### Security & Safety **[MANDATORY]**

Phaicull processes untrusted local files. Treat every input file as potentially adversarial.

| Threat | Required Mitigation |
|---|---|
| **Malicious file types** | Validate using MIME magic bytes, not file extension |
| **Decompression bombs** | Check image dimensions and file size before loading; reject files exceeding safe limits |
| **Corrupted files** | Catch all exceptions per file; log to SQLite `status` column; never crash the scan |
| **Path traversal** | Use `pathlib.Path.resolve()` and verify all paths stay within the target project directory |
| **Sensitive EXIF data** | Strip or mask GPS coordinates and other PII from logs and JSON output |
| **Network exposure** | No network calls, telemetry, or runtime model downloads — ever |
| **DB corruption** | Always close connections and roll back uncommitted batches on shutdown or error |

> **See also:** [Resilience & Error Handling](#resilience--error-handling) for implementation patterns covering graceful failure and shutdown.

---

## Technical Standards

### Python
- Version: **3.12+**
- Use **type hints** everywhere. No untyped public functions.
- Use **`pathlib.Path`** for all filesystem operations. Never `os.path`.
- Use **pydantic v2** for all data validation (DB input, JSON output, config).

### Analyzer Contract
Every analyzer **must**:
- Inherit from `BaseAnalyzer` (defined in `core/analyzers/base.py`).
- Be **independently runnable** — no hidden dependencies on other analyzers.
- Be **idempotent** — running it twice on the same file produces the same result.
- Accept a `Path` (never raw bytes) and return a typed `Pydantic` model.

### Database
- Engine: **SQLite** with `PRAGMA journal_mode=WAL;` enabled on every connection.
- Schema versioning: use a `schema_version` table. Avoid Alembic until schema stabilizes.
- Partial scans are a first-class concept: every metric column is **nullable**.
- Use the **DAO pattern** (Data Access Objects) in `core/database/dao.py`. No raw SQL outside the DAO layer.
- Never perform heavy computation inside a SQLite write-lock.

### CLI
- Entry point: `core/cli.py`
- All output to `stdout` must be **machine-readable JSON**.
- Exit codes: `0` = success, non-zero = failure (use standard POSIX codes).
- The UI interacts with the Python core via **CLI subprocess calls** or **direct SQLite reads**. Never couple them more tightly.

---

## Architecture & Image Analysis

### Component Map

```
Analyzers   → Modular classes, one metric each (Blur, Brightness, pHash, etc.)
Storage     → DAO pattern over SQLite
CLI         → Typer entry point; outputs structured JSON
UI (macOS)  → SwiftUI app; reads SQLite or calls CLI subprocess
UI (Windows)→ .NET 8 / WinUI 3; same contract as macOS UI
```

### Image Analysis Phases

| Phase | Analyses | Trigger |
|---|---|---|
| **1. Metadata** | EXIF (date, camera, orientation) | Always |
| **2. Fast Scan** | Laplacian Variance (Blur), Histogram (Brightness), pHash (Duplicates) | Default scan |
| **3. Deep Scan** | MediaPipe/YOLO (faces), CLIP (quality score) | Explicit flag or later sprint |

### AI / Model Strategy
- **Embeddings:** CLIP via `sentence-transformers` or `open_clip`.
- **Quality scoring (MVP):** Pre-trained Aesthetic Predictor on top of CLIP embeddings.
- **User preferences:** Weight matrix stored locally in SQLite.
- **Model storage:** All weights in `.models/` (git-ignored). Models must be bundled locally; no runtime downloads.

### Auto-Orientation
- Read EXIF orientation before any analysis.
- All coordinate outputs (e.g., face bounding boxes) must be relative to the **oriented** image, not the raw file.

### Thumbnail Strategy
- Generate thumbnails during Fast Scan.
- Store in `phaicull/thumbs/` inside the user's photo directory (see [Directory Structure](#directory-structure)).
- Thumbnails are git-ignored.

---

## Performance & Concurrency

### The Brain / Brawn Model

| Layer | Technology | Responsibilities |
|---|---|---|
| **Brain** | `asyncio` | Orchestration, file-walking, DB writes, I/O coordination |
| **Brawn** | `multiprocessing` (ProcessPoolExecutor) | CPU-bound work: Blur, CLIP, OpenCV |

**Rule:** Never run Brawn logic inside the async event loop. Use `loop.run_in_executor(executor, fn, path)` to bridge them.

### Memory Safety — The Golden Rule

1. **Pass `Path`, never `bytes`** between processes.
2. **Lazy loading:** Load an image only when the specific analyzer that needs it is executing.
3. **Batching:** Process AI model inference (CLIP, MediaPipe) in batches, not one image at a time.
4. **Bomb check:** Always verify image dimensions and file size before loading to prevent Decompression Bomb crashes.

---

## Resilience & Error Handling

- **Graceful failure:** If a file is corrupted or unreadable, log the error to the SQLite `status` column and continue. Never crash the scan.
- **MIME validation:** Verify file signatures (magic bytes), not just extensions.
- **Graceful shutdown:** Handle `SIGINT` (Ctrl+C) by closing SQLite connections and rolling back uncommitted batches.
- **Validation gate:** All data must pass Pydantic v2 validation before DB writes or JSON output.

---

## Testing Standards

### Framework & Location
- Framework: **pytest**
- Location: `tests/` (mirrors `core/` structure, e.g., `tests/analyzers/test_blur.py`)
- Naming: `test_<module>.py`, test functions as `test_<behavior>_<condition>`

### Required Test Cases per Analyzer

Every analyzer must have tests for all four categories:

| Category | Example |
|---|---|
| **Happy path** | Valid JPEG, valid PNG |
| **Corrupted files** | Zero-byte file, truncated JPEG |
| **Non-image files** | `.txt`, `.pdf` passed as input |
| **Edge cases** | Extreme aspect ratios, 1×1 pixel, very large file |

### TDD Workflow
1. Write the test (failing).
2. Write the minimum code to pass.
3. Refactor.
4. Do not submit code where tests are skipped without a documented reason in [`TODO.md`](./TODO.md).

---

## Dependency & Environment

- **Package manager:** `uv` (preferred). All dependencies declared in `pyproject.toml`.
- **Model storage:** `.models/` directory, git-ignored. No runtime downloads; models must be present locally.
- **Project storage:** `.projects/` directory, git-ignored.
- **Portability:** Code must run on macOS (arm64/x86) and Windows 10+.

---

## Anti-Patterns

| ❌ Do NOT | ✅ Instead |
|---|---|
| Use `os.path` | Use `pathlib.Path` |
| Mix UI concerns (Tkinter, PySide) into Python core | Keep UI in `ui-macos/` or `ui-windows/` |
| Introduce a long-running daemon or server (MVP) | Use CLI subprocess or direct SQLite reads |
| Perform heavy computation inside a SQLite write-lock | Compute first, write results in batch |
| Pass raw `bytes` between processes | Pass `Path` objects |
| Create a new analyzer without inheriting `BaseAnalyzer` | Always subclass `BaseAnalyzer` |
| Add a feature not in [`TODO.md`](./TODO.md) | Add it to `TODO.md` and get acknowledgment first |
| Write tests without edge cases | Include all four test categories (see [Testing Standards](#testing-standards)) |

---

## Terminology Glossary

| Term | Definition |
|---|---|
| **Analyzer** | A module that computes exactly one metric (e.g., blur score). Must subclass `BaseAnalyzer`. |
| **Scan** | A run over a set of files that may compute only a subset of metrics. |
| **Project** | A photo directory with a single associated SQLite database in `phaicull/phaicull.db`. |
| **Base Model** | An immutable model shipped with Phaicull (read-only). |
| **Personal Model** | A user-trained local model layered on top of a Base Model. |
| **Brain** | The `asyncio` orchestration layer. Handles I/O, file-walking, DB coordination. |
| **Brawn** | The `multiprocessing` compute layer. Handles CPU-bound image analysis. |
| **Fast Scan** | Metadata + Blur + Brightness + pHash. Designed to be quick. |
| **Deep Scan** | Face detection + CLIP quality scoring. Heavier, run on-demand or later. |

---

## Directory Structure

### Repository

```
/phaicull
├── .models/              # Local model weights (git-ignored)
├── .projects/            # Project path registry (git-ignored)
├── core/
│   ├── analyzers/
│   │   ├── base.py       # BaseAnalyzer abstract class
│   │   ├── blur.py
│   │   ├── brightness.py
│   │   └── ...
│   ├── database/
│   │   ├── schema.py     # SQLite schema, WAL pragma, version table
│   │   └── dao.py        # Data Access Objects (all SQL lives here)
│   ├── models/           # Pydantic schemas (DB models, JSON output)
│   ├── utils/            # Image loading, EXIF helpers, thumbnail generation
│   └── cli.py            # Typer entry point
├── ui-macos/             # SwiftUI app
├── ui-windows/           # .NET 8 / WinUI 3 app
├── tests/
│   ├── analyzers/        # test_blur.py, test_brightness.py, ...
│   ├── database/
│   └── conftest.py       # Shared fixtures (synthetic images, temp DBs)
├── pyproject.toml        # Managed via uv
├── TODO.md               # ← Single source of truth for task status
├── AGENTS.md             # ← This file
└── README.md
```

### Per-Project Directory (Inside User's Photo Folder)

```
/photo-directory/
├── phaicull/
│   ├── thumbs/           # Cached thumbnails (git-ignored)
│   └── phaicull.db       # SQLite database for this photo directory
├── img001.jpg
├── img002.jpg
└── ...
```

---

## Definition of Done

### General Definition

A task is considered **done** when all of the following are true:

| Criterion | Requirement |
|---|---|
| **Implemented** | Code is written, compiles/runs, and fulfills the task description |
| **Tested** | Unit tests cover happy path + all four edge case categories (see [Testing Standards](#testing-standards)) |
| **Documented** | Any changed public interface, CLI flag, or DB schema is reflected in `README.md` or `docs/` |
| **Validated** | Pydantic models validate all inputs/outputs; no unhandled exceptions on known error cases |
| **Logged** | Errors and key events are logged at the appropriate level |
| **TODO updated** | The corresponding item in [`TODO.md`](./TODO.md) is marked complete; any discovered follow-up tasks are added |

A task is **not done** if tests are skipped, documentation is stale, or [`TODO.md`](./TODO.md) has not been updated.

### Sprint Task Status

> **All current sprint tasks, priorities, and completion status are tracked in [`TODO.md`](./TODO.md).**
> That file is the single source of truth. Do not rely on this file for task status — always read `TODO.md` first.

---

*Last updated: see git log. For task status, always refer to [`TODO.md`](./TODO.md).*
