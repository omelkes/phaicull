# 🤖 AGENTS.md — AI Engineering Partner for Phaicull

This file is the **authoritative guide** for any AI agent working on this codebase.
Read it fully before writing any code.
Source of truth for tasks: [`TODO.md`](./TODO.md).

---

## 🛡️ Core Principles (The "Soul" of Phaicull)

- **PRIVACY FIRST [MANDATORY]:** No cloud processing. No telemetry. No external API calls. All models must run 100% locally. Treat user data as sacred.
- **Speed is a Feature:** Use thumbnails, lazy-loading, and background processing.
- **CLI-First:** The Python core is a standalone CLI tool. UI is merely a consumer.
- **Idempotent Analyzers:** Must be safely re-runnable. Missing metrics = `NULL`, not an error.
- **TDD First:** Write tests before or alongside implementation.

---

## 🛠 Workflow Protocols [MANDATORY]

### 1. Atomic Tasks [MANDATORY]
- **Atomic Tasks:** One TODO item per response. Include code + tests + docs + TODO update. 
- **Plan First:** For any non-trivial change, provide a `PLAN` (What, Why, Risks, Alignment) and wait for acknowledgment.


### 2. Living Documentation
    - Update [`TODO.md`](./TODO.md) immediately after completion (mark done, add new bugs/tasks).
    - End every response with a **"Project State"** summary if the roadmap or architecture shifted.
    - Update `README.md` or `docs/` if the public interface, setup steps, or architecture changed.

### 3. Interface Stability (The "Contract")
The following are **Stable APIs**. Do not rename or break them without a version bump:
- **CLI commands/flags** | **JSON output schema** | **SQLite schema** | **Analyzer contract** | **DAO methods**

**Rules for Evolving APIs:**
- **Additions:** Must be backward-compatible (nullable columns, optional JSON fields).
- **Changes/Removals:** Requires `schema_version` increment, migration note in `TODO.md`, and updated tests.
- **Internal Refactoring:** Free to change as long as the stable interfaces remain identical.


### 4. Search Before Code
Always search the codebase for existing patterns/utilities. Reuse > Refactor > Create.

---

## ⚖️ Decision Matrix

| Situation | Action |
|---|---|
| New dependency needed | **ASK** — verify it works 100% offline |
| Ambiguous requirement or multiple valid architectural trade-offs | **ASK** — provide options & recommendation |
| Minor implementation detail (naming, helpers) matching existing style | **DECIDE** — proceed and note in summary |
| Discovered bug outside current task scope | **LOG** — add to `TODO.md`, do not fix now |
| Change to Stable APIs (CLI, JSON schema, DAO public methods) | **ASK** — requires version bump plan |

### Decision template

Use in commit message, docs or TODO note.

```
Decision: X, 
Alternatives: A,B,... 
Rationale: R" (2-3 lines) 
```

---


## 🏗 Core Architecture & Logic

### The Brain / Brawn Model
- **Brain (`asyncio`):** Orchestration, I/O, DB writes, file-walking. **Never** run CPU-bound code here.
- **Brawn (`multiprocessing`):** All image analysis (OpenCV, AI models). 
- **Bridge:** Use `loop.run_in_executor` to call Brawn from Brain.

### Data & Storage
- **Local Only:** No cloud, no telemetry, no runtime model downloads.
- **SQLite (WAL mode):** Use the **DAO pattern** (`core/database/dao.py`). No raw SQL in analyzers.
- **Analyzers:** Must inherit from `BaseAnalyzer`, be **idempotent**, and handle only **one** metric.
- **Memory Safety:** Pass `Path` objects between processes, never raw `bytes`. Load images only when needed.
- **Schema versioning:** use a schema_version table. Avoid Alembic until schema stabilizes.

---

## 🔒 Security & Resilience
- **Decompression Bombs:** Verify image dimensions/size before loading.
- **Adversarial Input:** Validate MIME magic bytes, not extensions. Catch all per-file exceptions; never crash the scan.
- **Path Traversal:** Use `pathlib.Path.resolve()` to ensure operations stay within project scope.
- **Graceful Shutdown:** Handle `SIGINT` (Ctrl+C) by rolling back uncommitted DB batches.
- **Network exposure:**  No network calls, telemetry, or runtime model downloads — ever.

---

## 📝 Technical Standards (Python 3.12+)

- **Typing:** Strict type hints everywhere. No `Any` without justification.
- **Validation:** Use **Pydantic v2** for all data (DB, JSON output, Config).
- **Filesystem:** `pathlib.Path` only. Never use `os.path`.
- **Testing:** Every analyzer requires 4 test categories:
    1. **Happy path** (valid files).
    2. **Corrupted** (truncated/zero-byte).
    3. **Invalid type** (txt, pdf).
    4. **Edge cases** (1x1 px, extreme aspect ratios).

---

## 🚫 Anti-Patterns (Do NOT do these)

| ❌ AVOID | ✅ INSTEAD |
|---|---|
| Speculative features | Stick strictly to `TODO.md` |
| Mixing UI logic into `core/` | UI must remain a consumer (CLI/SQLite only) |
| Heavy computation in DB write-lock | Compute first, batch write results later |
| Silent failures | Log to SQLite `status` column and system logger |
| Hardcoded paths | Use `Path(__file__)`, config, or project registry |
| Creating new analyzers from scratch | Subclass `BaseAnalyzer` |

---

## 📁 Non-Obvious Directory Notes
- `.models/`: Git-ignored. Stores local weights. Models must be bundled.
- `.projects/`: Git-ignored. Registry of local photo directories.
- `ui-macos/` & `ui-windows/`: Independent UI consumers. Maintain strict CLI/DB contract.
- `phaicull/` (inside user folders): Contains `phaicull.db` and `thumbs/`.

---

**Definition of Done:** Implemented + 4-category Tests + Docs updated + `TODO.md` updated + No Pydantic validation errors.