## Testing Strategy (Loader & DB)

This document summarizes how SQLite and test data are used across the
test suite, with a focus on the Loader phase.

### Test tiers and DB modes

- **Unit tests (fast, pure logic)**  
  - Prefer **no DB at all** when possible (e.g. analyzers given already‑loaded image data).  
  - When a DB is useful, use an **in‑memory project DB connection** via a dedicated pytest fixture
    (see `tests/conftest.py`) so setup/teardown are cheap and isolated.

- **Component tests (Loader + analyzers, small sets)**  
  - Use **temporary on‑disk project DBs** created under `tmp_path` via factory fixtures.  
  - These exercise real migrations, DAO calls, and partial scan flows while staying fast.  
  - Each test gets its own DB; nothing is shared between tests.

- **Integration / benchmark tests (real workloads)**  
  - Use **on‑disk project DBs** placed alongside real photos in `.local-photos/`.  
  - These runs are marked as slow/optional (e.g. `pytest -m real_photos`) and are not required for CI.  
  - Databases and logs from these runs are **not cleaned up automatically** so they can be inspected
    when debugging issues such as failures after hundreds or thousands of files.

### Cleanup and isolation

- **Unit and component tests**
  - Rely on pytest `tmp_path` for all on‑disk DBs and synthetic files.
  - DBs are created with function‑scope fixtures, so state never leaks between tests.
  - Temporary files and DBs live under the test run’s temp directory; they are removed by pytest,
    but can still be inspected while a failing test session is active.

- **Real‑photo integration tests**
  - Use real project roots under `.local-photos/` so DBs and thumbnails persist across runs.
  - Intended for local development, performance checks, and model training/debugging.
  - Never required for a green CI run and never committed to the repository.

### Test data layout

- **Committed synthetic fixtures**
  - Live under `tests/fixtures/images/`.  
  - Contain only small, non‑sensitive images and edge‑case files:
    - Tiny images (1x1, very wide/tall) for edge cases.
    - Simple patterns for blur/exposure checks.
    - Corrupted or non‑image files (zero‑byte, truncated JPEG, `.txt`) for negative tests.
  - Safe to store in Git and use in CI.

- **Local real‑photo directory**
  - `.local-photos/` at the repository root is **gitignored** and intended for private photo sets.  
  - Used for:
    - Manual ad‑hoc testing of new Loader/analyzer behavior.
    - Optional slow integration tests.
    - Training and validating future models on realistic data.
  - Developers are responsible for populating this folder locally; no sample photos are provided.

This hybrid approach keeps the default test suite fast and deterministic, while still supporting
realistic, on‑disk debugging and long‑running experiments during Loader and model development.

