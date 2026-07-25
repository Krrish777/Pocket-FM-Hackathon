# Project Progress

> Durable cumulative state. **Read at session start; update before session end.** Per-session notes go in
> `session_handoff.md`; decisions in `DECISIONS.md`; the machine task list is `feature_list.json`.

## Current State
- **Phase:** **PRODUCT** (the brief has landed; harness phase is closed). The problem statement is selected,
  narrowed, and written up — **`project_context.md` is the single source of truth for what we are building
  and why. Read it before building anything.**
- **Product in one line:** a playable branching layer over the **Dexter novels** — pick a character, play
  forward through choices mined from **fan-fiction**, with every character remembering only what they
  actually learned. Track: P1 Story Time Machine + Infinite Story Universe.
- **Runway:** 24–36h, 2–4 people. Parallel sessions are live in `.claude/worktrees/`
  (`reddit-fanfic-scraper` = the EXT-1 ingestion dependency; `knowledge-base`).
- **Verification:** `make check` is **GREEN — 110 passing** (70 unit, 40 integration + e2e against REAL
  on-disk SQLite). INIT-01…05 + HARDEN-01…04 pass; HARDEN-05 deferred.
- **🧠 THE KNOWLEDGE BASE IS BUILT AND END-TO-END TESTED** (branch `worktree-knowledge-base`, rebased onto
  main 2026-07-25). Three stores over one tri-temporal fact model: **canon store** (SQLite, atomic
  supersession, as-of queries) · **graph projection** (multi-hop traversal, relationship diff) ·
  **vector store** (semantic recall, guard applied as a PRE-filter) · plus **agent working memory**
  (bounded, deterministic, per-character). Spoiler guard asserted at every layer; durability proven by
  closing and reopening the database twice. `KB-01`, `KB-07`…`KB-12` all `passes:true`, each verification
  command re-run individually.
- **What the KB still owes the product:** it is **EMPTY** (no ingestion — that is EXT-1), and `KB-13`
  (fork write path + deriving `knower_scope` from `Scene.witnesses`) is not started. Those two are the only
  KB items the agent loop actually needs. **Seeding 20–40 hand-authored facts (~1h) unblocks the loop today**
  — the API is stable and tested, so an agent built against seeded data works unchanged when ingestion lands.
- **Product features M1–M8 / S1–S3 remain `passes:false`** — but M5 and M8's *storage substrate* now exists
  and is tested; see their `evidence` fields for exactly what is done and what is not.

## Completed
- [x] **Conventions system** — migrated (session 4) to native **`.claude/rules/`**: 7 path-scoped rules that
      auto-load by file type. Replaced the hand-rolled PreToolUse hook; one `python-conventions` skill kept.
- [x] **Research** (8 cited artifacts) in top-level `research/` + `research/llms.txt` source index (moved OUT
      of `.claude/` to keep it lean).
- [x] **Harness**: `CLAUDE.md` (+ `AGENTS.md` mirror) with clock-in/out loop; SessionStart clock-in hook;
      state files (`BACKLOG`, `PROGRESS`, `DECISIONS`, `session_handoff`, `feature_list.json`).
- [x] **Backend scaffold** (`src/story_engine/`, ~30 modules, all compile): `domain/` (base + enums + models:
      Story/Episode/Character + memory models), `ports/` (llm, prompt_store, 3 memory ports), `services/`
      (episode_generator), `adapters/outbound/` (in-memory repos, stub LLM, file prompt store), `api/` (FastAPI
      factory + router + schemas + error handlers), `cli/` (Typer), `bootstrap.py`, `config/settings.py`,
      `shared/` (errors + text + retry), `observability/logging.py`, `resources/`.
- [x] Config: `pyproject.toml` (deps + tool config + `[project.scripts]`), `.env.example`,
      `.pre-commit-config.yaml`, `.gitignore`. Removed root `main.py`. Documented `temp/` as agent scratchpad.
- [x] Strict evaluation of `.claude` setup; fixed hook placeholder `${CLAUDE_PROJECT_DIR}`.

### Session 2 (2026-07-24) — harness hardening
- [x] **`make check` green from scratch**: fixed packaging (dev tools → PEP 735 `[dependency-groups]` so
      `uv sync` installs them), `StrEnum` (UP042), excluded vendored `.agents/` from ruff, `isinstance`-narrowed
      the FastAPI error handler for mypy. INIT-02…05 now pass.
- [x] **SQLite persistence adapter** (`adapters/outbound/persistence/`, SQLModel): `db.py` (engine +
      `session_scope` + `init_db`), `tables.py` (`EpisodeSummaryRow`, JSON columns), `episode_log_repository.py`
      (`SqliteEpisodeLogRepository` implements `EpisodeLogRepositoryPort`, explicit Row⇄domain mapping,
      `col()` for strict-mypy). Fixed a `DetachedInstanceError` (map inside the session scope). **HARDEN-01.**
- [x] **Enhanced settings** (`config/settings.py`): tiangolo-adapted `project_name`, `api_v1_str`,
      `environment`, CORS `parse_cors` + `all_cors_origins`, `database_url` (SQLite default) — kept our
      `SecretStr` LLM settings + `STORYENGINE_` prefix.
- [x] **Wired bootstrap + app factory**: engine created + schema init at startup; `SqliteEpisodeLogRepository`
      injected; `custom_generate_unique_id`, optional-CORS, router aggregation (`api/main.py`) mounted under
      `api_v1_str`; `create_app(container)` is now test-injectable. Wired `make dev`/`make run` (uvicorn).
- [x] **Validation Hierarchy set up** (L1 static / L2 runtime / L3 e2e) — `tests/{unit,integration,e2e}/`,
      `integration`/`e2e` markers, `make check` runs all three, documented in `tests/README.md` (from the
      Harness-Engineering docs). **HARDEN-02/03.**
- [x] **Skills**: installed `find-skills` meta-skill; verified + installed official **FastAPI skill**
      project-level; recorded the reusable skill-evaluation matrix in `DECISIONS.md` + memory. **HARDEN-04.**

### Session 3 (2026-07-24) — user file-by-file review (REVIEW-01…04)
- [x] **REVIEW-01:** dropped the `STORYENGINE_` env prefix — removed `env_prefix` in `settings.py`, rewrote
      `.env.example` with plain SDK-native names (also fixed a stale `TEMPERATURE` var that never mapped to a field).
- [x] **REVIEW-02:** relocated conventions `.claude/docs/conventions/` → **`.claude/conventions/`** (they aren't
      "docs"); patched all 29 inbound references; left `DECISIONS.md` history intact + appended a reversal entry.
- [x] **REVIEW-03:** researched (3 parallel web agents) + refreshed **all** convention docs. Python: mypy-strict
      redundancy, PEP 695 generics, pytest-9 / Ruff-0.16, Black→`ruff format`, **new `09-persistence.md`**.
      Structure: re-synced all 3 docs to the real tree (bootstrap composition root, `shared/`/`resources/`, split
      ports). Frontend: Next 16 async APIs / React 19.2+Compiler 1.0 / Tailwind v4 / WCAG 2.2 AA / shadcn Base UI
      (framed "verify at creation"). Inline source URLs + provenance appended to 5 `research/` files.
- [x] **REVIEW-04:** aligned live `pyproject.toml` — trimmed mypy to `strict`+`no_implicit_optional`, added `RUF`
      (0 new violations), `minversion=9.0`, `[tool.coverage]`. Doc ⇄ config now in sync.

### Session 4 (2026-07-24) — restructure onto native `.claude/rules/`
- [x] **Researched the question first (3 agents):** confirmed our 22-file conventions "database" was
      over-engineered vs. how real Claude-Code repos work; produced the Opus-4.8 prompt-engineering rule draft
      and the `research/`-reorg + `reference/`-hub design. A 4th agent verified the exact `.claude/rules/` format
      (`paths:` YAML list, not Cursor's `globs:`) before any file was written.
- [x] **Migrated → `.claude/rules/`** (7 rules: `python-style`, `python-design`, `persistence`, `structure`,
      `llm-storytelling`, `prompts`, `testing`). Deleted `.claude/conventions/`, the `conventions-reminder.mjs`
      hook + its settings.json registration, and the `frontend-conventions` skill; preserved the untracked
      frontend draft → `temp/frontend-conventions-draft/`. Repointed CLAUDE.md, AGENTS.md, README, prompts/README,
      pyproject, and 11 `src/` docstrings.
- [x] **Two-tier testing** encoded (`.claude/rules/testing.md` + memory): pytest (code) + DeepEval (LLM quality).
      Scaffolded `evals/metrics/metrics.py` + `evals/README.md`; `deepeval` not yet a dep; datasets blocked on brief.
- [x] **research/ reorganized** by domain + `research/README.md`; **new `reference/llms.txt`** hub of upstream
      dependency docs (link-not-vendor), wired into CLAUDE.md/AGENTS.md (research = learned-from, reference = go-read).

### Session 5 (2026-07-25) — the brief landed; problem statement selected and narrowed (INIT-01 ✅)
- [x] **INIT-01 closed.** Established that the official brief is a **menu** (~40 statements / 6 tracks), so
      "capture the problem statement" was a *selection + narrowing* decision, not a copy-paste. Selected
      **P1 Story Time Machine** + **Infinite Story Universe**.
- [x] **Resolved the repo's central unresolved conflict**: `_PROBLEM VERDICT` said build for the *creator*;
      the friend-authored PRD built for the *listener*. Settled: **the Player is primary, creator is a slide** —
      an explicit override of the vault's own recommendation, recorded as such in `DECISIONS.md`.
- [x] **Wrote `project_context.md`** (13 §, ~390 lines): problem, product, users, exact core loop, glossary,
      corpus, MUST/SHOULD/OUT scope, demo proof, external deps, **17 settled decisions**, **6 open items**
      (each with ID/owner/recommendation/deadline), and explicit **supersessions** of the friend's PRD,
      `_PROBLEM VERDICT`, and parts of `PRD-KNOWLEDGE-BASE.md`.
- [x] **Wrote `docs/2026-07-25-product-definition-session.md`** — decision provenance: 13 decisions each with
      *what was chosen, why, and what was rejected*, plus a corrections table (5 mid-session reversals,
      including two of the assistant's own errors). New top-level `docs/` dir (not yet in `structure.md`).
- [x] **Key product ideas established** (neither doc had them): fan-fiction is the **branch oracle** (a third
      path past the hand-authored-vs-generated dead end); **intentional divergence vs accidental contradiction**;
      **protagonist-ness is a rendering choice, not a stored property** — which makes Infinite Story Universe
      nearly free and unlocks the closing demo beat (replay the same branch as Debra).
- [x] **Patched** `CLAUDE.md` + `AGENTS.md` (mirror kept in sync) to point at `project_context.md`; verified
      INIT-01's own verification command passes.
- [x] **Seeded `feature_list.json` with the product phase** — M1–M8 (MUST) + S1–S3 (SHOULD), each with a
      verification command, all `passes:false`. Build order flagged: **M8 first** (only decision expensive to retrofit).
- [x] **Fixed the gate:** added `.claude/worktrees` to ruff `extend-exclude` — parallel-session worktrees are
      separate checkouts that run their own `make check`; linting them from the parent made our gate fail on
      their in-progress code. `make check` re-verified GREEN (exit 0, 7 passed).
- **No product code written this session** — by design; this was an elicitation session.

## Known Issues
- **L3 E2E is partial**: the full `premise → episode → persist` request path is NOT yet E2E-tested — the LLM
  adapter is deferred to the event brief and `StubLLM.generate` raises by design. Today's E2E proves boot +
  schema init only (tracked in `tests/README.md` + HARDEN-02).
- Domain models/services/adapters are **STARTER stubs** — refine to the brief. `StoryBible` repo is still
  in-memory (only the episode-log is SQLite so far).
- `fastapi.testclient` emits a `StarletteDeprecationWarning` (wants `httpx2`) — harmless, future compat only.
- The project-level FastAPI skill is a **symlink** (`.claude/skills/fastapi` → `.agents/skills/fastapi`);
  confirm git tracks it correctly on Windows before relying on it committed.
- CLAUDE.md/AGENTS.md are manual mirrors (drift risk). Clock-out is prose-only (not enforced).
- **⚠ The git index is shared across parallel sessions.** Session 5 staged 4 files for review; a parallel
  session then ran a commit that swept the whole index into `8d70e1b` "regular updates" (164 files). Staging
  is **not** a safe hold when other sessions are live — only an uncommitted working tree is. Coordinate before
  staging, or expect your work to be committed by someone else under someone else's message.
- **New top-level `docs/` dir** (session 5) is not yet described in `.claude/rules/structure.md`, which is an
  always-on rule and is meant to be an accurate map of the tree. Add it, or move the file.
- **`make check` exit codes:** do not pipe `make check` into `tail`/`head` — the pipeline reports the *filter's*
  exit code, not make's, and a red gate reads as green. Redirect to a file and check `$?` instead.

## Next Steps
> Ordered. WIP = 1. `project_context.md` §7 defines every done-condition; do not re-derive scope from memory.

1. **M8 — the uniform character state schema. BUILD THIS FIRST.** All 5 cast members share one identical
   state structure (knowledge set over one world state + traits + goals); **no PC/NPC asymmetry in storage**;
   character state **never** stored as narrative text; the renderer takes a character as a **parameter**.
   Rationale: it is the only decision in the product that is expensive to retrofit, and M5 + S3 both depend
   on it. Spec: `project_context.md` §4.4.
2. **Resolve OD-1 (fork vs. tier)** before the storage layer is written. Recommendation: **fork** — a tier
   model mislabels every deliberate divergence as an error, which is fatal for fan-fiction.
3. **Get the EXT-1 contract from the scraper session (OD-3)** — highest-risk unknown in the project; everything
   downstream of ingestion depends on a shape nobody has written down. Then fill `project_context.md` §9.
4. **Resolve OD-2 (novel vs. screen canon)** *before* any fan-fiction is ingested. Our KB is novel-based;
   Dexter fan-fiction is largely screen-based — a silent corruption path.
5. **M5 — per-character epistemic memory** (depends on M8). Acceptance: a character who did not learn a fact
   at step 4 still does not know it at step N, for all N > 4.
6. Then **M1 → M4 → M2 → M3 → M6 → M7**. Only after every M passes: **S3** (replay-as-Debra, the closing beat),
   then S2, S1.
7. **Deferred / unblocked-by-brief but lower priority than the above:** HARDEN-05 (local sqlmodel/pytest skills);
   the E2E gap (deterministic offline LLM so generate→persist is L3-testable without a key); `StoryBible` in
   SQLite; the `deepeval` eval harness (goldens can now be generated — the brief no longer blocks it);
   re-homing the frontend convention draft from `temp/frontend-conventions-draft/` when a UI actually starts.
