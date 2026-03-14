# Phaicull — Architecture Decisions

> Decisions made during development. Each entry documents the choice, alternatives, and rationale.

## Summary (Sprint 0, Section 1)

| ID | Topic | Decision |
|----|-------|----------|
| DEC-001 | SQLite access | raw `sqlite3` |
| DEC-002 | Structured logging | loguru |
| DEC-003 | CLI framework | typer |
| DEC-004 | Migration strategy | custom lightweight script |
| DEC-005 | Config format | TOML (stdlib tomllib) |

See [ADR-001](adr-001.md) for the full architecture decision record (CLI-first, SQLite, offline-first, UI contracts).

---

## DEC-001: SQLite Access — raw `sqlite3` vs SQLAlchemy

**Status:** Decided  
**Date:** 2025-03-02  
**TODO:** Sprint 0, Section 1 — Research and Decide: SQLite via raw `sqlite3` or `SQLAlchemy`

### Decision

**Use the standard library `sqlite3` module** (raw SQL). No SQLAlchemy.

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **raw `sqlite3`** | Zero DB dependency, full control, explicit SQL, lightweight, matches DAO pattern | Manual migrations, no ORM conveniences |
| **SQLAlchemy Core** | Structured queries, optional Alembic migrations | Extra dependency, more abstraction than needed for simple schema |
| **SQLAlchemy ORM** | ORM conveniences, model mapping | Heavier, ORM overhead, schema is simple enough to not benefit |

### Rationale

1. **AGENTS.md alignment:** "Avoid Alembic until schema stabilizes" — we are in Sprint 0; schema will evolve. A lightweight custom migration script fits better than adopting Alembic now.

2. **DAO pattern:** All SQL lives in `core/database/dao.py` regardless. The DAO layer provides the abstraction; an ORM does not add value for our use case.

3. **Schema simplicity:** Four tables (`files`, `metrics`, `groups`, `projects`) with straightforward relationships. Raw SQL is readable and maintainable.

4. **Dependency footprint:** `sqlite3` is built into Python. No extra packages for DB access.

5. **Control:** WAL mode, batching, and connection lifecycle are explicit. We avoid ORM behavior that can surprise (e.g., lazy loading, session management).

6. **Future flexibility:** If the schema stabilizes and migrations become complex, we can revisit SQLAlchemy/Alembic. The DAO interface can remain stable.

### Implementation Notes

- Use `sqlite3` with `PRAGMA journal_mode=WAL;` on every connection.
- All SQL in `core/database/dao.py`; no raw SQL elsewhere.
- Schema versioning via a `schema_version` table and a custom lightweight migration script (see DEC-004).

---

## DEC-002: Structured Logging — Tool for UI-Parseable Log Stream

**Status:** Decided  
**Date:** 2025-03-02  
**TODO:** Sprint 0, Section 1 — Decide tool for structured logging

### Decision

**Use `loguru`** for structured logging. Configure a JSON sink for stdout when the UI needs to parse progress; use human-readable format for interactive CLI use.

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **loguru** | Simple API, `serialize=True` for JSON, easy custom sinks, drop-in friendly | Extra dependency |
| **structlog** | Designed for structured/JSON output, processors, context binding | Steeper learning curve, more config for simple cases |
| **stdlib `logging` + custom JSON formatter** | No extra dependency | Boilerplate, no built-in serialization, harder to maintain |

### Rationale

1. **UI parsing requirement:** The UI must parse the log stream for real-time progress (e.g., `{"event": "progress", "percent": 42, "current": "img001.jpg"}`). Loguru supports `serialize=True` to emit JSON lines, or we can add a custom sink that emits structured progress events.

2. **Simplicity:** Loguru has a minimal API (`logger.info(...)`) and sensible defaults. Less setup than structlog for our use case.

3. **Dual output:** We can route to multiple sinks — human-readable for terminal, JSON for UI subprocess consumption — without duplicating logic.

4. **TODO alignment:** The TODO explicitly recommends considering loguru; it fits the requirement.

5. **Maturity:** Loguru is widely used, well-maintained, and compatible with Python 3.12+.

### Implementation Notes

- Add `loguru` to `pyproject.toml` dependencies.
- Use `logger.add(sys.stderr, format="...")` for interactive CLI.
- For UI subprocess: add a sink with `serialize=True` or a custom serializer that emits JSON lines with `event`, `percent`, `current`, `message`, etc.
- Define a **progress event schema** (documented in the Progress Reporting Contract; see `docs/progress_contract.md`).

---

## DEC-003: CLI Framework — Typer vs Click

**Status:** Decided  
**Date:** 2025-03-02  
**TODO:** Sprint 0, Section 1 — Decide framework for CLI

### Decision

**Use `typer`** for the CLI entry point.

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **typer** | Type-hint driven, built on Click, Pydantic integration, less boilerplate | Extra dependency (includes Click) |
| **click** | Mature, flexible, widely used | More decorator/boilerplate, no native type-hint inference |

### Rationale

1. **AGENTS.md alignment:** Technical Standards specify "Use **type hints** everywhere" and "**pydantic v2** for all data validation." Typer infers options and arguments from type hints, reducing repetition and keeping the CLI consistent with the rest of the codebase.

2. **TODO preference:** The TODO explicitly prefers Typer.

3. **Pydantic integration:** Typer supports Pydantic models for complex validation. Phaicull uses Pydantic for DB models and JSON output; CLI args can reuse or mirror these models.

4. **Click compatibility:** Typer is built on Click. We get Click's ecosystem (e.g., `rich` for output) with a cleaner API.

5. **Entry point:** CLI lives at `core/cli.py` per AGENTS.md; Typer's `typer.Typer()` app pattern fits this structure.

### Implementation Notes

- Add `typer` to `pyproject.toml` dependencies.
- Entry point: `core/cli.py` with `app = typer.Typer()`.
- Use `rich` for terminal output (per TODO Section 5).

---

## DEC-004: Migration Strategy — Custom Script vs Alembic

**Status:** Decided  
**Date:** 2025-03-02  
**TODO:** Sprint 0, Section 1 — Decide Migration Strategy

### Decision

**Use a custom lightweight migration script.** No Alembic. Migrations live as sequential SQL files in `core/database/migrations/`; a small Python module applies them and updates the `schema_version` table.

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **Custom lightweight script** | No extra dependency, works with raw sqlite3, full control, simple | Manual migration file creation |
| **Alembic** | Mature, auto-generate migrations, version tracking | Tied to SQLAlchemy ecosystem, overkill for 4-table schema, AGENTS.md says avoid until schema stabilizes |
| **Inline schema + Python migrations** | Single source of truth | Harder to review diffs, migrations mixed with app code |

### Rationale

1. **DEC-001 alignment:** We chose raw `sqlite3`. Alembic is typically used with SQLAlchemy; using it with raw SQL is possible but adds complexity and an extra dependency.

2. **AGENTS.md:** "Avoid Alembic until schema stabilizes" — we are in Sprint 0; schema will evolve through Sprints 1–2.

3. **Schema simplicity:** Four tables with straightforward changes. A script that runs `001_initial.sql`, `002_add_metrics.sql`, etc., is sufficient.

4. **Transparency:** SQL migration files are easy to review, diff, and understand. No ORM/metadata layer.

5. **Future flexibility:** If the schema grows complex, we can adopt Alembic later. The `schema_version` table and migration pattern will translate.

### Implementation Notes

- Create `core/database/migrations/` with numbered SQL files: `001_initial.sql`, `002_*.sql`, etc.
- `schema_version` table: `(version TEXT PRIMARY KEY)` — stores current version (e.g., `"1"` or `"001"`).
- Migration runner: `core/database/migrate.py` — on DB open, check `schema_version`, run any migrations with higher number, update `schema_version`.
- Each migration file is idempotent where possible, or the runner ensures each runs only once.

### Implemented (Sprint 0)

- `core/database/migrations/001_initial.sql` — creates `schema_version` table with `(version, description, applied_at)`.
- `core/database/migrations/002_project_schema.sql` — project DB tables: `files`, `metrics`, `groups`.
- **Two databases:**
  - **Project DB:** one per photo directory at `{project}/phaicull/phaicull.db`. Tables: `schema_version`, `files`, `metrics`, `groups`. Use `migrate(db_path)`.
  - **Registry DB:** one in install dir at `.projects/registry.db`. Tables: `schema_version`, `projects`. Use `migrate_registry(db_path)`.
- `core/database/migrations_registry/001_initial.sql` — registry `schema_version` and `projects` table.
- `core/database/migrate.py`:
  - `migrate(db_path)` — project DB: applies migrations from `migrations/`; returns current version (e.g. `"002"`).
  - `migrate_registry(db_path)` — registry DB: applies migrations from `migrations_registry/`; returns current version (e.g. `"001"`).
  - `get_schema_version(db_path)` — returns current version without running migrations.
  - `get_applied_migrations(db_path)` — returns list of all applied migrations (version, description, applied_at) for audit.
- **Description:** From migration file via `-- migration: <description>` or `-- description: <description>`; otherwise filename.
- **History:** Each applied migration is appended to `schema_version` (no overwrite); full history enables recovery and verification.
- `core/database/schema.py` — schema constants and table/column names (stable API).
- `core/database/dao.py` — DAO: `get_project_db_path`, `get_registry_db_path`, `ensure_project_db`, `ensure_registry_db`, `open_project_connection`, `open_registry_connection`, `insert_file`, `add_project`, `list_projects`.

---

## DEC-005: Config Format — TOML vs YAML

**Status:** Decided  
**Date:** 2025-03-09  
**TODO:** Sprint 0, Section 5 — Config system

### Decision

**Use TOML** for configuration. Load via stdlib `tomllib` (Python 3.11+). Config file: `phaicull.toml`.

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **TOML** | Stdlib `tomllib`, zero dependency, matches pyproject.toml, Pydantic validation | Less common for app config than YAML |
| **YAML** | Widely used for config, human-friendly | Requires PyYAML, AGENTS.md: ASK for new deps, verify offline |

### Rationale

1. **No new dependency:** `tomllib` is in the Python 3.11+ stdlib. Phaicull requires 3.12+.
2. **AGENTS.md alignment:** "New dependency needed — ASK" — TOML avoids adding PyYAML.
3. **Pydantic:** `Config.model_validate(tomllib.load(fp))` works cleanly.
4. **Schema:** `[thresholds]`, `burst_window_seconds`, `heavy_features_enabled` map directly.

### Implemented (Sprint 0)

- `core/config.py` — `Config`, `ThresholdsConfig` (Pydantic v2), `load_config(path)`.
- Fields: `thresholds.blur_min`, `thresholds.brightness_min`, `thresholds.brightness_max`, `burst_window_seconds`, `heavy_features_enabled`.
- `phaicull.toml.example` — example config for users.
