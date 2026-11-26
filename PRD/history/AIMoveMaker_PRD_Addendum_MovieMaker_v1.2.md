PRODUCT REQUIREMENTS DOCUMENT ADDENDUM
AI Movie Maker
Movie Maker Layers

| Field | Value |
|---|---|
| Version | 1.2 — Addendum to PRD v1.0 |
| Status | Specification for the v1.2 build — not yet implemented |
| Date | November 26, 2026 |
| Changelog | v1.2 (November 26, 2026): Moved the committed LTX core from LTX 2.3 to LTX-2.5 (`ltx_2_5` / `ltx_2_5_default`); pinned Diffusers ≥ 0.40 for LTX-2.5 (`LTX2Pipeline` / `LTX25AutoBlocks`) and Wan Animate 2 (`WanAnimate2Pipeline`); IC-LoRA, Prompt Relay, and Bernini-R-S2V remain TBD capability flags; Wan 2.5–3.0 and Hailuo are hosted-only and out of scope for local engines. |
| Classification | Independent Project — Confidential |
| Intended Reader | AI Build Agent + Engineering Team |
| Baseline | PRD v1.0 — March 13, 2026; updated May 31, 2026; Implemented v1 — Regression verified |
| Authoritative baseline text | `PRD/prd_text.txt` in the SidneyAnderson/AIMoveMaker repository |
| Related plan Pages | Gap analysis and phased plan (updated 2026-11-25 for multi-user). An integration map Page was referenced during drafting; it could not be opened from this environment, so multi-user specifics are taken from the updated plan Page and the settled decisions listed in Section A0.2. |

---

# Section A0: How to Read This Addendum

This document is a build contract for the Movie Maker layers that sit on top of the implemented AI Movie Maker v1 platform. It extends PRD v1.0. It does not rewrite or replace that document.

Every decision is stated as fact when it has been settled. Where a model capability, numeric limit, converter formula, runtime choice, or schedule has not been verified on the target hardware, this addendum marks it **TBD** or **estimate**. The build agent MUST NOT invent model capabilities, frame-rate limits, resolution ceilings, or quality claims that are not stated here or in the v1 baseline.

The primary reader is an AI build agent; the secondary reader is a human engineering team.

## A0.1 Conventions

This addendum inherits the v1 conventions from Section 0 of `PRD/prd_text.txt` without change.

| Convention | Meaning | Example |
|---|---|---|
| MUST | Non-negotiable. Build exactly as specified. | The system MUST keep Redis 7 and Celery 5. |
| MUST NOT | Explicitly prohibited. | The system MUST NOT add a ComfyUI runtime. |
| SHOULD | Strong recommendation. Deviate only with documented justification. | Import conversion SHOULD stream weights so a 37 GB file does not exhaust 32 GB VRAM. |
| MAY | Optional. | The Admin MAY keep a converted model's original file. |
| TBD | Not yet decided or not yet verified. Do not implement a guessed behavior as if it were required. | Direct import of ComfyUI `int8_HQ` ConvRot checkpoints — TBD pending Phase 0. |
| estimate | Effort or duration figure that is an engineering estimate, not a commitment. | Phase 2 is 7–10 days (estimate). |

Field type notation is identical to v1 Section 0:

| Notation | Type | Notes |
|---|---|---|
| string | VARCHAR / TEXT | Use TEXT unless length noted |
| uuid | UUID v4 | All primary keys |
| int | INTEGER (32-bit) | |
| float | FLOAT | Use NUMERIC(10,4) for cost fields |
| bool | BOOLEAN | |
| json / jsonb | JSONB (PostgreSQL) | Indexed where noted |
| datetime | TIMESTAMP WITH TIME ZONE | Always UTC |
| enum(...) | Constrained string | Values in parentheses |
| FK(Entity) | Foreign key | Cascade rules noted per field |

Acceptance criteria format: GIVEN [precondition] WHEN [action] THEN [outcome]. Every feature section ends with acceptance criteria. The build is complete for a feature when all its criteria pass.

Agent Note: Where this document or v1 names a library, framework, or tool, use exactly that. Do not substitute alternatives. Where this addendum and v1 conflict on a row listed in Section A2, this addendum wins for that row only. All other v1 requirements remain in force.

## A0.2 Settled Decisions and Provenance

The following decisions are settled as of November 25, 2026. They supersede any earlier draft that assumed a single-user local queue, a `solo_creator` bypass of RBAC, or a 35–52 / 39–56 day estimate.

1. Multi-user is required. Redis 7, Celery 5, JWT/OAuth authentication, Redis pub/sub progress, the four personas (Admin, Creative, Engineer, Viewer), and the v1 role-gated project state machine MUST be kept and extended. They MUST NOT be replaced with a single-user SQLite worker queue.
2. Each project locks one core video model family at creation (`minimax_h3`, `ltx_2_5`, or `wan_bernini`). The choice is immutable in place. Migration requires cloning into a new project.
3. The application is runtime-agnostic. Official / standard-layout weights load through Diffusers or SGLang. ComfyUI compatibility is explicitly not a goal. ComfyUI-packed checkpoints and ComfyUI/Kohya LoRAs are converted once at import into the standard Diffusers layout.
4. Import Model accepts a Civitai download or a local file, detects layout from the safetensors header, converts and quantizes (fp8 or NVFP4) in the same step, runs a test-load plus short sample-render safety gate, then prompts to delete or keep the original. The original is deleted only after that gate passes, and only under the RBAC and reference rules in Section A6.
5. Visibility for models and LoRAs is `global` or `user`, with `owner_id` on both registries.
6. Import Model is limited to Admin and Engineer. Deleting or moving an original is allowed only for an Admin or the owner, and only when no active project or job references it.
7. Shared secrets live in an Admin-managed server `.env` (mode `0600`). Optional per-user overrides are permitted. Secret values MUST still obey v1 Section 8.4: never returned in API responses (only `is_set`), never written to logs.
8. Native installers MUST install Redis without Docker: `redis-server` on Ubuntu, Memurai or a native Redis build on Windows.
9. Delivery effort is 41–58 days (estimate) across Phases 0–5, with Import Model in Phase 2. See Section A16.

Provenance used while writing this addendum:

- Authoritative v1 text: `PRD/prd_text.txt` (GitHub SHA recorded at fetch time; local clone used to read the full file after the connector truncated the download).
- Gap analysis and phase plan Page, re-read on November 25, 2026 after the multi-user correction (41–58 day estimate; phase lines in Section A16).
- Inspected safetensors headers for Civitai “H3 Eros Max” v1.0 BF16 (534 tensors) and int8_HQ (894 tensors).
- Seed Hunter v3 workflow mapping and the Fox•Fur•Essence Films walkthrough transcript (`lKmv63AKBhY`).

Requirement IDs in this addendum (PROFILE, LIB, IMPORT, LORA, GEN, PREVIEW, CONT, EDIT, QUEUE, VIS, SECRET, INSTALL, OUTPUT) are the build-contract identifiers for the new layers. They do not replace v1 section numbers.

## A0.3 Items This Addendum Does Not Decide

The following remain open and MUST be treated as TBD or as estimates, not as hidden requirements:

- Whether MiniMax H3 plus its LoRAs run cleanly outside ComfyUI on the RTX 5090 (Phase 0 gate).
- The exact algebraic reconstruction of pruned AdaLN (`adaln_basis` / `adaln_mean` / `adaln_t_table`) into full per-block Diffusers AdaLN.
- Whether Diffusers + torchao or SGLang + NVIDIA ModelOpt is the default H3 runtime on `sm_120`.
- Whether ComfyUI ConvRot `int8_HQ` files can be dequantized, or whether import MUST require the BF16 source.
- Numeric length, resolution, and FPS ceilings for each core model beyond the values documented in v1 or verified in Phase 0. Known-bad combinations MAY only be populated with combinations that have been verified or that v1 already flags.
- Standalone Diffusers/PyTorch ports of H3 RefMods and the 3D latent upscaler, which today ship as ComfyUI nodes.
- IC-LoRA, Prompt Relay, and Bernini-R-S2V (including other Bernini editing or reference features), except as optional profile capabilities that may be enabled only when a Diffusers-native pipeline actually exposes them.

---

# Section A1: Purpose, Vision, and Scope of the Addendum

## A1.1 Purpose

Movie Maker grows out of the existing, regression-verified AI Movie Maker application (v1) and absorbs the long-video, model-library, and finishing capabilities specified for Long-Video-Creator. The result is one local-first, multi-user AI film studio that takes a crew from idea to a finished, scored, and lip-synced film on local hardware, with optional Vast.ai burst as already specified in v1 Section 6.4.

This addendum specifies only the new layers and the v1 changes required to support them. Creative-domain image generation, inpainting, storyboard, handoff, snapshots, notifications, and the four-persona permission model remain as in v1 unless a row in Section A2 says otherwise.

## A1.2 End-to-End Flow (Addendum Scope)

1. An Admin creates a project and MUST select its one core video model family and workflow profile. That choice is locked for the life of the project.
2. Admin or Engineer populate the model and LoRA libraries: recursive folder scan, and/or Import Model (Civitai or local file → convert → quantize → safety gate → delete or keep).
3. The Creative persona storyboards keyframes using v1 image tools (FLUX, SDXL, and other registered image models). Image `Keyframe.model_id` is unchanged.
4. After handoff, the Engineer generates video in profile-legal modes (H3: `t2va` / `fl2va` / `ref2va`; LTX and Wan: `t2v` / `i2v` / true `v2v`). Segments may be reviewed as cheap multi-seed previews, upscaled in a second pass, continued with overlap conditioning, and accompanied by forced or voice-cloned dialogue where the engine supports it.
5. The Engineer finishes on the v1 multitrack timeline: seam color, exposure, and warmth matching, blur or zoom transitions, RIFE interpolation, spatial upscale, and export.

## A1.3 In Scope for v1.2

- Project model profiles and immutable core-model lock.
- Model library scan, missing-piece preflight, and Import Model (convert, quantize, safety gate, delete-or-keep).
- LoRA library filtering, stacking, compatibility warnings, and key conversion.
- Generation engines: MiniMax H3 (Diffusers ≥ 0.40 or SGLang Diffusion), LTX-2.5 via Diffusers ≥ 0.40 (`LTX2Pipeline` / `LTX25AutoBlocks`), Wan 2.2 via Diffusers, and Wan Animate 2 via `WanAnimate2Pipeline` (Diffusers ≥ 0.40), with true video-to-video.
- Seed Hunter-style Stage-1 previews, Stage-2 latent upscale, continuation, and quality-reset helpers, for H3 projects.
- Timeline seam finishing, blur/zoom transitions, RIFE (already in v1), upscale, and export.
- Multi-user extensions: per-engine Celery queues, a GPU mutex, `global`/`user` visibility, Import/delete RBAC, Admin-managed `.env` secrets with optional per-user overrides, and Docker-free Redis installers for Windows and Ubuntu.

## A1.4 Out of Scope for v1.2

All v1 Section 1.3 / Section 10.2 backlog items remain out of scope unless Section A17 explicitly promotes them. In particular this addendum does NOT require:

- A ComfyUI runtime, ComfyUI node graph, or Docker-based deployment (v1 Section 3.4 already forbids Docker for standard deployment; this addendum also forbids Docker for Redis).
- In-place switching of a project's core video model.
- Mixing MiniMax H3 and Wan (or LTX) segments on one project timeline.
- Real-time CRDT/OT multi-user co-editing (v1 Section 10.2). The fixed-crew model and presence behavior from v1 / Section 14 stay as they are.
- A community model marketplace or cloud-native SaaS tenancy.
- Full color-grading / LUT suites beyond the seam-matching and transition tools in Section A10.
- Invented support for IC-LoRA, Prompt Relay, or Bernini-R-S2V (and other Bernini editing or reference features) until a Diffusers-native path is verified (TBD).
- Hosted-only video APIs as local generation engines, including Wan 2.5, Wan 2.6, Wan 2.7, Wan 3.0, and MiniMax Hailuo. Local engines remain MiniMax H3, LTX-2.5, and Wan 2.2 (with Wan Animate 2).

---

# Section A2: Changes to v1

Where a row says **Unchanged**, implementers MUST follow v1. Where a row says **Extends**, implement the v1 behavior plus the added requirements. Where a row says **Modifies**, the addendum requirement replaces the named v1 behavior only.

| v1 section | Change type | Summary |
|---|---|---|
| §0 Conventions, field types, AC format | Unchanged | Inherited in full. |
| §1.1–1.2 Vision and value | Extends | Platform remains a web-based local-first studio; adds long-video continuity, Import Model, and a project-level core model. |
| §1.3 v1 Scope | Modifies (narrow) | Color grading / LUT tools, transition effects, and subtitle / caption generation were v2. This addendum promotes a narrow subset: seam color/exposure/warmth matching, blur/zoom seam transitions, and (Phase 4) caption tracks / ASR. Full LUT suites, arbitrary transition packs, and a marketplace remain v2. See Section A17. |
| §2.1 Personas | Unchanged | Admin, Creative, Engineer, Viewer. Solo Mode (one user holding Admin + Creative + Engineer) remains. No `solo_creator` mode that bypasses RBAC is added. |
| §2.2 Feature Access Matrix | Extends | New rows for Import Model, convert/quantize, delete or move originals, model-folder scan roots, visibility changes, and workflow-profile selection. See Section A4.2. |
| §2.3 Project State Machine | Unchanged | Draft → CreativeActive → PendingHandoff → EngActive → PendingReturn / Completed, with the same lock rules. Admin MAY still force any transition. Import Model is system-scoped (not gated by project state) but is role-gated. Video generation remains Engineer-only and still requires EngActive (or Admin). |
| §2.4 User lifecycle, OAuth, passwords | Unchanged | |
| §3.1 Architecture table | Extends | Keep FastAPI, React 18, Vite 5, SQLAlchemy, SQLite dev / PostgreSQL 15+ prod, Celery 5, Redis 7. Add: Diffusers ≥ 0.40 for H3, LTX-2.5 (`LTX2Pipeline` / `LTX25AutoBlocks`), and Wan Animate 2 (`WanAnimate2Pipeline`); optional SGLang Diffusion ≥ 0.5.17; torchao; NVIDIA ModelOpt; per-engine virtualenvs; GPU mutex. “No ComfyUI dependency” is restated as a hard rule for inference and for saved artifacts. |
| §3.2 Hardware Baseline | Modifies | CUDA requirement becomes 12.8 or newer (v1 said 12.4+). OS becomes native Windows and Ubuntu 22.04+ (including the MesaAI WSL Ubuntu 22.04 box). GPU, RAM, and sm_120 inductor warning are unchanged. PyTorch MUST be a build that supports `sm_120` from a CUDA 12.8+ index. |
| §3.3 Hardware Profile Service | Extends | MUST also report FP8 / NVFP4 quantization capability, sparse-attention backend availability, and a llama-server VRAM budget when an LLM assistant is configured. `eager` compile on sm_120 remains mandatory. |
| §3.4 Deployment — No Docker | Modifies | Redis MUST be installed natively, not via `docker run redis:7`. Ubuntu: `redis-server`. Windows: Memurai or a native Redis build, run as a service. The Vast.ai remote-side isolation exception in v1 is unchanged. |
| §3.5 Directory structure | Extends | Add library roots, converted-model storage, import staging, archive roots, and `.venvs/<engine>`. Install root on Windows is configurable (default TBD in the installer). Path-traversal rules in §8.4 are extended to those roots. |
| §4 Creative Domain | Unchanged, with one clarification | `Keyframe.model_id` remains the image-model selector (FLUX, SDXL, and other registered image models). It is not used to select a core video family. |
| §5.1 Timeline Editor | Extends | Adds seam grading, blur/zoom transitions, optional cadence limiting, and a `caption` track type in Phase 4. |
| §5.2 Video Generation | Modifies | Core model is chosen at project creation, not freely per clip. H3 modes `t2va` / `fl2va` / `ref2va` are added. `v2v` MUST be true video-to-video and MUST NOT alias to `i2v`. Supported families become MiniMax H3, LTX-2.5, and Wan/Bernini, each behind a workflow profile. |
| §5.2.1 Supported Video Models | Extends | Adds MiniMax H3. The committed LTX core is LTX-2.5 (not the earlier LTX-2.3 path, and not the retired LTX-Video 0.9.x line). WAN 2.2 remains the local Wan flagship, with Wan Animate 2 available via Diffusers. VRAM figures from v1 for LTX (~14 GB at 720p) and WAN (~24 GB+ at 720p, flag above 28 GB) remain until Phase 0/3 re-measures them on the current models. H3 VRAM is TBD pending Phase 0. |
| §5.2.2 Parameters | Extends | Profile validator enforces legal (mode, resolution, frames, fps) tuples. H3 is guidance-distilled: `cfg_scale` MUST be hidden and ignored for H3 profiles. H3 uses dual schedulers (video shift 12.0, audio shift 3.0, from Diffusers documentation). |
| §5.2.4 RIFE | Unchanged | Still optional per VideoClip, 2x/4x, scene-cut detect. |
| §5.3 Audio Generation | Extends | v1 MusicGen, AudioGen, Coqui TTS, and wav2lip remain. H3 joint 32 kHz stereo audio, forced-audio latent lock, and voice-cloned dialogue pre-gen are added for H3 projects. Export still resamples to the v1 export audio spec (AAC/Opus, 48 kHz stereo) unless an explicit “native H3 audio” option is added (MAY; default is resample). |
| §5.4 Render and Export | Extends | Render preflight MUST include the missing-piece library check and seam/transition settings. Native segment specs are distinct from final NLE export targets. |
| §6.1 Model Registry | Extends | Adds recursive scan, companion-pack preflight, `visibility`, `owner_id`, `base_model`, layout/quantization metadata, and the Import Model pipeline. Existing HuggingFace / Civitai / local registration paths remain for already-standard artifacts. |
| §6.1.3 VRAM Profiler | Extends | Estimates MUST include quantized (fp8/NVFP4) footprints and H3 text-encoder + VAE companions. The Vast.ai confirm gate is unchanged. |
| §6.2 LoRA Registry | Extends | Adds `visibility`, `owner_id`, `base_model`, `lora_compatibility_notes`, `target_partition`, slot assignment, and key-conversion on import. Architecture filtering remains. |
| §6.3 Job Queue | Extends | Keep a single priority order (HIGH > MEDIUM > NORMAL > LOW). Add named Celery queues `gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`, and a Redis-backed GPU mutex. New job types are listed in Section A4.3. Progress streaming via `/ws/jobs/{job_id}` is unchanged. |
| §6.4 Vast.ai | Unchanged in contract; implementation is currently a stub | v1 routing flow remains the requirement. Phase 5 MUST replace empty `offers=[]` stubs with the real VM-mode worker. |
| §6.5 Snapshots | Extends | Save/Load Job execution checkpoints (Stage-1 latents/seeds, single-family signatures, paused restore without auto-run) are separate from v1 project snapshots. |
| §7.3 Project | Extends | Adds `core_video_model` and `workflow_profile_id`. `fps` / `resolution_*` remain, but MUST be consistent with the profile. |
| §7.10 Track | Extends | Phase 4 MAY add `caption` to `type`. |
| §7.11 VideoClip | Extends / Modifies | `mode` enum extended for H3. `model_id` MAY identify a checkpoint inside the project's family and MUST NOT select a different family. Adds preview, continuation, dialogue, and seam fields. |
| §7.14 Job | Extends | New `type` values; optional `celery_queue` field. |
| §7.15 ModelRegistry / §7.16 LoRARegistry | Extends | `visibility`, `owner_id`, conversion and compatibility metadata. `storage_path` remains server-side only. |
| §7.20 Setting / §7.20.1 | Modifies (secrets) | Shared provider secrets (`vastai_api_key`, `civitai_api_key`, `hf_token`, `smtp_*`, OAuth client secrets) move from the SQLite/Postgres `Setting` value store into an Admin-managed server `.env`. Non-secret settings remain in `Setting`. Optional per-user overrides are stored as user-scoped secrets, never returned in API bodies. The `is_set` pattern from v1 §8.4 remains. |
| §8 NFRs | Extends | Additional VRAM, storage, and importer performance targets. Path allow-lists expand beyond `/opt/aimoviemaker/`. |
| §9.1 / §13 APIs | Extends | New endpoints for profiles, imports, scans, preflight, previews, continuation, seam grade, and clone-to-migrate. `POST /projects` requires the core model and profile. |
| §9.3 Civitai | Extends | Used as an Import Model intake source, still server-side, still `X-API-Key`, still `nsfw=true`, still no application-level content filter. |
| §10.1–10.2 Open items and v2 backlog | Touched | See Section A17. Items not listed there remain deferred. |
| §11 UI | Extends | Profile picker at project creation, Import Model wizard, library visibility badges, preview picker, continuation and seam inspectors. Design language from §11 remains the default unless the Phase 5 theme is applied. |
| §12 Build instructions | Extends | New Alembic migrations, new Celery worker processes, new installer scripts, Phase 0 hardware spike as a gate. |
| §13.2, §13.8, §13.9 schemas | Extends | Fields added as specified in Section A12. `storage_path` MUST still never appear in responses. |
| §14 May 31, 2026 implementation addendum | Unchanged | v1 remains implemented and regression-verified. This v1.2 addendum starts from that baseline. |

---

# Section A3: Environment and Architecture Extensions

*Extends v1 Sections 3, 8.4, and 12.6.*

## A3.1 Target Environment

| Item | Requirement |
|---|---|
| Local GPU | NVIDIA RTX 5090 (Blackwell, `sm_120`), 32 GB VRAM — same as v1 §3.2 |
| System RAM | 64 GB — same as v1 |
| Operating systems | Native Windows, and Ubuntu 22.04+ (including the MesaAI WSL Ubuntu 22.04 box) |
| Python | 3.11+ |
| CUDA | 12.8 or newer (modifies v1 §3.2, which required 12.4+) |
| PyTorch | A stable or nightly build whose CUDA 12.8+ wheel supports `sm_120` |
| Docker | MUST NOT be used for standard deployment, local Redis, or local workers |
| Model formats at rest after import | safetensors in standard Diffusers layout, plus fp8 or NVFP4 quantized variants |
| GGUF | MAY be used only for components that do not need LoRA loading (for example a text encoder with no LoRA). GGUF MUST NOT be the default format for a LoRA-bearing DiT |
| Runtime for H3 | Diffusers ≥ 0.40 (`MiniMaxH3` modular pipeline and LoRA loader) and/or SGLang Diffusion ≥ 0.5.17. Default runtime is TBD after Phase 0 |
| Runtime for LTX-2.5 and Wan/Bernini | Diffusers ≥ 0.40 (`LTX2Pipeline` / `LTX25AutoBlocks` for LTX-2.5; `WanPipeline` for Wan 2.2; `WanAnimate2Pipeline` for Wan Animate 2). Upgrade from the v1 `diffusers==0.33.1` pin. The minimum MUST be pinned in `requirements.txt` |
| Attention on sm_120 | `torch.compile` MUST use the `eager` backend. xformers MUST be conditionally loaded with silent SDPA fallback, as in v1 §3.2 |

INSTALL-01. The system MUST deploy as native virtual environments on the host OS, with isolated `.venvs/<engine>` environments at least for `h3`, `ltx`, `wan`, `audio`, and `import`.

INSTALL-02. The Ubuntu installer (`scripts/install.sh`, extending `setup.sh` / `start.sh`) MUST install and start `redis-server` natively, create the venvs, install pinned requirements, run Alembic migrations, and seed the bootstrap Admin as in v1 §2.4.1.

INSTALL-03. The Windows installer (`scripts/install.ps1`) MUST install and start Redis without Docker, using Memurai or a native Redis build, running it as a Windows service. It MUST also create the venvs, run migrations, and seed the bootstrap Admin.

INSTALL-04. `start.sh` / the Windows start script MUST start Redis if it is not running, start the Celery workers for the queues in Section A4.3, and start the FastAPI server. All processes MUST log in structured JSON as in v1 §8.1.

## A3.2 Runtime-Agnostic Rule

GEN-RUNTIME-01. The system MUST NOT depend on ComfyUI, ComfyUI custom nodes, or ComfyUI-specific quantized kernels (`comfy_quant`, ConvRot) at inference time.

GEN-RUNTIME-02. Saved library artifacts MUST be in standard Diffusers (or SGLang-readable) layout. ComfyUI-packed sources are allowed only as import inputs.

GEN-RUNTIME-03. A React SPA served by FastAPI remains the UI shell (v1 §3.1). The system MAY later wrap that SPA in a single-process desktop shell (`pywebview` or Tauri). The system MUST NOT replace the v1 React timeline with a PySide6 rewrite in v1.2.

## A3.3 Path and Storage Rules

INSTALL-05. On Linux the default install root remains `/opt/aimoviemaker/` unless the installer is given another root. On Windows the default root is chosen by the installer and MUST be documented (exact default path TBD).

INSTALL-06. File paths in API requests (`local_path`, archive folder, scan roots) MUST be validated against an allow-list of configured roots. Path traversal MUST be rejected with `error_code` `path_traversal`. This extends v1 §8.4 beyond `/opt/aimoviemaker/outputs/` and `/opt/aimoviemaker/models/`.

INSTALL-07. Import staging, converted-library storage, and original-archive folders MUST be distinct directories. The importer MUST write converted artifacts to library storage, never over the source file.

---

# Section A4: Personas, Permissions, Queue Routing, and Secrets

*Extends v1 Sections 2, 6.3, 7.20, 8.4, and 8.5. Multi-user is required.*

## A4.1 Multi-User Foundation (Unchanged)

RBAC-01. The system MUST retain the four personas and the counts in v1 §2.1: Admin (system-wide, unlimited), Creative (exactly one per project), Engineer (exactly one per project), Viewer (unlimited per project). A single user MAY still hold Admin + Creative + Engineer (Solo Mode). Feature surfaces for all held roles remain available concurrently, subject to the project state machine.

RBAC-02. The project state machine in v1 §2.3 is unchanged. In `creative_active`, Engineer is read-only on the project. In `eng_active`, Creative is read-only. In `pending_handoff` or `pending_return`, both roles are read-only on the project. Admin always has full project access. Import Model and library administration are system-scoped operations (see A4.2) and are not locked by project state, but they remain role-gated.

RBAC-03. The system MUST NOT add a mode that bypasses the state machine or role checks. Frontend gating remains UI convenience only; server-side checks remain mandatory (v1 §8.4).

## A4.2 Extended Feature Access Matrix

v1 §2.2 remains in force. The following rows are added.

| Feature | Admin | Creative | Engineer | Viewer |
|---|---|---|---|---|
| Select core video model and workflow profile at project creation | Yes | No | No | No |
| Change a project's core video model in place | No (clone only; Admin clones) | No | No | No |
| Manage scan roots and run a library scan | Yes | No | Yes (run scan on roots they can read; scan-root create/delete is Admin) | No |
| Import Model (Civitai or local), convert, quantize | Yes | No | Yes | No |
| Choose delete or keep/move after a passing safety gate | Yes, or as owner | No | Yes, only as owner, and only if unreferenced | No |
| Change `visibility` of a library entry | Yes (any entry) | No | Yes (entries they own) | No |
| Delete a library entry | Yes | No | Yes (own `user`-visible entries only, and only if unreferenced) | No |
| Use a `global` model or LoRA in a project they can edit | Yes | Yes (image models / storyboard) | Yes | No (read-only view of names MAY be shown) |
| Use another user's `user`-visible model or LoRA | Yes | No | No | No |
| Generate H3 / LTX / Wan video, previews, continuation | Yes (in Engineer role or as Admin override) | No | Yes (project in EngActive) | No |
| Seam grade, transitions, upscale, export | Yes (as above) | No | Yes (EngActive) | No |

## A4.3 Celery Queues and GPU Mutex

*Extends v1 §6.3. Priority order HIGH > MEDIUM > NORMAL > LOW is unchanged.*

QUEUE-01. The system MUST declare the following Celery queues, each consumed by a worker that uses the matching `.venvs/<engine>` when GPU inference is required:

| Queue name | Worker venv | Typical job types |
|---|---|---|
| `gpu_h3` | `.venvs/h3` | H3 video/audio generation, H3 previews, H3 latent upscale, H3 sample-render safety gates, H3 continuation |
| `gpu_ltx` | `.venvs/ltx` | LTX-2.5 generation and LTX sample-render gates |
| `gpu_wan` | `.venvs/wan` | Wan/Bernini generation and Wan sample-render gates |
| `gpu_audio` | `.venvs/audio` | v1 local audio (MusicGen, AudioGen, Coqui, wav2lip) and non-H3 dialogue tools |
| `import_cpu` | `.venvs/import` | Header detection, key rename, QKV split, AdaLN expansion, LoRA key conversion, CPU-staged weight rewrite. MUST NOT run GPU inference |

QUEUE-02. Existing v1 job types (image generation, inpaint, outpaint, interpolation, render, export) MUST be routed to an appropriate queue. Image generation MAY share a GPU queue or a dedicated `gpu_image` queue. If `gpu_image` is added, it MUST also acquire the GPU mutex. The name `gpu_image` is MAY; it is not required if image jobs are scheduled on a mutex-protected default GPU worker. This addendum does not invent a sixth required queue name.

QUEUE-03. The local RTX 5090 MUST be guarded by a Redis-backed GPU mutex so that at most one mutex-holding task runs on the local GPU at a time. Tasks on `gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio` (when the audio model needs the NVIDIA GPU), image GPU jobs, GPU-side quantization, and sample-render safety gates MUST acquire the mutex before allocating VRAM and MUST release it in a `finally` block, including on cancellation and worker crash recovery (the lock MUST have a TTL and a heartbeat).

QUEUE-04. `import_cpu` tasks MUST NOT acquire the GPU mutex. If an import reaches a GPU-requiring step (sample render, and quantization if it cannot run fully on CPU), that step MUST be enqueued on the matching `gpu_*` queue and MUST acquire the mutex. The parent import job remains one logical Job in the v1 `Job` table and MUST show combined progress on `/ws/jobs/{job_id}`.

QUEUE-05. New `Job.type` enum values MUST include at least: `model_import`, `model_scan`, `sample_render`, `video_preview`, `latent_upscale`, `video_upscale`, `video_continuation`, `dialogue_generation`, `seam_grade`. v1 types remain.

QUEUE-06. Progress, retry, cancel, and Admin override behavior remain as in v1 §6.3. Import and sample-render failures are critical when they would otherwise have deleted a source file: the original MUST be left untouched (see IMPORT-14).

## A4.4 Visibility

VIS-01. `ModelRegistry` and `LoRARegistry` MUST gain `visibility enum(global, user)` and `owner_id FK(User)`. `added_by` from v1 remains (the acting user at insert time). On import, `owner_id` defaults to the importing user.

VIS-02. `visibility='global'` entries are visible to every authenticated user who is allowed to list models or LoRAs under v1 (Admin, Engineer, Creative for use; Viewer MAY see display names on a project they can open, but cannot manage).

VIS-03. `visibility='user'` entries are visible only to `owner_id` and to any Admin.

VIS-04. Default visibility: Admin imports default to `global`; Engineer imports default to `user`. The importer MAY choose the other value at import time, subject to A4.2.

VIS-05. GET list endpoints MUST filter by these rules server-side. A request for an entry the caller cannot see MUST return HTTP 404 (not 403), to avoid leaking existence, except for Admin.

## A4.5 Secrets

*Modifies v1 §7.20.1 storage for shared secrets; keeps v1 §8.4 disclosure rules.*

SECRET-01. Shared provider secrets MUST be stored in an Admin-managed server `.env` file with permissions `0600` (Owner read/write only on POSIX; an equivalent ACL on Windows). Keys include at least: `VASTAI_API_KEY`, `CIVITAI_API_KEY`, `HF_TOKEN`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `DISCORD_OAUTH_CLIENT_ID`, `DISCORD_OAUTH_CLIENT_SECRET`, `ELEVENLABS_API_KEY`, `SUNO_API_KEY`.

SECRET-02. The `Setting` table remains for non-secret global and user preferences (for example `default_gpu_target`, `vram_safety_margin_pct`, `default_video_duration_s`). Secret values MUST NOT be written back into `Setting.value`.

SECRET-03. A user MAY supply an optional per-user override for a subset of secrets that are safe to override (Civitai, HuggingFace, and personal LLM provider keys). Vast.ai and SMTP MAY be restricted to Admin-only; if so, the UI MUST not offer a per-user override for those keys. Override storage MUST be a user-scoped secret store (file or encrypted table). Values MUST never be returned by the API; only `is_set: bool` and `source: enum(server_env, user_override, unset)` MAY be returned.

SECRET-04. Resolution order: process environment (deployment inject) > user override (when the acting user is the job owner) > Admin server `.env`. The Admin settings UI SHOULD show which source is active, without showing the secret.

SECRET-05. All v1 log-redaction and “invalid API key” error rules remain. Civitai, HuggingFace, and Vast.ai keys MUST be used server-side only.

## A4.6 Error States (Multi-User and Queue)

| Condition | HTTP / job result | error_code |
|---|---|---|
| Caller lacks role for Import Model | 403 | `insufficient_role` |
| Caller cannot see a `user`-visibility entry | 404 | `not_found` |
| Delete or move requested by a non-owner non-Admin | 403 | `insufficient_role` |
| Delete or move requested while a project or job references the file or library entry | 409 | `resource_in_use` |
| GPU mutex not acquired before TTL and job cancelled by user | job `failed` or remains queued per retry policy | `gpu_mutex_timeout` |
| Redis unavailable at startup | process MUST fail health checks and MUST NOT accept generation jobs | `redis_unavailable` |
| Secret missing when a provider call is attempted | 400 or job `failed`, modal as in v1 | `secret_not_configured` |

## A4.7 Acceptance Criteria

- GIVEN a running production install WHEN an operator inspects process lists THEN Redis (native `redis-server` or Memurai / native Windows Redis) and Celery workers for `gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, and `import_cpu` are running AND no Redis container is required.
- GIVEN two GPU jobs of different families are queued WHEN the local mutex is held by the first job THEN the second job remains queued and MUST NOT allocate VRAM until the mutex is released.
- GIVEN an Engineer imported a `user`-visibility model WHEN a second Engineer calls GET `/models/{id}` THEN the response is HTTP 404.
- GIVEN an Admin imported a `global` model WHEN a Creative lists image-or-video models they are allowed to use THEN the model appears.
- GIVEN a non-Admin Engineer who does not own a library entry WHEN they request delete or move of its original file THEN the API returns HTTP 403 with `error_code` `insufficient_role` AND the file is unchanged.
- GIVEN Solo Mode (one user holds Admin + Creative + Engineer) WHEN that user works a project through the v1 state machine THEN handoff locks still apply unless the same user is performing the Admin force-transition; RBAC is not bypassed.
- GIVEN `CIVITAI_API_KEY` is set only in the Admin `.env` WHEN GET `/settings` is called THEN the response shows `is_set=true` and MUST NOT include the key material.

# Section A5: Project Model Profiles

*Extends v1 Sections 5.2, 7.3, 7.11, and 13.2. Implements PROFILE and OUTPUT requirements.*

## A5.1 Requirements

PROFILE-01. Every project MUST have exactly one core video model family, stored as `Project.core_video_model enum(minimax_h3, ltx_2_5, wan_bernini)`. The value is selected at creation and is immutable in place.

PROFILE-02. Every project MUST have exactly one `workflow_profile_id FK(WorkflowProfile)` selected at creation. The profile MUST belong to the chosen `core_video_model`. The pair is immutable in place.

PROFILE-03. The system MUST NOT allow MiniMax H3 and Wan, or H3 and LTX, or LTX and Wan, to be used as video generators inside the same project. Image models used on keyframes (FLUX, SDXL, and other `ModelRegistry.type='image'` entries) are independent of this lock.

PROFILE-04. `VideoClip.model_id` MAY point at a specific `ModelRegistry` row only when that row's family matches `Project.core_video_model` (for example, base MiniMax H3 versus an imported H3 fine-tune such as Eros Max). PATCH/POST that would assign a different family MUST be rejected with `error_code` `core_model_mismatch`.

PROFILE-05. Changing core family or workflow profile requires cloning: `POST /projects/{id}/clone` with a new `core_video_model` and `workflow_profile_id`. The clone copies storyboard and timeline metadata. Video outputs, latents, and continuation caches from the source project MUST be marked stale and MUST NOT be silently reused as if they were valid under the new family.

PROFILE-06. The selected `WorkflowProfile` drives available modes, legal resolutions (or megapixel targets), legal frame counts, legal FPS values, scheduler controls, and LoRA partitions. The UI MUST hide or disable controls the profile does not support (for example, `cfg_scale` on H3; `ref2va` reference slots on a profile that does not include them).

PROFILE-07. In-place mid-project engine swapping and mixed-model timeline assembly are out of scope. There is no migration-preview UI that rewrites an open timeline onto another family.

OUTPUT-01. A shared validator MUST run in both the API and the GPU worker. It MUST reject (mode, width, height, frames, fps, duration) combinations that the profile marks illegal, with `error_code` `profile_limit_violation` and a message that names the violated limit.

OUTPUT-02. Native segment generation specs are distinct from final NLE export targets in v1 Section 5.4.3. A project MAY export at 1080p/24 even if H3 previews were generated at 0.2-0.4 MP, provided the Stage-2 or spatial-upscale path produced a compatible master, or the Engineer explicitly exports a lower-resolution master.

OUTPUT-03. Known-bad combinations are stored on the profile (`blocked_combinations jsonb`). The validator MUST block them with `error_code` `known_bad_combination`. The shipped list MUST only contain combinations that v1 already flags or that Phase 0/3 has verified as bad. Implementers MUST NOT invent additional blocked combinations.

OUTPUT-04. Until Phase 0/3 verifies additional numeric ceilings, the following are the only numeric generation constraints this addendum states as requirements:

- v1 defaults remain: project/timeline default 1280x720, 24 fps, default clip duration from `default_video_duration_s` (4 seconds).
- v1 WAN 2.2 warning remains: jobs estimating more than 28 GB VRAM at 720p MUST offer Vast.ai routing before queueing.
- For `minimax_h3` profiles, generation frame counts MUST snap to the 17n+5 series used by Seed Hunter v3 (5, 22, 39, 56, ...) unless Phase 0 demonstrates that other counts are valid. Whether 17n+5 is a hard model constraint or a continuity convention is TBD; it is still enforced for H3 projects in v1.2 until that TBD is resolved.
- For `minimax_h3` Stage-1 previews, the default target is 0.2-0.4 megapixels at 24 fps, from the Seed Hunter v3 workflow. Stage-2 / single-pass defaults are 1.0-2.0 megapixels. These are workflow defaults, not independently verified model maxima.
- All other family-specific maxima (maximum native duration, maximum official resolution, legal FPS sets for LTX-2.5 and Wan) are TBD and MUST be filled into `WorkflowProfile` from vendor documentation or Phase 0/3 measurement before those presets are marked `is_verified=true`. Unverified presets MUST have `is_verified=false` and the UI SHOULD label them as unverified.

## A5.2 Shipped Workflow Profiles (Initial Set)

The system MUST ship at least one profile per family. Fields that are not verified are left TBD in data, not guessed in code.

| profile_key | core_video_model | Modes the UI may expose | Notes |
|---|---|---|---|
| `h3_default` | `minimax_h3` | `t2va`, `fl2va`, `ref2va`, plus continuation as a generation flow rather than a mixed-family mode | Joint video + 32 kHz stereo audio, from Diffusers MiniMax-H3 documentation. Dual partitions: `transformer/` for `t2va`/`fl2va`, `transformer_ref/` for `ref2va`. Guidance-distilled (no CFG). Dual schedulers: video shift 12.0, audio shift 3.0. |
| `ltx_2_5_default` | `ltx_2_5` | `t2v`, `i2v`, `v2v` | LTX-2.5 via Diffusers ≥ 0.40 (`LTX2Pipeline` / `LTX25AutoBlocks`). Joint audio and Gemma 4 text encoding are part of that pipeline. Prompt Relay and IC-LoRA are TBD and MUST be enabled only if the pinned Diffusers pipeline exposes them. |
| `wan_bernini_default` | `wan_bernini` | `t2v`, `i2v`, `v2v` | v1 WAN 2.2 path, extended as Diffusers support allows. Wan Animate 2 is available via `WanAnimate2Pipeline` (Diffusers ≥ 0.40) and MAY be enabled on the profile. Bernini editing and Bernini-R-S2V remain TBD and MUST be enabled only if a Diffusers-native pipeline exposes them. Hosted Wan 2.5–3.0 APIs are out of scope for local engines. |

Admin MAY register additional profiles. A profile MUST NOT advertise a mode that the runtime adapter does not implement.

## A5.3 Data Model

### A5.3.1 New entity `WorkflowProfile`

| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| profile_key | string UNIQUE | Machine-readable, e.g. `h3_default`. |
| display_name | string | |
| core_video_model | enum(minimax_h3, ltx_2_5, wan_bernini) | |
| supported_modes | jsonb | Array of mode strings. |
| legal_resolutions | jsonb | Array of `{width:int, height:int, megapixels:float?, label:string, stage:enum(preview,native,export)?}`. Empty array means unverified — allow v1 defaults only. |
| legal_fps | jsonb | Array of int. Default `[24]` until verified otherwise. |
| frame_count_rule | enum(any, series_17n_plus_5, custom) | `series_17n_plus_5` required for the shipped H3 profile. |
| custom_frame_rule | jsonb nullable | Used when `frame_count_rule='custom'`. |
| blocked_combinations | jsonb | Array of objects naming illegal tuples. Default `[]`. |
| scheduler_schema | jsonb | Profile-specific scheduler controls (H3 dual shift, and so on). |
| hides_cfg_scale | bool | Default true for H3, false otherwise. |
| joint_audio | bool | True for H3. For LTX/Wan, set true only when verified. |
| native_audio_hz | int nullable | 32000 for H3. Null if the profile does not emit audio. |
| is_verified | bool | Default false until Phase 0/3 signs off. |
| notes | string nullable | Human-readable caveats. |
| created_at | datetime | |
| updated_at | datetime | |

### A5.3.2 Fields added to `Project` (v1 Section 7.3)

| Field | Type | Notes |
|---|---|---|
| core_video_model | enum(minimax_h3, ltx_2_5, wan_bernini) | Required. Immutable after insert. |
| workflow_profile_id | FK(WorkflowProfile) | Required. Must match `core_video_model`. Immutable after insert. |

## A5.4 API

- `GET /workflow-profiles?core_video_model=` — lists shipped and Admin-registered profiles. Auth required.
- `GET /workflow-profiles/{id}` — profile detail, including legal limits and `blocked_combinations`.
- `POST /projects` (modifies v1 Section 13.2) — `core_video_model` and `workflow_profile_id` are required. `fps`, `resolution_w`, and `resolution_h` MUST be consistent with the profile or the API returns 422 `profile_limit_violation`.
- `PATCH /projects/{id}` — MUST reject changes to `core_video_model` or `workflow_profile_id` with HTTP 409 `core_model_immutable`.
- `POST /projects/{id}/clone` — body `{ "title": "string", "core_video_model": "...", "workflow_profile_id": "uuid", "fps": "int?", "resolution_w": "int?", "resolution_h": "int?" }`. Admin only (project create is Admin in v1). Returns 201 `ProjectResponse` including the new ids. Cloned video clips have `render_state='unrendered'` and stale output references cleared or flagged.
- `POST /projects/{id}/videoclips` and `PATCH /projects/{id}/videoclips/{vid}` — MUST run the profile validator and family check on `mode`, `model_id`, `frames`, `fps`, and resolution params.

`ProjectResponse` is extended with `core_video_model` and `workflow_profile_id` (and SHOULD include `workflow_profile_key` and `workflow_profile_display_name` as denormalized read-only fields).

## A5.5 UI Behavior

- Project creation (Admin) MUST present a core-model selector first, then a filtered profile selector, then fps/resolution controls limited to that profile.
- After creation, the project header MUST show the locked family and profile as read-only. A "Clone project to another model..." action is available to Admin.
- Video inspectors MUST render `param_schema` plus profile-driven controls only. Unsupported modes do not appear.
- When a Creative is in Storyboard, no video-family switcher is shown. Image model pickers are unchanged.

## A5.6 Error States

| Condition | HTTP | error_code |
|---|---|---|
| Missing core model or profile on create | 422 | `core_model_required` |
| Profile does not belong to the core model | 422 | `profile_model_mismatch` |
| PATCH of core model or profile | 409 | `core_model_immutable` |
| Clip mode not in `supported_modes` | 422 | `mode_not_in_profile` |
| Illegal resolution, frames, or fps | 422 | `profile_limit_violation` |
| Combination listed in `blocked_combinations` | 422 | `known_bad_combination` |
| `VideoClip.model_id` family differs from project | 422 | `core_model_mismatch` |
| Unverified profile used without acknowledgement | MAY warn in UI; MUST not silently invent limits | `profile_unverified` (warning) |

## A5.7 Acceptance Criteria

- GIVEN an Admin on the project creation form WHEN they submit without a core video model or profile THEN the API returns HTTP 422 with `error_code` `core_model_required` AND no project row is inserted.
- GIVEN a project created with `core_video_model='minimax_h3'` WHEN an Engineer sets a VideoClip `mode` to `t2v` (an LTX/Wan mode) THEN the API returns HTTP 422 `mode_not_in_profile`.
- GIVEN a project created with `core_video_model='minimax_h3'` WHEN an Engineer assigns `VideoClip.model_id` to a registered Wan checkpoint THEN the API returns HTTP 422 `core_model_mismatch` AND the clip is unchanged.
- GIVEN a project in any state WHEN an Admin PATCHes `core_video_model` THEN the API returns HTTP 409 `core_model_immutable`.
- GIVEN an H3 project WHEN an Engineer requests a frame count that is not in the 17n+5 series THEN the API returns HTTP 422 `profile_limit_violation` (unless Phase 0 has documented that other counts are valid and the profile has been updated).
- GIVEN an existing H3 project WHEN an Admin clones it to `wan_bernini` THEN a new project is created with the new family AND cloned video clips are `unrendered` AND H3 output assets are not treated as Wan outputs.
- GIVEN an H3 profile WHEN the VideoClip inspector is shown THEN `cfg_scale` is hidden.

# Section A6: Model Library and Import Model

*Extends v1 Sections 6.1, 9.3, 9.4, and 13.8. ComfyUI compatibility is not a goal.*

## A6.1 Recursive Library Scan and Missing-Piece Preflight

LIB-01. Admin MUST be able to register one or more scan roots (shared/global roots and, optionally, per-user roots). The scanner MUST walk each root recursively.

LIB-02. The scanner MUST skip in-progress downloads and junk files, including names ending in `.crdownload`, `.tmp`, `.part`, and files that have been unchanged for less than a configurable quiet period (default 30 seconds).

LIB-03. The scanner MUST read safetensors headers (and Diffusers `model_index.json` where a directory layout is found) without loading weights into VRAM. It MUST classify each artifact as `standard_diffusers`, `comfyui_packed`, `comfyui_quant` (including ConvRot `int8_HQ`), `lora`, `companion` (text encoder, video VAE, audio VAE, latent upscaler), or `unknown`.

LIB-04. Newly discovered standard-layout models and companions SHOULD be offered for registration. ComfyUI-packed or `comfyui_quant` files MUST NOT be registered as runnable checkpoints; they MUST appear as import candidates.

LIB-05. Each registered video checkpoint MUST declare a dependency pack: the companion IDs or roles it needs to generate (for H3, at least text encoder, video VAE, and audio VAE; latent upscaler is required for Stage-2). Cross-OS stable IDs (sha256 and/or a library UUID) MUST be used so the same file is not registered twice if the root is mounted at a different path.

LIB-06. Before a generate, preview, continuation, sample-render, or Stage-2 job is queued, a preflight check MUST verify that every required companion is present, readable, and `is_active`. Failure returns HTTP 409 `error_code` `missing_model_piece` with `detail` listing the missing roles. This check is in addition to the v1 VRAM profiler.

LIB-07. Scans run as `model_scan` jobs on `import_cpu` (or a lightweight backend task) and MUST stream progress on `/ws/jobs/{job_id}`.

LIB-08. Visibility rules in Section A4.4 apply to scan-discovered registrations. Files under a user root default to `visibility='user'`; files under a shared root default to `global` after an Admin confirms registration.

## A6.2 Import Model Pipeline

Import Model extends, and does not remove, v1 Section 6.1.1 registration (HuggingFace snapshot, Civitai download, local path). When the source is already standard Diffusers layout, conversion is skipped. Quantization remains available. The safety gate is required before any original is deleted.

IMPORT-01. Only Admin and Engineer MAY start an import. Creative and Viewer MUST receive HTTP 403 `insufficient_role`.

IMPORT-02. Intake sources: (a) a Civitai model or version URL, or a Civitai model/version id; (b) a local file or directory path on a configured root. HuggingFace repo intake from v1 remains and SHOULD enter the same pipeline when the downloaded artifact needs conversion or quantization.

IMPORT-03. Civitai downloads remain server-side using the Admin-managed `CIVITAI_API_KEY` as in v1 Section 9.3. The key MUST NOT be sent to the frontend. NSFW=true remains. Rate-limit backoff remains. Downloads land in a staging directory, not in the live library path.

IMPORT-04. Before loading weights into VRAM, the importer MUST parse the safetensors header (and any file metadata) and classify layout.

IMPORT-05. Header classification MUST detect at least the following, using evidence already observed on "H3 Eros Max" v1.0:

- Standard Diffusers transformer keys (unfused Q/K/V, full per-block AdaLN).
- ComfyUI-packed H3: fused `blocks.N.attn.qkv_proj` (observed shape `[21504, 5376]` on Eros Max BF16), 50 blocks (`blocks.0..49`), hidden size 5376, pruned AdaLN tensors `adaln_basis` `[8, 2688]`, `adaln_mean` `[2688]`, `adaln_t_table` `[1025, 8]`, and per-block `adaln_proj.linear.weight` `[96768, 8]`. Eros Max BF16 metadata includes `converted_from: "diffusers MiniMax-H3 transformer"` and 534 tensors.
- ComfyUI-specific quantization: `comfy_quant`, `weight_scale`, `convrot`, `h3_native_hq.topology` (Eros Max int8_HQ: `bf16_edges_int8_interiors`, 894 tensors, `convrot_groupsize: 256`, `int8_tensorwise`).

IMPORT-06. For ComfyUI-packed BF16/FP16 (or unquantized) checkpoints, the converter MUST, in one import pass: (1) rename keys to the standard Diffusers layout; (2) split fused `attn.qkv_proj` into separate Q, K, and V projections; (3) expand pruned AdaLN into full per-block AdaLN. The exact AdaLN reconstruction formula is TBD and is a Phase 0 gate. The converter MUST fail closed if reconstruction cannot be verified.

IMPORT-07. In the same import pass, the system MUST quantize the converted (or already standard) weights to fp8 or NVFP4. Diffusers path: torchao via `TorchAoConfig`. SGLang path: NVIDIA ModelOpt. The user (Admin or Engineer) selects the target format from formats the Hardware Profile Service reports as available on the host. If NVFP4 is unavailable, the UI MUST not offer it.

IMPORT-08. Conversion and quantization of large checkpoints SHOULD be CPU-staged / streamed so a roughly 37-60 GB BF16 file does not need to reside fully in the 32 GB GPU VRAM. This is a SHOULD for Phase 0 if a streaming path is not yet proven; OOM is a failed import, not a deleted source.

IMPORT-09. ComfyUI `int8_HQ` / ConvRot sources MUST NOT be treated as standard weights. The default behavior is to reject them with `error_code` `unsupported_comfy_quant` and instruct the user to supply the BF16 counterpart. A dequantize-and-convert path is TBD (Phase 0/2) and MUST be disabled until verified.

IMPORT-10. After writing the converted/quantized artifact to library storage, the system MUST test-load it in the target non-ComfyUI runtime (Diffusers or SGLang) and run a short sample render (a small frame count and, for H3, a short joint audio check when companions are present). This is the safety gate. Sample render is a mutex-holding `gpu_*` job (QUEUE-04).

IMPORT-11. If test-load or sample render fails, the original file MUST be left untouched, the converted artifact SHOULD be retained only as a failed-import record or deleted from library storage, and the job status is `failed` with a modal error (v1 critical-failure pattern). No delete-or-keep prompt is offered.

IMPORT-12. Only after the safety gate passes does the UI prompt: Delete the original, or Keep it and move it to a folder the user chooses. This prompt is shown only to an Admin, or to the `owner_id` of the import.

IMPORT-13. Delete or move of the original MUST also be refused with HTTP 409 `resource_in_use` when any active project or job references that original path or the pre-conversion library entry. "Active" means a `Job` in `queued` or `running`, or a Project that is not `completed` and that still references the file as a registered storage path. Completed projects that still point at the path SHOULD also block deletion unless Admin confirms a forced archive; forced deletion of in-use files is MUST NOT for queued or running jobs.

IMPORT-14. The system MUST NOT delete or overwrite the original until IMPORT-10 has passed and IMPORT-12 has an affirmative, authorized choice, and IMPORT-13 is satisfied. A keep-in-place option (leave the original where it is) MUST be available in addition to move; if keep-in-place is chosen, the original is not copied.

IMPORT-15. On successful registration the library row MUST store `base_model`, layout and quant metadata, `lora_compatibility_notes` (from Civitai description or operator input), `visibility`, and `owner_id`. sha256 of the converted artifact is computed for dedup as in v1 Section 6.1.1. Dedup MUST use the converted artifact hash, not only the source hash.

IMPORT-16. Source metadata (Civitai version id, file name, author notes) MUST be retained on the record even after the original is deleted.

IMPORT-17. The original is never deleted automatically by a timeout or by a successful gate. Only an explicit authorized action deletes it.

## A6.3 Data Model

### A6.3.1 Fields added to `ModelRegistry` (v1 Section 7.15)

| Field | Type | Notes |
|---|---|---|
| visibility | enum(global, user) | Default `global` for Admin, `user` for Engineer. |
| owner_id | FK(User) | Importer or registrar. |
| core_video_model | enum(minimax_h3, ltx_2_5, wan_bernini) nullable | Required for `type='video'` generators; null for image/audio/companions. |
| base_model | string nullable | Family or official repo name, e.g. `MiniMax-H3`. |
| role | enum(generator, text_encoder, video_vae, audio_vae, latent_upscaler, other) | Default `generator` for type=video checkpoints. |
| layout | enum(standard_diffusers, comfyui_packed, comfyui_quant, unknown) | Runnable rows MUST be `standard_diffusers`. |
| quant_format | enum(bf16, fp16, fp8, nvfp4, other) nullable | |
| lora_compatibility_notes | string nullable | Surface in the LoRA UI. |
| companion_requirements | jsonb | Array of roles or model ids. |
| source_layout | enum(standard_diffusers, comfyui_packed, comfyui_quant, unknown) nullable | Layout of the intake file. |
| source_sha256 | string nullable | Hash of the original, if known. |
| import_job_id | FK(Job) nullable | |
| original_disposition | enum(pending, deleted, kept_moved, kept_in_place, not_applicable) | `not_applicable` for direct standard registrations that did not go through cleanup. |
| original_archive_path | string nullable | Server-side only; never in API responses. |

`architecture` values are extended with at least `minimax_h3`, `ltxv`, `wan` (v1 already uses `ltxv` and `wan`).

### A6.3.2 New entity `ModelImport`

| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| job_id | FK(Job) | Parent job. |
| imported_by | FK(User) | Becomes `owner_id` on success. |
| source | enum(civitai, local, huggingface) | |
| source_url | string nullable | |
| civitai_id | string nullable | |
| civitai_version_id | string nullable | |
| local_path | string nullable | Server-side only. |
| detected_layout | enum(standard_diffusers, comfyui_packed, comfyui_quant, lora, unknown) nullable | |
| target_quant | enum(fp8, nvfp4, none) | |
| target_runtime | enum(diffusers, sglang) | |
| status | enum(staged, detecting, converting, quantizing, safety_gate, awaiting_disposition, registered, failed, cancelled) | |
| model_id | FK(ModelRegistry) nullable | Set on success. |
| lora_id | FK(LoRARegistry) nullable | When the intake is a LoRA. |
| gate_passed | bool | Default false. |
| gate_log | string nullable | No secrets. |
| error_code | string nullable | |
| created_at | datetime | |
| updated_at | datetime | |

### A6.3.3 New entity `ModelScanRoot`

| Field | Type | Notes |
|---|---|---|
| id | uuid PK | |
| path | string | MAY be shown to Admin/Engineer who can manage roots; MUST NOT be shown to Viewer or Creative if it would reveal another user's directory. |
| visibility_default | enum(global, user) | |
| owner_id | FK(User) nullable | Null for shared roots. |
| created_by | FK(User) | |
| created_at | datetime | |
| is_active | bool | Default true. |

## A6.4 API

- `GET /models` — extends v1 list; filters by visibility; MAY filter `core_video_model`, `role`, `layout`. Still MUST NOT return `storage_path` or `original_archive_path`.
- `POST /models` — v1 behavior remains for standard sources. If the local/Civitai file is ComfyUI-packed, the API SHOULD instruct the client to use `POST /models/imports` rather than silently registering an unrunnable file.
- `POST /models/imports` — Admin+Engineer. Body: `{ "source": "civitai" | "local", "civitai_url": "string?", "civitai_id": "string?", "civitai_version_id": "string?", "local_path": "string?", "target_quant": "fp8" | "nvfp4" | "none", "target_runtime": "diffusers" | "sglang", "visibility": "global" | "user", "name": "string?", "display_name": "string?", "core_video_model": "string?", "lora_compatibility_notes": "string?" }`. Returns HTTP 202 with `{ "import_id": "uuid", "job_id": "uuid" }`.
- `GET /models/imports/{id}` — status, detected layout, gate result, and whether disposition is available. Paths to the original are not returned except as a basename.
- `POST /models/imports/{id}/disposition` — `{ "action": "delete" | "keep_move" | "keep_in_place", "destination_path": "string?" }`. `destination_path` required for `keep_move`. Enforces IMPORT-12 and IMPORT-13. Returns 200 on success, 409 `resource_in_use`, 403 `insufficient_role`, 409 `safety_gate_not_passed` if called early.
- `GET /models/scan-roots`, `POST /models/scan-roots` (Admin), `DELETE /models/scan-roots/{id}` (Admin).
- `POST /models/scans` — start a scan job, HTTP 202.
- `POST /projects/{id}/preflight` — body describes the intended generation (clip id or params). Returns `{ "ok": bool, "missing_pieces": [...], "vram_estimate_mb": int, "warnings": [...] }`.

Progress uses existing `WS /ws/jobs/{job_id}`.

## A6.5 UI Behavior

- An Import Model wizard (Admin, Engineer) has steps: source (Civitai URL/id or local file picker bound to allowed roots) then header detection summary (layout, tensor counts, warnings for `comfy_quant`) then quant/runtime choices (legal options only) then job progress then safety-gate result then disposition (delete / keep and choose folder / keep in place), shown only after a pass and only if the user is allowed.
- Failed gates show the error and a "Keep original and discard failed output" state. There is no delete control.
- Library views badge `global` vs `user`, quant format, and "needs import" for packed files found by a scan.
- Render / Generate actions run preflight first. Missing pieces produce a blocking modal listing the missing roles and a link to Import or scan, not a silent queue.

## A6.6 Error States

| Condition | HTTP / job | error_code |
|---|---|---|
| Role is Creative or Viewer | 403 | `insufficient_role` |
| Civitai key missing | 400 / failed job | `secret_not_configured` |
| Civitai 401/404 | failed job | `civitai_unavailable` or `civitai_not_found` |
| Path outside allow-list | 422 | `path_traversal` |
| Header is `comfyui_quant` and dequant is not enabled | failed job | `unsupported_comfy_quant` |
| AdaLN/QKV conversion failure | failed job | `conversion_failed` |
| Quantization failure | failed job | `quantization_failed` |
| Test-load or sample render failure | failed job | `safety_gate_failed` |
| Disposition before gate pass | 409 | `safety_gate_not_passed` |
| Disposition in-use | 409 | `resource_in_use` |
| Missing companions at generate time | 409 | `missing_model_piece` |
| Duplicate converted sha256 | 409 | `duplicate_model` (v1 dedup behavior) |

## A6.7 Acceptance Criteria

- GIVEN an Admin or Engineer with a Civitai API key configured WHEN they start an import from a Civitai version URL for a standard or ComfyUI-packed BF16 H3 checkpoint THEN a `model_import` job is created AND weights are not loaded until the header has been classified AND progress streams on `/ws/jobs/{job_id}`.
- GIVEN a local ComfyUI-packed H3 BF16 file whose header shows fused `attn.qkv_proj` and pruned AdaLN tensors WHEN import runs with `target_quant` set THEN the converter rewrites keys, splits Q/K/V, expands AdaLN, quantizes to the requested format, and writes a new library file without modifying the source.
- GIVEN a ComfyUI `int8_HQ` file whose header contains `comfy_quant` / `h3_native_hq.topology` WHEN the operator imports it and the dequant path is not enabled THEN the job fails with `unsupported_comfy_quant` AND the original file is unchanged.
- GIVEN conversion succeeds but sample render fails WHEN the job completes THEN `gate_passed=false` AND the disposition endpoint returns 409 `safety_gate_not_passed` AND the original file still exists at its source path.
- GIVEN `gate_passed=true` WHEN the owner or an Admin posts `disposition.action=delete` AND no active project or job references the original THEN the original is deleted AND the library entry remains with `original_disposition='deleted'`.
- GIVEN `gate_passed=true` WHEN a non-owner Engineer posts disposition THEN the API returns 403 `insufficient_role` AND the original is unchanged.
- GIVEN `gate_passed=true` WHEN an authorized user posts `keep_move` with a destination inside a configured root THEN the original is moved there AND `original_disposition='kept_moved'`.
- GIVEN a project whose H3 video VAE is missing WHEN an Engineer clicks Generate THEN preflight returns `missing_model_piece` AND no GPU job is queued.
- GIVEN a Creative user WHEN they call `POST /models/imports` THEN the API returns HTTP 403 `insufficient_role`.
- GIVEN a file already in standard Diffusers layout WHEN it is imported with `target_quant='none'` THEN conversion is skipped AND the safety gate still runs before any delete prompt is offered.

# Section A7: LoRA Library

*Extends v1 Sections 6.2 and 7.16.*

## A7.1 Requirements

LORA-01. The LoRA browser MUST filter to LoRAs whose `base_model` / architecture / `core_video_model` match the project's core video family (and, for H3, the active partition when relevant). LoRAs that do not match MUST NOT appear, with no error, as in v1 Section 6.2.

LORA-02. Visibility follows Section A4.4 (`global` / `user`, `owner_id`).

LORA-03. Stacking remains an array of `{lora_id, weight}` as in v1, subject to `max_lora_stack_size` and weight min/max on the target model. For H3, the UI MUST support the Seed Hunter v3 slots: Stage 1+2 (for example Turbo + Realism), Upscale-only, and Vocal. A LoRA assigned to Upscale-only MUST NOT be applied during Stage-1 previews or during continuation unless the Engineer explicitly overrides, which the UI SHOULD discourage.

LORA-04. Compatibility checks MUST run at preflight and when the stack changes. Checks include architecture/family match, partition match (`fl2va` vs `ref2va` for H3), and any `lora_compatibility_notes` on either the LoRA or the fine-tune checkpoint.

LORA-05. Strength warnings MUST be shown, not silently applied as a hidden rescale, unless the operator has stored an explicit recommended default weight on the LoRA. Example, from the Eros Max author and recorded on the library entry: base H3 LoRAs hit about twice as hard on that fine-tune, and low-rank MLP-only LoRAs are recommended. The UI MUST warn when a base-H3 LoRA is stacked on a checkpoint that carries this note. The system MAY suggest a lower weight; it MUST NOT change a user-set weight without confirmation.

LORA-06. During H3 continuation, Turbo LoRAs MUST be disabled by default (Seed Hunter v3 uses 10-14 steps with Turbo off). The Engineer MAY re-enable them only after a warning.

LORA-07. ComfyUI and Kohya key layouts MUST be converted to a Diffusers-loadable layout at import time (same Import Model wizard, intake type LoRA). LoRAs already in PEFT / Diffusers / ai-toolkit formats that the official Diffusers >= 0.40 `MiniMaxH3LoraLoaderMixin` accepts MAY skip key conversion after header/key inspection.

LORA-08. A LoRA trained specifically against pruned AdaLN SHOULD be flagged; AdaLN-targeted keys MAY be skipped during conversion, with a warning stored in `lora_compatibility_notes`. Behavior of pruned-AdaLN LoRAs on expanded checkpoints is TBD and MUST be tested in Phase 0 when a sample is available.

LORA-09. NSFW LoRAs remain unfiltered, as in v1 Section 6.2.

LORA-10. Import, visibility changes, and delete/move of original LoRA files follow the same RBAC and reference rules as Section A6 (Admin or Engineer to import; Admin or owner to dispose, and only when unreferenced).

## A7.2 Data Model — fields added to `LoRARegistry` (v1 Section 7.16)

| Field | Type | Notes |
|---|---|---|
| visibility | enum(global, user) | |
| owner_id | FK(User) | |
| core_video_model | enum(minimax_h3, ltx_2_5, wan_bernini) nullable | Null for image-model LoRAs. |
| base_model | string nullable | |
| target_partition | enum(fl2va, ref2va, both, n_a) | Default `n_a` for non-H3. |
| default_slot | enum(stage12, upscale, vocal, general) | Default `general`. |
| lora_compatibility_notes | string nullable | |
| recommended_weight | float nullable | Overrides display of `weight_default` when set. |
| key_layout | enum(diffusers, comfyui, kohya, peft, ai_toolkit, unknown) | |
| converted | bool | Default false. True after a successful key conversion. |
| original_disposition | enum(pending, deleted, kept_moved, kept_in_place, not_applicable) | |

`VideoClip.lora_stack` jsonb is extended to `{lora_id: uuid, weight: float, slot: enum(stage12, upscale, vocal, general)?}`. Missing `slot` defaults to `general`.

## A7.3 API

- `GET /loras` — visibility filtered; query params `core_video_model`, `base_model`, `target_partition`, `project_id` (applies the project filter).
- `POST /loras` — v1 registration, plus the import pipeline at `POST /models/imports` with a LoRA source (same endpoint, `detected_layout='lora'`).
- `PATCH /loras/{id}` — Admin, or owner for notes, default slot, visibility, recommended weight.
- `DELETE /loras/{id}` — Admin, or owner of a `user` row, and only if no active project or job references it (409 `resource_in_use` otherwise).
- Preflight (`POST /projects/{id}/preflight`) MUST include `lora_warnings: [{lora_id, code, message}]` for strength and Turbo-on-continuation notes. Warnings do not fail the request unless `error` severity is set (family mismatch is an error).

## A7.4 UI Behavior

- The inspector LoRA browser is empty of cross-family LoRAs.
- Compatibility notes appear as warning callouts when a flagged LoRA is added to a flagged fine-tune (Eros Max example).
- H3 slot racks for Stage 1+2, Upscale, and Vocal are shown only on H3 projects.
- Continuation presets turn Turbo-slot LoRAs off and show why.

## A7.5 Error States

| Condition | HTTP / preflight | error_code |
|---|---|---|
| LoRA family does not match project family | 422 | `lora_architecture_mismatch` |
| LoRA partition incompatible with mode (`ref2va` vs `fl2va`) | 422 | `lora_partition_mismatch` |
| Strength / MLP-only / Turbo-on-continuation | warning in preflight | `lora_strength_warning` / `lora_continuation_warning` |
| Key conversion failed | failed import | `lora_conversion_failed` |

## A7.6 Acceptance Criteria

- GIVEN an H3 project WHEN the Engineer opens the LoRA browser THEN only H3-compatible LoRAs that the user is allowed to see are listed AND Wan LoRAs do not appear.
- GIVEN a library entry for Eros Max that notes base H3 LoRAs hit about twice as hard WHEN the Engineer stacks a base-H3 LoRA at weight 1.0 THEN preflight returns a `lora_strength_warning` AND the weight is not auto-changed.
- GIVEN an H3 continuation job WHEN the Stage 1+2 slot contains a Turbo LoRA THEN the continuation preset disables it by default AND a warning is recorded if the Engineer forces it on.
- GIVEN a ComfyUI-format H3 LoRA file WHEN an Engineer imports it AND key conversion and a test load succeed THEN the LoRA is registered with `converted=true` AND it can be attached to an H3 clip.
- GIVEN a Wan LoRA id posted onto an H3 clip stack WHEN the API validates the clip THEN it returns 422 `lora_architecture_mismatch`.

# Section A8: Generation Engines

*Extends v1 Sections 5.2, 5.3, and 13.9. Does not invent unverified model capabilities.*

## A8.1 Common Engine Rules

GEN-01. Video inference MUST run in the engine virtualenv and Celery queue that match the project's `core_video_model` (`gpu_h3`, `gpu_ltx`, or `gpu_wan`). Workers MUST acquire the GPU mutex (QUEUE-03).

GEN-02. The application MUST NOT call ComfyUI, a ComfyUI HTTP API, or ComfyUI custom nodes to generate video or audio.

GEN-03. `VideoClip.mode='v2v'` (and family equivalents that consume a source video) MUST use the source video asset. The implementation MUST NOT alias `v2v` to `i2v` by discarding `source_asset_id` / the source video path. That alias, present in the v1 codebase, is a defect relative to v1 Section 5.2 and is forbidden here.

GEN-04. Every generate, preview, continuation, and sample-render request MUST pass profile validation (Section A5) and library preflight (LIB-06) before the mutex is acquired for a long run. VRAM profiler behavior from v1 Section 6.1.3 remains, including the Vast.ai confirmation gate.

GEN-05. Job progress MUST continue to stream on `WS /ws/jobs/{job_id}` every 500 ms during active generation (v1 Section 6.3.3).

GEN-06. Ordered multimedia references for `ref2va` / `fl2va` (and any future reference modes) MUST be stored on the clip and passed to the adapter in a stable order.

## A8.2 MiniMax H3

GEN-H3-01. H3 MUST run through Diffusers >= 0.40 (MiniMax-H3 modular pipeline with LoRA loader) or SGLang Diffusion >= 0.5.17. The default of those two runtimes is TBD after Phase 0 benchmarking on the RTX 5090. Both adapters MUST load standard-layout (converted) weights only.

GEN-H3-02. Modes required for H3 projects: `t2va` (text to joint video+audio), `fl2va` (first and/or last frame guided), `ref2va` (reference-conditioned). These names reflect the official dual-partition layout: `transformer/` for `t2va`/`fl2va`, `transformer_ref/` for `ref2va`. The UI MUST use these modes on H3 profiles rather than v1 `t2v`/`i2v` alone.

GEN-H3-03. When companions are present, H3 generation MUST produce video and 32 kHz stereo audio jointly, as documented for MiniMax-H3. The clip's output includes a video asset and an associated audio asset (or a container with both). Native audio rate is 32 kHz; export resampling is specified in Section A5 / v1 Section 5.4.3.

GEN-H3-04. H3 is guidance-distilled. The worker MUST NOT require CFG. `cfg_scale` is hidden (PROFILE-06).

GEN-H3-05. Dual schedulers MUST be exposed: video shift default 12.0, audio shift default 3.0, from Diffusers documentation. Seed Hunter also uses sigma-shift presets (12/6 or 12/3); those MAY be offered as named presets after Phase 3 confirms they map cleanly onto the official pipeline. Unverified sampler names from the ComfyUI workflow (`er_sde`, `beta`, `linear_quadratic`) MUST NOT be advertised as supported until the Diffusers/SGLang adapter implements them.

GEN-H3-06. Forced or voice-cloned dialogue: the Engineer MAY pre-generate dialogue audio (up to three takes, from a vocal reference of roughly 15-45 seconds or an `<Audio 1>` slot, with optional `*emphasis*` and a scene-tone context prompt — from Seed Hunter v3 and the walkthrough transcript) and then lock that audio into the H3 latent (`force_audio` mode). If the official pipeline does not expose an equivalent of audio VAE encode + latent noise mask, this lock path is TBD and MUST be gated behind a capability flag, not faked with a post-hoc mux only. A simple mux of pre-generated audio onto video without latent locking MAY be offered as a fallback and MUST be labeled as such.

GEN-H3-07. Previews and latent upscale are specified in Section A9. Continuation is specified in Section A9.

GEN-H3-08. Companion artifacts required for a full H3 generate (preflight): Qwen3-VL 32B text encoder (quantized as available), H3 video VAE, H3 audio VAE, and — for Stage-2 — the 3D latent upscaler. Exact official filenames may vary; preflight checks roles, not a single hard-coded filename.

## A8.3 LTX-2.5 and Wan / Bernini

GEN-LTX-01. LTX-2.5 MUST run via Diffusers ≥ 0.40, using `LTX2Pipeline` and `LTX25AutoBlocks`. Modes: `t2v`, `i2v`, true `v2v`. Approximate VRAM at 720p remains the v1 figure (~14 GB, measured against the earlier LTX path) until re-measured on LTX-2.5.

GEN-LTX-02. Joint audio and Gemma 4 text encoding are part of the LTX-2.5 Diffusers pipeline and MAY be used when present in the loaded checkpoint. Prompt Relay and IC-LoRA Union/Ingredients MUST NOT be advertised unless the pinned Diffusers pipeline exposes them. If exposed, they MAY be enabled on the LTX workflow profile and documented in `scheduler_schema` / `supported_modes`. Otherwise they stay TBD.

GEN-WAN-01. Wan 2.2 MUST run via Diffusers, extending the v1 `WanPipeline`. Modes: `t2v`, `i2v`, true `v2v`. The v1 24 GB+ / 28 GB Vast.ai flag remains.

GEN-WAN-02. Wan Animate 2 MUST be offered through Diffusers ≥ 0.40 `WanAnimate2Pipeline` when the project's workflow profile enables it. It MUST NOT be advertised on a profile that has not enabled it.

GEN-WAN-03. Bernini editing/reference and Bernini-R-S2V speech conditioning MUST NOT be advertised unless a Diffusers-native pipeline is pinned and verified. They remain TBD optional profile capabilities. Wan 2.5, Wan 2.6, Wan 2.7, Wan 3.0, and MiniMax Hailuo are hosted-only APIs and MUST NOT be implemented as local engines.

## A8.4 Data Model — fields added to `VideoClip` (engine-related)

| Field | Type | Notes |
|---|---|---|
| mode | enum(t2v, i2v, v2v, t2va, fl2va, ref2va) | Extends v1 enum. Default remains `i2v` for LTX/Wan profiles; H3 default is `t2va` or `fl2va` according to the profile. |
| reference_asset_ids | jsonb | Ordered Asset UUIDs for `ref2va` / reference modes. Default `[]`. |
| first_frame_asset_id | FK(Asset) nullable | `fl2va` Picture 1. |
| last_frame_asset_id | FK(Asset) nullable | `fl2va` Picture 2. |
| force_audio_asset_id | FK(Asset) nullable | Pre-generated dialogue or locked audio. |
| force_audio_mode | enum(off, mux_only, latent_lock) | Default `off`. `latent_lock` only if capability flag is true. |
| video_shift | float nullable | H3 scheduler; default from profile. |
| audio_shift | float nullable | H3 scheduler; default from profile. |
| output_audio_asset_id | FK(Asset) nullable | Joint audio output. |

`Asset.subtype` is extended with at least `preview`, `dialogue`, `continuation`, `upscaled`, `first_frame`, `last_frame`. v1 subtypes remain.

## A8.5 API

- `POST /projects/{id}/videoclips` and PATCH (extends v1 Section 13.9) accept the new fields. Mode must be in the project profile.
- `POST /jobs` with `type=video_generation` (v1) remains the creation path; the server sets `celery_queue` from the project family.
- `POST /projects/{id}/videoclips/{vid}/dialogue` — H3 only. Body includes script/text, optional vocal `asset_id`, take count (default 3, max 3 unless TBD changes), emphasis flags. Returns 202 with job_id. Outputs candidate audio assets.
- Generate remains Engineer + EngActive (or Admin), as in v1.

## A8.6 UI Behavior

- Mode selector shows only profile-legal modes, labeled in plain language (Text to video+audio, First/last frame, References, Video to video).
- `v2v` requires a source video; the Generate button is disabled without one.
- H3 inspectors show dual shifts, reference slots, and a Dialogue / Force audio panel. LTX/Wan inspectors keep v1-style prompts and params, plus a working source-video field for `v2v`.
- A toast MUST NOT say a feature (IC-LoRA, Bernini S2V, latent audio lock) is available if the capability flag is false.

## A8.7 Error States

| Condition | HTTP / job | error_code |
|---|---|---|
| `v2v` / `fl2va` / `ref2va` missing required source or references | 422 | `source_asset_required` |
| Latent lock requested but capability flag false | 422 | `capability_unavailable` |
| H3 runtime failed to load standard weights | failed job | `runtime_load_failed` |
| OOM | failed job, Vast.ai offer as in v1 | (v1 OOM handling) |

## A8.8 Acceptance Criteria

- GIVEN an LTX or Wan project with a source video on the clip WHEN the Engineer generates in `v2v` THEN the worker consumes that video AND MUST NOT fall back to an image-only `i2v` path.
- GIVEN an H3 project WHEN the Engineer generates `t2va` with all companions present THEN the job runs on `gpu_h3` under the GPU mutex AND a video asset and 32 kHz audio asset (or a joint container) are stored on success.
- GIVEN an H3 project WHEN the Engineer selects `ref2va` with no reference assets THEN the API returns 422 `source_asset_required`.
- GIVEN a WAN job whose VRAM estimate exceeds 28 GB WHEN the Engineer queues it THEN the v1 Vast.ai confirmation modal is shown and the job is not dispatched to the cloud without `user_ack`.
- GIVEN LTX IC-LoRA is not verified on the pinned pipeline WHEN the inspector is rendered THEN IC-LoRA controls are absent.

# Section A9: Seed Hunter-Style Review and Continuity

*New layer, extending v1 Section 5.2. Provenance is noted per requirement: Seed Hunter v3 workflow JSON, the walkthrough transcript, or engineering inference.*

This section applies to `minimax_h3` projects. LTX and Wan projects MAY offer a simpler single-output preview using v1 variation patterns; they are not required to implement 17n+5 overlap continuation unless Phase 3 verifies an equivalent.

## A9.1 Stage-1 Multi-Seed Previews

PREVIEW-01. (Workflow JSON + transcript) The Engineer MAY request Stage-1 previews as three seeds derived from a base seed `a`: `a`, `a+1000`, and `a+2000`. Default spatial target is 0.2-0.4 megapixels at 24 fps, with frame counts snapped to 17n+5.

PREVIEW-02. (Workflow JSON) Each preview decodes to a playable video+audio take. The three takes are stored on the clip (analogous to `Keyframe.candidate_asset_ids`) and are not yet the final `output_asset_id`.

PREVIEW-03. (Workflow JSON) A Single Pass option MAY skip Stage-1 and generate directly at the Stage-2 / native target (default 1.0-2.0 MP). It MUST still obey profile limits.

PREVIEW-04. The Engineer MUST explicitly promote one preview (or a Single Pass result) before Stage-2. Promotion does not delete the other takes.

## A9.2 Stage-2 Latent Upscale

PREVIEW-05. (Workflow JSON) Stage-2 MUST upscale the promoted Stage-1 latent with the H3 3D latent upscaler companion when that companion is registered. A spatial-only fallback (Section A10 upscaler) MAY be used if the latent upscaler is missing, and MUST be labeled as a fallback. Preflight warns on the missing companion.

PREVIEW-06. (Workflow JSON) Stage-2 has an independent reroll seed, optional Upscale-only LoRA, and MUST export first and last frame stills as assets (`first_frame` / `last_frame` subtypes) for later pinning.

PREVIEW-07. Stage-1 latents and seeds MUST be cached so Stage-2 can be rerun without regenerating Stage-1, unless the Engineer invalidates the cache. Cache paths are server-side only.

PREVIEW-08. Porting the ComfyUI 3D latent upscaler node to Diffusers/PyTorch is a Phase 3 risk (TBD). If the port is not ready, Stage-2 MUST fail clearly with `capability_unavailable` rather than silently skipping to a degraded path unless the Engineer chose the spatial fallback.

## A9.3 Continuation and Quality Reset

CONT-01. (Workflow JSON + transcript) Seamless continuation conditions the next segment on the last overlap of the previous video and audio. Overlap lengths MUST be chosen from the 17n+5 series used by Seed Hunter v3: 5, 22, 39, or 56 frames. The default overlap is 5 frames unless the Engineer selects another legal value.

CONT-02. (Workflow JSON) The previous clip is trimmed so that only the overlap is used as conditioning; the public timeline duration MUST not double-count the overlap after a stitch (the overlap is trimmed in the delivered edit).

CONT-03. (Workflow JSON) Continuation uses the Turbo-off preset (10-14 steps, Turbo LoRAs disabled — LORA-06).

CONT-04. (Transcript + workflow) The system MUST maintain an extension drift counter on the continuation lineage. After about 3 extensions, the UI MUST prompt for a quality reset before allowing another continuation. The Engineer MAY continue anyway after acknowledgement. The number 3 is a workflow convention, not a measured model law; it is still the v1.2 default.

CONT-05. (Transcript + workflow) Quality-reset options MUST include: (a) a camera-away redraw using the character/subject reference sheet, and (b) pinning an upscaled still (target 1080p when an upscaler is available) as `<Picture 2>` / `last_frame_asset_id` so the next continuation starts from that frame.

CONT-06. (Engineering inference on top of the transcript) Downstream clips that were generated from a segment that is later rerolled MUST be flagged stale. The Engineer is warned before export if stale descendants exist.

CONT-07. Continuation is H3-family only in v1.2 unless another family's adapter implements an equivalent overlap contract and the profile is updated.

## A9.4 Dialogue Pre-Gen in the Review Loop

(Workflow JSON + transcript) Dialogue takes from GEN-H3-06 can be padded or trimmed (including silence padding when the source video has no audio — "OG Video Has No Audio") and then fed back via `force_audio_*` before Stage-1 or continuation. Built-in silence/pause editing SHOULD be provided; a round-trip to an external editor is allowed but MUST not be the only way to pad.

## A9.5 Data Model — fields added to `VideoClip`

| Field | Type | Notes |
|---|---|---|
| preview_seed_base | int nullable | `a` in `a`, `a+1000`, `a+2000`. |
| preview_asset_ids | jsonb | Up to three Asset UUIDs. Default `[]`. |
| promoted_preview_index | int nullable | 0, 1, or 2. |
| stage2_seed | int nullable | Independent reroll seed. |
| stage1_cache_key | string nullable | Server-side cache identifier; MUST NOT appear in API if it embeds a path. A boolean `stage1_cached` MAY be returned instead. |
| continuation_of_clip_id | FK(VideoClip) nullable | Parent clip in the lineage. |
| overlap_frames | int nullable | Must be in {5, 22, 39, 56} for H3. |
| extension_index | int | Default 0. Incremented on each continuation. |
| drift_ack | bool | Default false. Required true to continue when extension_index >= drift_limit. |
| stale | bool | Default false. |

A system setting `h3_drift_limit` int default 3 MAY be stored as a non-secret Setting.

## A9.6 API

- `POST /projects/{id}/videoclips/{vid}/previews` — starts a 3-seed Stage-1 job on `gpu_h3`. Body: `{ "seed": "int?", "frames": "int?", "megapixels": "float?" }`. HTTP 202.
- `POST /projects/{id}/videoclips/{vid}/previews/promote` — `{ "index": 0|1|2 }`.
- `POST /projects/{id}/videoclips/{vid}/upscale-latent` — Stage-2. HTTP 202.
- `POST /projects/{id}/videoclips/{vid}/continue` — body `{ "overlap_frames": 5|22|39|56, "acknowledge_drift": "bool?" }`. Creates or fills the next clip, runs generation on `gpu_h3`. Returns 409 `drift_limit_reached` if the counter is at the limit and `acknowledge_drift` is not true.
- `POST /projects/{id}/videoclips/{vid}/quality-reset` — `{ "method": "camera_away" | "pinned_last_frame", "asset_id": "uuid?" }`.

All are Engineer + EngActive (or Admin).

## A9.7 UI Behavior

- A Preview tray on the clip shows three takes, playable with audio, and a Promote button.
- Stage-2 has Reroll, Upscale LoRA slot, and Download first/last frame.
- Continue asks for overlap length (default 5). At extension 3+, a modal explains contrast/quality burn (transcript: lighting, contrast, and warmth shifts after the 5-frame overlap and after multiple extensions) and requires acknowledgement or a quality reset.
- Stale descendants show a badge on the timeline.

## A9.8 Error States

| Condition | HTTP / job | error_code |
|---|---|---|
| Promote without previews | 422 | `preview_not_found` |
| Stage-2 without promotion | 422 | `preview_not_promoted` |
| Latent upscaler missing and no fallback chosen | 409 | `missing_model_piece` |
| Illegal overlap | 422 | `profile_limit_violation` |
| Drift limit without ack | 409 | `drift_limit_reached` |
| Latent upscaler port not available | 409 / failed | `capability_unavailable` |

## A9.9 Acceptance Criteria

- GIVEN an H3 clip WHEN the Engineer requests Stage-1 previews with seed 10 THEN three jobs or one batched job produce takes for seeds 10, 1010, and 2010 at 0.2-0.4 MP AND all three appear in the preview tray with audio.
- GIVEN three previews WHEN the Engineer promotes index 1 and runs Stage-2 THEN Stage-2 consumes the cached Stage-1 latent for that take AND first and last frame stills are stored AND the other preview takes remain available.
- GIVEN a completed H3 clip WHEN the Engineer continues with `overlap_frames=5` THEN the next segment is conditioned on the last 5 video frames and the matching audio AND the stitched timeline does not play the overlap twice.
- GIVEN a lineage that already has 3 extensions WHEN the Engineer requests another continuation without `acknowledge_drift` and without a quality reset THEN the API returns 409 `drift_limit_reached`.
- GIVEN a quality reset via pinned last frame WHEN the Engineer provides an upscaled still THEN the next continuation uses that still as `last_frame_asset_id`.

---

# Section A10: Multitrack Timeline Finishing

*Extends v1 Sections 5.1, 5.2.4, 5.4, and 11.7. Seam color and blur/zoom tools promote a narrow slice of v1's deferred color-grading and transition backlog (Section A17).*

## A10.1 Requirements

EDIT-01. v1 timeline behavior remains: tracks, snapping, trim handles, mute/lock/visibility, storyboard import, RIFE 2x/4x with scene-cut detect, and FFmpeg export formats (MP4/H.264, MKV/H.265, WebM/VP9) with the v1 resolution and fps export list.

EDIT-02. (Transcript) At a continuation seam, the Engineer MUST be able to match color, exposure (highlights/shadows/contrast), and warmth between the last frame of the outgoing segment and the first frame of the incoming segment, using adjacent-frame A/B comparison (left/right or a swap key). Adjustments apply to the incoming clip (or a chosen side) as clip-level grade parameters, not as a full LUT workstation.

EDIT-03. (Transcript) The Engineer MUST be able to add a short blur and/or zoom (and optional glow) transition across the seam, intended to mask residual mismatch. Defaults SHOULD be short and reset quickly. This is a seam tool, not a general transition pack. Cross-dissolves and wipes from v1 Section 10.2 remain out of scope unless already trivial to add as a MAY.

EDIT-04. (Workflow JSON; inferred NLE scope for cadence) The system MAY include an AnimeCadence-style 2D cadence limiter before RIFE. If included, it MUST be optional and off by default for live-action looks. RIFE remains the required interpolator (v1).

EDIT-05. A standalone spatial video upscaler MUST be available for Engineer's use on a clip or export (chunked/tiled so it fits in 32 GB). The specific upscaler checkpoint (`nmkdSiaxCX_200k` or another registered model) is chosen from the library; RTX VSR MAY be used if detected. This also serves quality-reset still upscales (CONT-05). v1 left Real-ESRGAN / canvas resize as an open item; this addendum requires a registered-model upscale path but does not require a particular vendor name if that model is not in the library.

EDIT-06. Render preflight MUST warn about unrendered clips (v1), missing pieces, stale continuation descendants, and ungraded seams where `seam_grade_required` is set (default true on continuation stitches).

EDIT-07. Export audio: if the timeline contains 32 kHz H3 audio, FFmpeg MUST resample to the v1 export spec (48 kHz AAC or Opus, stereo) unless the Engineer enables an optional native-rate export (MAY).

EDIT-08. Grades and transitions MUST be stored on the timeline/clip so they survive snapshot/restore (v1 snapshots store entity JSON; include the new fields).

## A10.2 Data Model

### A10.2.1 Fields added to `VideoClip`

| Field | Type | Notes |
|---|---|---|
| seam_grade | jsonb nullable | `{ "enabled": bool, "shadows": float, "highlights": float, "contrast": float, "warmth": float, "details": float, "applied_to": enum(incoming, outgoing, both) }`. Ranges TBD, documented in `param`-like limits; start with approximately -1.0..1.0 defaults 0. |
| seam_transition | jsonb nullable | `{ "type": enum(none, blur, zoom, blur_zoom), "duration_frames": int, "blur_amount": float, "zoom_amount": float, "glow": float }`. |
| cadence_limit_enabled | bool | Default false. |
| spatial_upscale | jsonb nullable | `{ "enabled": bool, "model_id": "uuid?", "target_h": int? }`. |
| seam_grade_required | bool | Default false; set true when created by continuation. |

### A10.2.2 Track type (Phase 4)

`Track.type` MAY be extended with `caption` when ASR lands in Phase 4. If extended, caption clips are a new entity or a constrained AudioClip-like record; the exact caption schema is TBD in Phase 4 and MUST be specified then without blocking Phases 0-3.

## A10.3 API

- `PATCH /projects/{id}/videoclips/{vid}` accepts `seam_grade`, `seam_transition`, `cadence_limit_enabled`, `spatial_upscale`.
- `POST /projects/{id}/videoclips/{vid}/seam-preview` — MAY return two-frame JPEGs (outgoing last, incoming first, and a graded incoming first) as assets or data URLs for the A/B inspector. If implemented as a job, use `type=seam_grade`.
- `POST /jobs` `type=video_upscale` or `type=interpolation` (v1) as appropriate.
- Render/export remain `POST /jobs` with `type=render` / `export`.

## A10.4 UI Behavior

- In the timeline inspector, a Seam panel appears when two video clips abut (especially continuation pairs). It shows A/B frames, sliders for shadows, highlights, contrast, warmth, and details (transcript), and transition controls for blur, zoom, and duration.
- Keyboard left/right SHOULD swap A/B frames, matching the walkthrough's described comparison habit.
- RIFE and export controls stay where v1 put them. Upscale is a clip or export action with progress on the clip.

## A10.5 Error States

| Condition | HTTP / job | error_code |
|---|---|---|
| Seam tools applied to a clip with no neighbor | 422 | `seam_not_applicable` |
| Upscaler model missing | 409 | `missing_model_piece` |
| Render with unrendered clips | v1 warning; Engineer may cancel | (v1 behavior) |
| Render with stale descendants | warning; MAY block if setting enabled | `stale_continuation` |

## A10.6 Acceptance Criteria

- GIVEN two H3 clips stitched with a 5-frame overlap WHEN the Engineer opens the Seam panel THEN they can A/B the outgoing last frame and the incoming first frame AND moving warmth/contrast sliders updates a preview of the incoming frame.
- GIVEN a seam transition of type `blur_zoom` with a short duration WHEN the Engineer exports THEN FFmpeg (or the render pipeline) applies a blur and zoom across that boundary in the output file.
- GIVEN `rife_enabled=true` and `rife_multiplier='2x'` WHEN video generation completes THEN a RIFE job still runs as in v1 and the clip's output becomes the interpolated asset.
- GIVEN an Engineer requests spatial upscale to 1080p with a registered upscaler WHEN the job completes THEN a new asset is stored and can be used as a pinned last frame.
- GIVEN an H3 timeline exported as MP4/H.264 at 1080p/24 WHEN render completes THEN the file is downloadable as in v1 AND audio is 48 kHz stereo unless native-rate export was selected.

# Section A11: Data Model Additions and Modifications

*Extends v1 Section 7. This section is the canonical field list for new and changed entities. Field-level rules in Sections A4-A10 still apply.*

All primary keys remain UUID v4. All timestamps remain TIMESTAMP WITH TIME ZONE in UTC. JSON fields use JSONB in PostgreSQL. `storage_path` and any archive or cache path fields remain server-side only and MUST NOT appear in API responses (v1 Section 13.11).

## A11.1 Entity inventory (delta)

| Entity | Change |
|---|---|
| WorkflowProfile | New |
| ModelImport | New |
| ModelScanRoot | New |
| Project | Add `core_video_model`, `workflow_profile_id` |
| ModelRegistry | Add visibility, owner, family, role, layout, quant, companions, import metadata |
| LoRARegistry | Add visibility, owner, family, partition, slot, notes, key conversion, disposition |
| VideoClip | Extend mode; add references, force audio, previews, continuation, seam, upscale fields |
| Asset | Extend subtype enum |
| Job | Extend type enum; optional `celery_queue` |
| Track | Phase 4 MAY add `caption` |
| Setting | Shared secrets no longer stored in `value`; see Section A4.5 |
| User, ProjectMember, HandoffRecord, Snapshot, Storyboard, Keyframe, Timeline, AudioClip, Batch, Notification, PromptTemplate, PromptHistory, UserInvite, OAuthIdentity | Unchanged except where Keyframe continues to use `model_id` for image models only |

## A11.2 Job.type additions

v1: `image_generation`, `video_generation`, `audio_generation`, `interpolation`, `inpaint`, `outpaint`, `render`, `export`.

Added: `model_import`, `model_scan`, `sample_render`, `video_preview`, `latent_upscale`, `video_upscale`, `video_continuation`, `dialogue_generation`, `seam_grade`.

Optional field `celery_queue string nullable` on Job records the routed queue (`gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`, or an image GPU worker).

## A11.3 Alembic

All schema changes MUST ship as Alembic migrations, including backfill:

- Existing projects MUST receive a `core_video_model` and `workflow_profile_id`. The migration SHOULD default historical LTX projects to `ltx_2_5` / `ltx_2_5_default` (the committed LTX core), or leave them in a `draft` state that requires Admin assignment before EngActive generation. The chosen backfill policy MUST be documented in the migration message. Silent assignment of `minimax_h3` to old projects is MUST NOT.
- Existing ModelRegistry / LoRARegistry rows default to `visibility='global'`, `owner_id=added_by` if present, else the bootstrap Admin, `layout='standard_diffusers'` if they were already used by v1 pipelines.

# Section A12: API Additions and Modifications

*Extends v1 Sections 9 and 13. Auth, pagination, error envelope, and thumbnail conventions are unchanged.*

## A12.1 New or extended REST groups

| Group | Base path | Key operations | Roles |
|---|---|---|---|
| Workflow profiles | `/workflow-profiles` | GET `/`, GET `/{id}` | Any authenticated user |
| Project clone | `/projects/{id}/clone` | POST | Admin |
| Preflight | `/projects/{id}/preflight` | POST | Creative/Engineer/Admin as allowed for the intended action |
| Model imports | `/models/imports` | POST `/`, GET `/{id}`, POST `/{id}/disposition` | Admin, Engineer |
| Scan roots | `/models/scan-roots` | GET `/`, POST `/`, DELETE `/{id}` | GET: Admin+Engineer; mutate: Admin |
| Scans | `/models/scans` | POST `/` | Admin, Engineer |
| Previews | `/projects/{id}/videoclips/{vid}/previews` | POST `/`, POST `/promote` | Engineer (EngActive), Admin |
| Latent upscale | `/projects/{id}/videoclips/{vid}/upscale-latent` | POST | Engineer, Admin |
| Continuation | `/projects/{id}/videoclips/{vid}/continue` | POST | Engineer, Admin |
| Quality reset | `/projects/{id}/videoclips/{vid}/quality-reset` | POST | Engineer, Admin |
| Dialogue | `/projects/{id}/videoclips/{vid}/dialogue` | POST | Engineer, Admin |
| Seam preview | `/projects/{id}/videoclips/{vid}/seam-preview` | POST | Engineer, Admin |

v1 groups remain. `POST /projects` and `ProjectResponse` are extended as in Section A5.4. `GET /models` and `GET /loras` filter by visibility (Section A4.4). `storage_path` remains omitted from all responses.

## A12.2 Extended POST /projects request (replaces the v1 body for new fields only)

```
{
  "title": "string",                 // required
  "description": "string?",
  "core_video_model": "minimax_h3" | "ltx_2_5" | "wan_bernini",  // required
  "workflow_profile_id": "uuid",     // required
  "fps": "int?",                     // default 24, must be profile-legal
  "resolution_w": "int?",            // default 1280, must be profile-legal
  "resolution_h": "int?"             // default 720, must be profile-legal
}
```

## A12.3 WebSocket

No new WebSocket paths are required. Import, scan, preview, continuation, and sample-render jobs MUST use `WS /ws/jobs/{job_id}`. Project-level completion events MAY also be published on `WS /ws/projects/{project_id}` with existing `event_type` + `payload` shape.

## A12.4 Error envelope

All new errors use the v1 envelope:

```
{ "error_code": "string", "message": "string", "detail": "object?" }
```

`error_code` values introduced in this addendum include: `core_model_required`, `core_model_immutable`, `core_model_mismatch`, `profile_model_mismatch`, `profile_limit_violation`, `known_bad_combination`, `mode_not_in_profile`, `profile_unverified`, `insufficient_role`, `not_found`, `resource_in_use`, `path_traversal`, `secret_not_configured`, `missing_model_piece`, `unsupported_comfy_quant`, `conversion_failed`, `quantization_failed`, `safety_gate_failed`, `safety_gate_not_passed`, `duplicate_model`, `lora_architecture_mismatch`, `lora_partition_mismatch`, `lora_conversion_failed`, `source_asset_required`, `capability_unavailable`, `runtime_load_failed`, `preview_not_found`, `preview_not_promoted`, `drift_limit_reached`, `seam_not_applicable`, `gpu_mutex_timeout`, `redis_unavailable`, `civitai_unavailable`, `civitai_not_found`.

# Section A13: UI Behavior Summary

*Extends v1 Section 11. The v1 design language is the default. A Phase 5 theme refresh (`#081A24` / `#36A9E8` / `#2DD4BF`) MAY be applied without changing layout contracts.*

- Application shell, command palette, toasts, modal, and log viewer patterns from v1 Section 11 remain.
- Project list and create dialog: required core model + profile selectors (Admin).
- Project header: read-only family/profile badge; Admin clone action.
- Library / Import: new views for scan roots, import wizard, visibility badges, disposition dialog (delete / keep-and-choose-folder / keep in place).
- Video inspector: profile-legal modes only; H3 reference and dialogue panels; preview tray; continuation and quality-reset controls; LoRA slots and warning callouts.
- Timeline: Seam panel with A/B frames and sliders; blur/zoom transition; upscale action; stale badges.
- Role-gating remains UI convenience; all rules are enforced on the API.
- Viewer persona remains read-only and MUST NOT see import disposition or secret-management screens.

# Section A14: Non-Functional Requirements

*Extends v1 Section 8. v1 targets still apply to unchanged endpoints.*

## A14.1 Performance and VRAM

| Metric | Target | Notes |
|---|---|---|
| API response (non-generation) | < 200 ms p95 | Unchanged |
| WebSocket progress interval | 500 ms during active generation | Unchanged, including import and previews |
| Timeline scrub | < 50 ms | Unchanged |
| Header-only layout detection | < 2 seconds for a local file once the header is readable | MUST NOT require a full weight load |
| Import convert+quantize of a ~37 GB BF16 H3 file | Estimate; no hard SLA in v1.2 | MUST be restartable if the process crashes; MUST not OOM-kill the API process |
| Sample-render safety gate | Short; exact frame count TBD in Phase 0 | Must finish under the 32 GB budget |
| H3 Stage-1 three-preview pack | Estimate, measured in Phase 3 | Must run under the GPU mutex sequentially or as one job |
| Cold load of quantized H3 + companions on RTX 5090 32 GB | TBD Phase 0 | If it does not fit, offload / quantize companions; do not ship a default that OOMs |
| VRAM safety margin | 10% as in v1 | Profiler includes companions and LoRAs |

Conversion SHOULD be streamed/CPU-staged. Peak working set for import on the 32 GB GPU MUST be treated as a failure if it exceeds available VRAM minus the safety margin; the original file stays.

## A14.2 Storage

- Converted and source files may both exist until disposition. Disk planning SHOULD assume a temporary 2x footprint during import.
- Scan, import staging, library, and archive roots MUST be on paths with sufficient free space; the importer SHOULD fail early with a clear error if free space is below the source size plus a margin (margin TBD; SHOULD be at least the source size).
- Stage-1 latent caches MUST be pruneable (Admin or project delete). They are not v1 snapshots and MUST NOT be required for project JSON rollback.

## A14.3 Security and reliability

All v1 Section 8.4 rules remain, plus:

- Path allow-lists cover scan, import, and archive roots (INSTALL-06).
- Secrets: Section A4.5. `.env` mode `0600` / Windows ACL. No secret in logs or API bodies.
- GPU mutex TTLs and heartbeats MUST prevent a dead worker from blocking the GPU indefinitely.
- Redis loss: generation and import MUST not start; health check fails (A4.6).

## A14.4 Logging

In addition to v1 Section 8.1, import jobs MUST log: detected layout, tensor counts, quant format, gate pass/fail, disposition action, and hashes. Prompt text at TRACE only. No file contents, no secrets, no full local paths in messages sent to the frontend log viewer if those paths would leak another user's root (Admin logs MAY include paths).

# Section A15: Open Risks and TBD Items

The following are not hidden requirements. Phase gates MUST resolve or explicitly defer them with a code comment that cites this section.

| ID | Risk | Severity | Gate |
|---|---|---|---|
| R1 | Whether MiniMax H3 plus a converted LoRA run cleanly outside ComfyUI on the RTX 5090 (32 GB, sm_120), including joint audio. | High | Phase 0. If this fails, H3 profiles MUST remain disabled in the product UI. |
| R2 | Exact reconstruction of pruned AdaLN (`adaln_basis` `[8, 2688]`, `adaln_mean` `[2688]`, `adaln_t_table` `[1025, 8]`, per-block `adaln_proj.linear.weight` `[96768, 8]`) and QKV split (`[21504, 5376]`) into standard Diffusers weights without quality loss. | High | Phase 0. Fail closed (IMPORT-06). |
| R3 | Diffusers + torchao versus SGLang + NVIDIA ModelOpt: LoRA stacking, Qwen3-VL offload, and NVFP4/fp8 quality inside 32 GB on sm_120. | High | Phase 0 chooses the default runtime. |
| R4 | Dequantizing ComfyUI ConvRot `int8_HQ` (`comfy_quant`, `weight_scale`, `convrot_groupsize: 256`) versus requiring the BF16 source. | Medium-High | Phase 0/2. Default is reject `unsupported_comfy_quant`. |
| R5 | H3 runtime maturity on sm_120 (compile, attention kernels, torchao/ModelOpt support). v1 already requires `eager` and xformers fallback. | Medium-High | Phase 0 and Hardware Profile Service extension. |
| R6 | H3 RefMods and the 3D latent upscaler today ship as ComfyUI nodes; standalone ports may slip. | Medium-High | Phase 3/4. Use `capability_unavailable` rather than a fake path. |
| R7 | Transcript quality risk: 5-frame overlap lighting/contrast/warmth jumps and contrast burn after about 3 extensions. | High / UX | Phase 3 continuation + Phase 5 seam tools. |
| R8 | Import of 37-60 GB BF16 files OOM or filling disk. | Medium-High | Phase 0/2 streaming and disk checks. |
| R9 | Vast.ai is specified in v1 but implemented as an empty stub. | Medium | Phase 5. v1 contract remains. |
| R10 | Unverified IC-LoRA, Prompt Relay, and Bernini-R-S2V capabilities. | Medium | Must stay TBD until a Diffusers-native pipeline is pinned. LTX-2.5 (`LTX2Pipeline` / `LTX25AutoBlocks`) and Wan Animate 2 (`WanAnimate2Pipeline`) are pinned to Diffusers ≥ 0.40 and are no longer in this TBD. |
| R11 | v1 TBD items this addendum touches, listed in Section A17, including lip-sync model choice, Real-ESRGAN, and audio export formats. | Medium | Resolve or re-defer with a comment citing v1 Section 10.1 and A17. |

# Section A16: Delivery Plan — Phases 0 through 5

Effort figures are engineering estimates, not commitments. They come from the gap-analysis Page as re-read on November 25, 2026, after the multi-user correction. Total: **41-58 days (estimate)**.

An integration map Page was also cited as a companion to that plan. It could not be opened from this drafting environment. Multi-user specifics in this addendum therefore follow the updated plan Page and the settled decisions in Section A0.2 (per-engine queues, GPU mutex, `global`/`user` visibility, Import RBAC, Admin `.env` plus optional user overrides, native Redis).

Phase 2 is where Import Model lands as a product feature. Phase 0 only spikes the converter and one LoRA on the 5090.

| Phase | Name | Estimate | Entry condition | Primary deliverables |
|---|---|---|---|---|
| 0 | H3 + LoRA + converter round-trip on RTX 5090 | 4-6 days | Start | Standalone (non-ComfyUI) conversion of one packed H3 checkpoint (Eros Max BF16 or a Comfy-Org pruned BF16), QKV split, AdaLN expansion, fp8 or NVFP4 quant (torchao and/or ModelOpt), one converted LoRA, a playable joint video+audio sample within 32 GB. Record the default runtime recommendation. Decision on `int8_HQ`. If the spike fails, H3 remains disabled and later H3-only work is replanned. |
| 1 | Project lock, Celery routes, multi-user library scan | 5-7 days | Phase 0 recorded (H3 may still be flagged unverified) | Keep Redis, Celery, JWT/OAuth, pub/sub, and RBAC. Add immutable `core_video_model` + `workflow_profile_id`, profile validator, queue routes `gpu_h3`, `gpu_ltx`, `gpu_wan`, `gpu_audio`, `import_cpu`, GPU mutex, Admin `.env` with optional user overrides, recursive scan, `global`/`user` + `owner_id`, missing-piece preflight. |
| 2 | Import Model | 7-10 days | Phase 1 library schema and `import_cpu` exist | Civitai and local intake (Admin/Engineer only), header detection, converter, quantize, test-load + sample-render gate on a `gpu_*` queue with Redis progress, disposition delete/keep/move (Admin or owner, and only if unreferenced). LoRA key conversion. |
| 3 | Engines, Seed Hunter stages, continuity, upscaler | 10-14 days | Import can produce standard-layout runnable H3 (or H3 stays behind a flag) | Runtime adapters for H3 / LTX-2.5 / Wan, true `v2v`, `t2va`/`fl2va`/`ref2va`, per-engine Celery GPU workers + mutex, 3-seed previews, Stage-2 latent upscale, dialogue pre-gen and force-audio (capability-flagged), 17n+5 continuation, drift/reset helpers, standalone spatial upscaler. |
| 4 | Prompt IDE, RefMods, LoRA gate, ASR/SAM | 6-9 days | Clip and audio APIs from Phase 3 | 6-field Singularity prompt IDE, RefMods if ported, llama-server/OpenAI scene-plan expansion (profile-specific renderers), LoRA compatibility warnings in all slots, Whisper/Qwen3-ASR, ForcedAligner, VoxCPM2, SAM3.1, optional `caption` tracks. Prompt IDE and ASR details that are not fully specified in Sections A5-A10 MUST be elaborated in a short follow-on note before Phase 4 implementation; they are in the phase plan but their field-level schemas are partially TBD. |
| 5 | NLE seams, Vast.ai, Docker-free installers | 9-12 days | Finishing APIs can consume Phase 3 outputs | Seam color/exposure/warmth, blur/zoom transitions, optional cadence limiter, real Vast.ai SSH/TLS VM worker (v1 Section 6.4 / 9.5), theme, `scripts/install.sh` (`redis-server`) and `scripts/install.ps1` (Memurai or native Windows Redis), no Docker. |

No phase MAY remove Redis, Celery, or the four-persona state machine.

# Section A17: v1 TBD and v2 Backlog Items Touched

v1 Section 0 example ("Audio timing offset — TBD v2"), Section 1.3 out-of-scope list, Section 10.1 open items, and Section 10.2 v2 backlog are the baseline. This addendum touches the following. Items not listed remain deferred exactly as in v1. Section 14 notes that some backlog items (PNG sequence export, analytics, presence) already landed in the May 31, 2026 implementation; this addendum does not reopen them except as noted.

| v1 location | Item | How this addendum touches it | Disposition in v1.2 |
|---|---|---|---|
| §0 / implied audio sync | Audio timing offset TBD v2 | Dialogue padding/trimming and force-audio lock can change audio length relative to video. | Still no general NLE time-stretch tool. Padding and latent-lock are in scope for H3. Residual sync offset remains TBD. |
| §1.3 / §10.2 | Color grading / LUT tools | Seam color, exposure (shadows, highlights, contrast), and warmth matching are required. | Narrow promotion only. Full LUT/CDL suites remain v2. |
| §1.3 / §10.2 | Transition effects (cross-dissolve, wipe) | Blur and zoom (optional glow) seam transitions are required. | Narrow promotion only. General transition packs remain v2. MAY add a dissolve later, not required. |
| §1.3 / §10.2 | Subtitle / caption generation | Phase 4 plan includes Whisper/Qwen3-ASR and a `caption` track type. | Promoted into Phase 4 at plan level. Caption schema is TBD until Phase 4 starts. Not required to close Phases 0-3. |
| §10.1 | Real-ESRGAN / canvas resize "if model registered" | Spatial video upscaler and pinned-frame still upscale are required, using a registered library model. | Open item resolved as "registered-model upscale is in scope." A specific Real-ESRGAN filename is not required. |
| §10.1 | Lip sync model (wav2lip vs SadTalker, sm_120) | H3 voice-cloned dialogue is adjacent but not a replacement for v1 wav2lip. | v1 open item remains. wav2lip stays the v1 lipsync path until Engineering confirms an alternative. |
| §10.1 | Audio export formats (WAV/FLAC implied) | H3 native 32 kHz audio is resampled to v1 48 kHz AAC/Opus on export; optional native-rate export is MAY. | Still confirm WAV/FLAC if they are required as official export formats. Not silently added. |
| §10.1 | xformers sm_120 status | Still relevant; eager + SDPA fallback remains mandatory. Hardware Profile adds fp8/NVFP4 capability checks. | Same rule as v1; verify again in Phase 0. |
| §5.2 / implementation | `v2v` specified in v1 but aliased to `i2v` in code | True `v2v` is required. | Defect relative to v1 is closed by GEN-03. |
| §3.2 | CUDA 12.4+ | Raised to 12.8+. | Modification. |
| §3.2 / §3.4 | Linux-only deploy; `docker run redis:7` in start scripts | Native Windows + Ubuntu; native Redis (Memurai or Windows Redis; `redis-server` on Ubuntu). | Modification. |
| §6.4 / §9.5 / §14 | Vast.ai bursting | Remains in contract; implementation stub must be replaced in Phase 5. | Already in v1 scope; not a new v2 promotion. |
| §10.2 | Real-time multi-user collaboration (CRDT/OT) | Multi-user RBAC is required and extended; CRDT co-editing is not. | Remains v2. |
| §10.2 | Community model marketplace | Import Model is an operator pipeline, not a marketplace. | Remains v2. |
| §10.2 | Cloud-native SaaS | Unchanged. | Remains v2. |
| §10.2 | Pixel-level paint tools | Unchanged. | Remains v2. |
| §10.2 | Mobile native application | Unchanged. | Remains v2. |
| §10.2 | Third-party plugin system | Unchanged. | Remains v2. |
| §10.2 | Project analytics dashboard | Section 14 already notes analytics landed in v1 implementation. This addendum does not extend it. | No change. |
| §10.2 | Admin audit log UI | Unchanged. Structured logs remain. Import logs extend §8.1. | Remains v2. |
| §10.2 | PNG sequence + EDL export | Section 14 says PNG sequence export landed. Not extended here. | No change. |

---

End of Addendum

AI Movie Maker PRD Addendum v1.2 — Movie Maker Layers — November 26, 2026

This addendum extends, and does not replace, AI Movie Maker PRD v1.0 (March 13, 2026; updated May 31, 2026; Implemented v1 — Regression verified).

