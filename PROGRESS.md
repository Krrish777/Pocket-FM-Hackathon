# Project Progress

> Durable cumulative state. **Read at session start; update before session end.** Per-session notes go in
> `session_handoff.md`; decisions in `DECISIONS.md`; the machine task list is `feature_list.json`.

## Current State
- **Phase:** Harness-hardening (pre-event). The real problem statement drops at the event **2026-07-25**;
  theme (fixed) = Generative Storytelling. Goal until then = a warm, verified harness — NOT product features.
- **Last commit:** _(none — checkpoint pending; ask before committing)_.
- **Verification:** `make check` is **GREEN** — ruff (+`RUF`) + ruff-format + mypy (45 files) + pytest **7 passing**
  (1 unit, 4 integration real-SQLite, 2 e2e). INIT-02…05 + HARDEN-01…04 pass; **INIT-01 blocked on the brief**;
  HARDEN-05 deferred. Session 4 migrated conventions to native **`.claude/rules/`** (path-scoped), split testing
  into two tiers (pytest + DeepEval), reorganized `research/` by domain, and added a `reference/` docs hub —
  `make check` still GREEN.

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

## Next Steps
1. **HARDEN-05 (deferred):** author local `sqlmodel` / `pytest` / thin `pydantic` skills modeled on the
   FastAPI skill structure (no standalone `sqlalchemy` skill — folds into `sqlmodel`).
2. Close the E2E gap: a deterministic **offline/fake LLM** + a persistence-backed route so the full
   generate→persist path is L3-testable without a key. Add `prompts/episode_generation/v1.jinja`.
3. Persist the `StoryBible` canonical store in SQLite too (mirror the episode-log adapter pattern).
4. **At the event (2026-07-25):** capture the real brief in `CLAUDE.md` (INIT-01), seed product features,
   pick the LLM/agent framework (LangChain/LangGraph/CrewAI/Pydantic-AI/raw) + drop in the OpenAI key.
5. When the brief unblocks it: add the `deepeval` dep (eval group), generate goldens (30–50), fill thresholds in
   `evals/metrics/metrics.py`, write an `evals/cases/` suite + `make eval`. Harness scaffolded (session 4).
6. Frontend convention draft is parked in `temp/frontend-conventions-draft/` (gitignored) — re-home as
   `.claude/rules/frontend-*.md` (`paths: **/*.tsx`) when the Next.js app actually starts.
