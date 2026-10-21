# 📸 Phaicull

> **Your AI second-set-of-eyes for family photos.**

**Phaicull** (pronounced *fai-cull*) is an open-source assistant for parents and photographers to reclaim their storage and time.

Fast, offline-first photo culling: find blurry, dark, duplicate, and low-quality shots, then keep only the best. 

## ❓ Why
Parents and enthusiasts with a "camera roll avalanche" need a tool that:
- **Works offline** by default (Privacy is non-negotiable for family photos).
- **Scans fast** and provides actionable sorting/filtering.
- **Identifies the "Best"** photo from a set of near-identical shots automatically.
- **Stays open source** and extensible for the community.

## 🎯 The Vision
Modern smartphones make it too easy to take 50 photos of a single moment. Most are "junk" (blurry, eyes closed, or near-identical). Phaicull helps you:
1. **Identify the Junk:** Quickly isolate blurry or dark photos.
2. **Select the Best:** Group near-duplicates and suggest the sharpest one.
3. **Protect Privacy:** No cloud. No subscriptions. Everything runs 100% locally. I dont plan to add online models, but it is opensource, so it is your choice.

## 🧠 Intelligent Scoring
Phaicull uses a multi-layered approach to analyze your library:
1. **Technical Layer:** Focus/Blur detection and exposure analysis (OpenCV).
2. **Subject Layer:** Face detection, eye-tracking (open/closed), and smile detection (MediaPipe).
3. **Aesthetic Layer:** High-level "keeper" scoring using a local **CLIP-based AI model**.

## 🛠 Development Setup
- **Python:** 3.12+
- **Package manager:** [uv](https://docs.astral.sh/uv/) (recommended)
- **Install:** `uv sync` — creates a virtual environment and installs dependencies from `pyproject.toml`
- **Run tests:** `uv run pytest`
- **CLI:** `uv run phaicull --help` or `uv run phaicull scan <folder>`. Each scan also groups
  visual near-duplicates (pHash, not time); see [`docs/grouping.md`](docs/grouping.md).
  Ctrl+C stops a scan safely (exit code 130): finished batches stay saved, and the
  next scan picks up the rest.

**Supported image formats:** JPEG, PNG, HEIC/HEIF (iPhone), GIF, WebP. Files are
validated by magic bytes, not extension; anything else is recorded as skipped.

**Sprint 1 verification** (speed, blur ranking, grouping stability; pass rules in
[`docs/plan/sprint1-verification.md`](docs/plan/sprint1-verification.md)):

```bash
uv run python scripts/verify_sprint1.py generate          # ~2 GB of 12 MP test photos in .local-photos/synthetic/
uv run python scripts/verify_sprint1.py run --photos .local-photos/synthetic/photos \
    --benchmark .local-photos/benchmark                   # real blurry/ + sharp/ photos (≥ 10 blurry)
```

Exit code 0 = all passed, 1 = a check failed, 2 = a check could not run (not enough photos).

**Test directories:**
- `tests/fixtures/images/` — committed basic images for unit tests (CI, contributors)
- `.local-photos/` — gitignored directory for real photo testing and model training (never committed)
- `.local-photos/benchmark/blurry/` and `../sharp/` — several hand-picked photos for blur accuracy checks. These are local test photos for development and testing. Do not commit this directory to the repository.

## 🛠 Tech Stack
- **Core:** Python 3.12+ (OpenCV, NumPy, MediaPipe, ONNX)
- **Database:** SQLite (One database per project/folder)
- **Frontends:** 
  - macOS: SwiftUI (Native)
  - Windows: .NET 8 / WinUI 3 (Native)
- **Communication:** 
  - **CLI-First**: The UI communicates with the core via a high-performance CLI and shared SQLite database.
  - Later: JSON-RPC?
  

## 🚀 Roadmap
- [ ] **Phase 1 (MVP - Foundation):** Robust CLI, SQLite persistence, technical metrics (blur/brightness), and pHash near-duplicate grouping (visual, not time-based).
- [ ] **Phase 2 (AI Core):** Integration of CLIP embeddings and the first "Aesthetic Scorer" model. Local fine-tuning for better user experience. 
- [ ] **Phase 3 (Native UI):** Initial release of macOS (SwiftUI) and Windows (.NET) grid views.
- [ ] **Phase 4 (Subject Intel):** Face mesh analysis for eye-closure and smile detection.
- [ ] **Phase 5 (Advanced):** RAW support, Apple/Android Photos integration, and user-driven model fine-tuning.

## ⚖️ License
MIT License - Open Source and free forever.
