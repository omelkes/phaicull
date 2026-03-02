# Phaicull — Architecture Decisions

> Decisions made during development. Each entry documents the choice, alternatives, and rationale.

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
- Schema versioning via a `schema_version` table and a lightweight migration script (to be decided in a separate decision).
