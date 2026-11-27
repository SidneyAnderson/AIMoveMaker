# AI Movie Maker — Product Requirements Documentation

This folder contains the Product Requirements Documents (PRDs) for the AI Movie Maker end-to-end AI film production platform.

---

## Core Documentation

### **prd_text.txt**
**Version:** 1.0 (Initial Release)  
**Status:** Implemented v1 — Regression verified  
**Date:** March 13, 2026; updated May 31, 2026  

The baseline PRD defining the core AI Movie Maker v1 platform. This document establishes the multi-user foundation (Redis, Celery, RBAC, JWT/OAuth), Creative/Engineer workflow, storyboard/timeline architecture, and the FastAPI + React application structure.

### **ai_movie_maker_prd_v1.docx**
Word format version of the baseline PRD v1.0.

---

## Movie Maker Addendum (v1.2)

### **addendum/AIMoveMaker_PRD_Addendum_MovieMaker_v1.3.md**
**Version:** 1.3 — Addendum to PRD v1.0  
**Status:** Specification for the v1.3 build — not yet implemented  
**Date:** November 26, 2026  
**Changelog:** v1.3 adds Section A18 keyframe image-model defaults: shipped T2I default Krea 2 Turbo (`krea_2_turbo`), automatic fallback Z-Image-Turbo (`z_image_turbo`), shipped edit/consistency default FLUX 3 Image Klein (`flux_3_image_klein`), MiniMax-H3-Image becomes H3-profile default only after license authorization + 32GB VRAM fit gates; per-profile `default_image_model_key` / `default_image_edit_model_key`; Import Model applies to image models. v1.2 moves LTX core to LTX-2.5, pins Diffusers ≥ 0.40, adds Wan Animate 2 pipeline support.

The build-contract addendum extending AI Movie Maker v1 with the Movie Maker layers: MiniMax H3 runtime-agnostic engine, Import Model converter pipeline with safety gates, project-level core model lock, multi-user model library, Seed Hunter v3 workflow (6-field structured prompts, RefMods, 3-seed Stage-1 previews, 3D latent upscale Stage-2, dialogue cloner, 17n+5 seamless continuation), keyframe image model defaults (Krea 2 Turbo, FLUX 3 Image Klein, MiniMax-H3-Image with gates), LTX-2.5 & Wan Animate 2 support, NLE seam finishing tools, and native Redis installers (Ubuntu/Windows without Docker).

**Key Features:**
- Immutable per-project core video model (`minimax_h3`, `ltx_2_5`, or `wan_bernini`)
- Keyframe image model defaults (v1.3): Krea 2 Turbo T2I default with Z-Image-Turbo fallback; FLUX 3 Image Klein edit/consistency default; MiniMax-H3-Image H3-profile default gated by license + VRAM fit
- Import Model: Civitai/local intake → header detection → ComfyUI-to-Diffusers conversion → FP8/NVFP4 quantization → test render safety gate → RBAC-guarded cleanup (applies to video and image models)
- Multi-user model/LoRA library with `global`/`user` visibility, `owner_id`, and shared-folder reference checks
- H3 Seed Hunter v3 integration: structured `Singularity` prompts, RefMods, multi-seed previews, voice cloner, continuation with quality resets
- Runtime-agnostic: standard Diffusers/SGLang only; ComfyUI compatibility explicitly dropped
- Admin `.env` secrets vs optional per-user credential overrides
- Celery per-engine GPU queue routing (`.venvs/h3`, `.venvs/ltx`, `.venvs/audio`)
- Effort estimate: 41–58 days across Phases 0–5

### **addendum/AIMoveMaker_PRD_Addendum_MovieMaker_v1.3.docx**
Word format version of the v1.3 addendum.

---

## Planning & Analysis Documents

### **MovieMaker_Plan.md**
**Title:** Bringing Long-Video-Creator into AIMoveMaker  
**Version:** Updated 2026-11-26  
**Estimate:** 41–58 days across Phases 0–5  

Comprehensive gap analysis and phased implementation plan. Code-verified audit of 24 feature areas comparing Long-Video-Creator/Seed Hunter v3 specifications against the implemented AI Movie Maker v1 codebase. Documents the multi-user architecture decision (keeping Redis/Celery/RBAC), runtime-agnostic standard weights policy, Import Model pipeline design, and six-phase delivery roadmap.

**Contents:**
- Summary verdict & key metrics (0 Has / 10 Partial / 14 Missing)
- Project-level core model design
- Import Model & model library architecture
- MiniMax H3 + LoRA: runtimes, quantization, training ecosystem, unknowns
- Seed Hunter v3 workflow mapping (8 pipeline stages)
- Feature gap matrix (24 areas with effort estimates)
- Design conflicts resolution
- Key risks and unknowns
- Phase 0–5 build order with acceptance criteria

### **MovieMaker_Integration_Map.md**
**Title:** Integration Plan: Movie Maker into AIMoveMaker  
**Version:** Updated 2026-11-26  
**Estimate:** 41–58 days across Phases 0–5  

File-by-file integration blueprint mapping the phased plan onto the AIMoveMaker codebase. Inventories 46 component groups (backend core, models/schemas, routers/services, pipelines/tasks, frontend, scripts) with disposition (Reuse as-is / Refactor / Replace / Remove) and phase assignments. Documents 8 critical integration seams with options and recommendations.

**Contents:**
- Integration overview (13 reuse / 31 refactor / 2 replace)
- Component inventory by layer with integration rationale
- Seams and conflicts (Celery GPU routing, WebSocket progress, RBAC extensions, model library visibility, admin `.env` vs user secrets, RuntimeAdapters, schema migrations, native Redis installers)
- Phase-by-phase integration sequence (exact files, migrations, endpoints, UI changes, acceptance checks)
- Integration risks and estimate reconciliation

---

## Implementation Guides (Agent-Ready)

### **BUILD_GUIDE.md**
**Title:** Movie Maker Build Guide  
**Version:** 1.0  
**Date:** 26 November 2026  
**Target:** Coding agents building Movie Maker features on AIMoveMaker v1 codebase

Agent-ready technical implementation guide grounded in the actual AIMoveMaker code at `/workspace`. Provides complete repository map, naming conventions, existing patterns to copy, and hard rules (multi-user RBAC, immutable project core model, runtime-agnostic Diffusers/SGLang only, no Docker, never commit secrets). Breaks each phase (P0–P5) into small work packages with exact files to modify, function signatures, data model changes, Alembic migrations, API endpoints, Celery queue assignments, test expectations, acceptance criteria, and definition of done.

**Contents:**
- Repository map & directory structure
- Code patterns with examples: Models (SQLAlchemy), Schemas (Pydantic), Services (async), Routers (FastAPI), Celery tasks, Migrations (Alembic), Frontend (React/Zustand/TypeScript)
- Hard rules (6 non-negotiable requirements)
- Phase-by-phase work packages: P0 (H3 spike), P1 (project lock + library), P2 (Import Model), P3 (H3 workers + Seed Hunter), P4 (Prompt IDE + ASR), P5 (NLE seam + native Redis)
- Testing strategy, common pitfalls, development workflow

### **UI_UX_SPEC.md**
**Title:** Movie Maker UI/UX Specification  
**Version:** 1.0  
**Date:** 26 November 2026  
**Target:** Coding agents building Movie Maker UI on AIMoveMaker v1 React/Vite frontend

Complete UI/UX design specification grounded in the actual React/Vite frontend code at `/workspace/frontend/src`. Covers information architecture (navigation by role), design system (blue-green theme, Shadcn/ui components), and detailed screen-by-screen specifications with layouts, states (empty/loading/error/progress), role permissions, and WebSocket real-time features. Includes ASCII wireframes and Mermaid flow diagrams.

**Contents:**
- Information architecture & route structure
- Design system: color palette (#081A24, #36A9E8, #2DD4BF), component library (Shadcn/ui), reusable patterns (list views, empty/loading/error states)
- Screen specifications: ProjectsView (core model picker), ModelsView (Import Model 5-step wizard), StoryboardView (6-field H3 Prompt IDE, RefMods, 3-seed Stage-1 previews, Stage-2 upscale), TimelineView (17n+5 continuation, drift counter, seam color grading, voice cloner, render queue), AdminView, SettingsView
- WebSocket progress patterns: job progress, import progress, project presence
- Responsive behavior & accessibility (keyboard nav, ARIA labels, WCAG AA contrast)
- ASCII wireframes & Mermaid flow diagrams

---

## Historical Versions

### **history/AIMoveMaker_PRD_Addendum_MovieMaker_v1.1.md**
**Version:** 1.1 — Addendum to PRD v1.0  
**Date:** November 25, 2026  

Previous version of the Movie Maker addendum. Retained for historical reference and change tracking.

### **history/AIMoveMaker_PRD_Addendum_MovieMaker_v1.2.md**
**Version:** 1.2 — Addendum to PRD v1.0  
**Date:** November 26, 2026  

Previous version (superseded by v1.3). Retained for historical reference and change tracking.

---

## Document Relationships

```
prd_text.txt (v1.0 baseline)
    ↓ extends
addendum/AIMoveMaker_PRD_Addendum_MovieMaker_v1.2.md (build contract)
    ↓ analyzed by
MovieMaker_Plan.md (gap analysis & phased roadmap)
    ↓ mapped to codebase by
MovieMaker_Integration_Map.md (file-by-file integration plan)
```

**Previous Version:**
- history/AIMoveMaker_PRD_Addendum_MovieMaker_v1.1.md (superseded by v1.2)

---

## Conventions

All PRD documents follow the build-contract convention system:

| Convention | Meaning |
|------------|---------|
| **MUST** | Non-negotiable. Build exactly as specified. |
| **MUST NOT** | Explicitly prohibited. |
| **SHOULD** | Strong recommendation. Deviate only with documented justification. |
| **MAY** | Optional. |
| **TBD** | Deferred or not yet verified. Do not implement guessed behavior. |
| **estimate** | Effort/duration figure that is an engineering estimate, not a commitment. |

---

## Key Architectural Decisions (as of 2026-11-26)

1. **Multi-user foundation preserved:** Redis 7, Celery 5, JWT/OAuth, Creative/Engineer RBAC, and Redis pub/sub WebSockets remain as core platform infrastructure.

2. **Project-level core model lock:** Every project is immutable to one core video model family (`minimax_h3`, `ltx_2_5`, or `wan_bernini`) set at creation. Migration requires cloning into a new project.

3. **Runtime-agnostic policy:** Standard Diffusers (≥ 0.40) or SGLang (≥ 0.5.17) only. ComfyUI compatibility is explicitly not a goal. ComfyUI-packed models and LoRAs are converted once at import.

4. **Import Model with safety gate:** Civitai/local intake → header detect → convert → quantize (FP8/NVFP4) → test-load + sample render → RBAC-guarded cleanup.

5. **Multi-user model library:** `global`/`user` visibility, `owner_id`, Import restricted to Admin/Engineer, deletion requires Admin or owner + zero active references.

6. **Admin secrets in `.env`:** Server secrets (`VASTAI_API_KEY`, `HF_TOKEN`, `CIVITAI_API_KEY`, `SMTP_*`) move to admin-only atomic `.env` (mode `0600`). Optional per-user overrides permitted.

7. **Native Redis installers:** Ubuntu `redis-server`, Windows Memurai/native Redis. Docker is explicitly not used.

8. **Celery GPU routing:** Per-engine queues (`gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`) with workers in isolated `.venvs/<engine>`.

---

## Effort Estimate Summary

| Phase | Estimate | Focus |
|-------|----------|-------|
| Phase 0 | 4–6 days | H3 + LoRA + converter round-trip proof on RTX 5090 |
| Phase 1 | 5–7 days | Project lock, Celery queues, multi-user library |
| Phase 2 | 7–10 days | Import Model, converter, quantizer, RBAC safety gate |
| Phase 3 | 10–14 days | H3 Celery GPU workers, Seed Hunter stages, continuity, upscaler |
| Phase 4 | 6–9 days | H3 Prompt IDE, RefMods, LoRA governance, ASR/SAM |
| Phase 5 | 9–12 days | NLE seam finishing, Vast.ai VM, native Redis installers |
| **Total** | **41–58 days** | Phased build from spike to production |

---

## Intended Readers

- **Primary:** AI build agent (all requirements stated as fact, no inference required)
- **Secondary:** Human engineering team
- **Tertiary:** Product stakeholders and technical reviewers

---

**Classification:** Independent Project — Confidential  
**Repository:** SidneyAnderson/AIMoveMaker  
**Authoritative Baseline:** `PRD/prd_text.txt`

---

*Last Updated: November 26, 2026*
