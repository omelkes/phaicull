# 📸 Phaicull

> **Your AI second-set-of-eyes for family photos.**

**Phaicull** (pronounced *fai-cull*) is an open-source assistant for parents and photographers to reclaim their storage and time.

Fast, offline-first photo culling: find blurry, dark, duplicate, and low-quality shots, then keep only the best. 

## ❓ Why
Parents and enthusiasts with a "camera roll avalanche" need a tool that:
- **Works offline** by default (Privacy is non-negotiable for family photos).
- **Scans fast** and provides actionable sorting/filtering.
- **Identifies the "Best"** photo from a burst or series automatically.
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
- [ ] **Phase 1 (MVP - Foundation):** Robust CLI, SQLite persistence, technical metrics (blur/brightness), and pHash duplicate grouping.
- [ ] **Phase 2 (AI Core):** Integration of CLIP embeddings and the first "Aesthetic Scorer" model. Local fine-tuning for better user experience. 
- [ ] **Phase 3 (Native UI):** Initial release of macOS (SwiftUI) and Windows (.NET) grid views.
- [ ] **Phase 4 (Subject Intel):** Face mesh analysis for eye-closure and smile detection.
- [ ] **Phase 5 (Advanced):** RAW support, Apple/Android Photos integration, and user-driven model fine-tuning.

## ⚖️ License
MIT License - Open Source and free forever.
